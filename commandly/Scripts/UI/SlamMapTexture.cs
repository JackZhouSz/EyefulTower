// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;

using nav_msgs = RosSharp.RosBridgeClient.MessageTypes.Nav;
using geo_msgs = RosSharp.RosBridgeClient.MessageTypes.Geometry;
using std_srvs = RosSharp.RosBridgeClient.MessageTypes.Std;
using System.Collections.Generic;
using System;

using eyeful_msgs = RosSharp.RosBridgeClient.MessageTypes.EyefulRos;

public partial class SlamMapTexture : TextureRect
{
    struct Pos
    {
        public double X { get; set; }
        public double Y { get; set; }
    }

    struct Rot
    {
        public double X { get; set; }
        public double Y { get; set; }
        public double Z { get; set; }
        public double W { get; set; }
    }

    [Export]
    private int ImageScale = 2;

    [Export]
    private Sprite2D RobotSprite;

    [Export]
    private bool PlaceableGoals = false;

    [Export]
    private PackedScene GoalPointPrefab;

    readonly float PAL_DIA = 0.60f; // Diameter is 54 centimeters. Expanding to get more coverage during capture.

    private sbyte[] mapData;
    private uint mapWidth;
    private uint mapHeight;
    private float mapResolution;
    private Pos mapOriginPos = new();
    private Quaternion mapOriginRot = new();
    private Image tmpImage;
    private List<Vector3> poseCache = [];
    private bool drawPoints = false;
    private Vector2 robotPose;
    private float robotRotation;
    private int robotPixelDia;

    private float widthScaler = 1;
    private float heightScaler = 1;

    private Mutex drawMutex = new();

    private bool updateMap = false;

    private bool firstFetch = true;

    private bool validMouse = false;

    private List<Vector2> goalPoints = [];
    private List<Sprite2D> goalPointSprites = [];

    public override void _Ready()
    {
        base._Ready();
        SlamMapSubscriber.Subscribe(mapCallback);
        CapturePoseSubscriber.Subscribe(getCapturePosition);
        RobotPoseSubscriber.Subscribe(getRobotPose);
        SdFormatterService.SubscribeToService(clearPoseCache);

        // TODO: Get size from attached texture rect
        tmpImage = Image.CreateEmpty(900, 550, false, Image.Format.Rgb8);
        this.MouseEntered += OnMouseEntered;
        this.MouseExited += OnMouseExit;
    }

    private void OnMouseEntered()
    {
        validMouse = true;
    }

    private void OnMouseExit()
    {
        validMouse = false;
    }

    public override void _Process(double delta)
    {
        if (mapData != null && (updateMap || firstFetch))
        {
            drawMutex.Lock();
            // tmpImage?.Free();
            drawMapFromData(true);
            tmpImage.Resize((int)(mapWidth * ImageScale), (int)(mapHeight * ImageScale));
            this.Texture = ImageTexture.CreateFromImage(tmpImage);
            firstFetch = false;
            drawMutex.Unlock();
        }
        else if (mapData != null && drawPoints)
        {
            PlacePoint();
            drawPoints = false;
        }

        if (mapData != null && !updateMap)
        {
            // move robot
            RobotSprite.Visible = true;
            moveRobotSprite(robotPose, robotRotation);
        }
        else
        {
            RobotSprite.Visible = false;
        }

        if (PlaceableGoals)
        {
            var mousePos = GetLocalMousePosition();
            if (Input.IsActionJustPressed("place_point") && inMapBounds(mousePos))
            {
                // Divide by scale to get the actual map position
                var goalPoint = GoalPointPrefab.Instantiate<Sprite2D>();
                this.AddChild(goalPoint);
                goalPoint.Position = new(mousePos.X, mousePos.Y);
                // Goal points will be in map frame
                // Mouse position in pixels, to meters
                var xMeters = mousePos.X * mapResolution;
                var yMeters = mousePos.Y * mapResolution;

                // Unscale, since we are scaling up
                var xUnscaledMeters = xMeters / ImageScale;
                var yUnscaledMeters = yMeters / ImageScale;

                // Offset by origin
                var xMapFrame = (float)mapOriginPos.X + xUnscaledMeters;
                var yMapFrame = (float)mapOriginPos.Y + yUnscaledMeters;

                var newPoint = new Vector2(xMapFrame, yMapFrame);
                goalPoints.Add(newPoint);
                goalPointSprites.Add(goalPoint);
            }
        }
    }

    public void StartMapUpdates()
    {
        updateMap = true;
        drawMutex.Lock();
        mapData = null;
        tmpImage = Image.CreateEmpty(900, 550, false, Image.Format.Rgb8);
        this.Texture = ImageTexture.CreateFromImage(tmpImage);
        drawMutex.Unlock();
    }

    public void StopMapUpdates()
    {
        updateMap = false;
    }

    public void ClearGoalPoints()
    {
        if (goalPoints.Count > 0)
        {
            GD.Print("Clearing");
            goalPoints.RemoveRange(0, goalPoints.Count);

            foreach (var sprite in goalPointSprites)
            {
                GD.Print("Freeing...");
                sprite.QueueFree();
                GD.Print("Freed");
            }

            goalPointSprites.RemoveRange(0, goalPointSprites.Count);
        }
    }

    public void FetchMap()
    {
        firstFetch = true;
        drawPoints = true;
    }

    public void RemovePoint(Vector2 point)
    {
        int index = goalPoints.IndexOf(point);
        goalPoints.Remove(point);
        var sprite = goalPointSprites[index];
        goalPointSprites.Remove(sprite);
        sprite.QueueFree();
    }

    public void RemoveLastPoint()
    {
        if (goalPoints.Count > 0)
        {
            var index = goalPoints.Count - 1;
            goalPoints.RemoveAt(index);
            var sprite = goalPointSprites[index];
            goalPointSprites.Remove(sprite);
            sprite.QueueFree();
        }
    }

    public List<Vector2> GetGoalPoints()
    {
        return goalPoints;
    }

    public void CanPlaceGoals(bool placeGoals)
    {
        this.PlaceableGoals = placeGoals;
    }

    private bool inMapBounds(Vector2 point)
    {
        return point.X > 0 && point.X < (mapWidth * ImageScale) && point.Y > 0 && point.Y < (mapHeight * ImageScale) && validMouse;
    }

    private void clearPoseCache(std_srvs.Trigger_Response response)
    {
        drawMutex.Lock();
        poseCache = [];
        drawPoints = true;
        drawMutex.Unlock();
    }

    private void getCapturePosition(eyeful_msgs.CapturePoseList poses)
    {
        // PlacePoint(robotPos);
        // TODO: handle the mapupdate part here
        // maybe just add directly to the cache
        drawMutex.Lock();
        foreach (var pose in poses.capture_poses)
        {
            var robotPos = new Vector3((float)pose.x, (float)pose.y, (float)pose.z);
            poseCache.Add(robotPos);
        }
        drawPoints = true;
        drawMutex.Unlock();
    }

    public void AddCapturePosition(Vector2 robotPos)
    {
        drawMutex.Lock();
        poseCache.Add(new(robotPos.X, robotPos.Y, 0.0f));
        drawPoints = true;
        drawMutex.Unlock();
    }

    private void getRobotPose(geo_msgs.Pose pose)
    {
        Vector2 posistion = new((float)pose.position.x, (float)pose.position.y);
        Quaternion rotation = new((float)pose.orientation.x, (float)pose.orientation.y, (float)pose.orientation.z, (float)pose.orientation.w);
        // robotPose = new(rotation.GetEuler().Z, posistion);
        robotPose = posistion;
        robotRotation = rotation.GetEuler().Z + mapOriginRot.GetEuler().Z;
    }

    public void PlacePoint()
    {
        // This will draw the circle at the given position on the map
        // Only draw points when map updating is done
        if (!updateMap)
        {
            drawMutex.Lock();
            // Convert from world position to pixel map position
            drawMapFromData(true);
            Color pixelColor = new(255, 0, 0);
            for (int i = 0; i < poseCache.Count; i++)
            {
                var robotPos = poseCache[i];
                drawCircleAt(robotPos, pixelColor, robotPixelDia / 2);
            }
            tmpImage.Resize((int)(mapWidth * ImageScale), (int)(mapHeight * ImageScale));
            this.Texture = ImageTexture.CreateFromImage(tmpImage);
            drawMutex.Unlock();
        }
        // drawPoints = false;
    }


    // TODO: I want to do things like this in a shader.
    private void drawCircleAt(Vector3 point, Color color, int radius, bool inMapFrame = false)
    {
        int centerX = (int)point.X;
        int centerY = (int)point.Y;
        if (!inMapFrame)
        {
            centerX = (int)((point.X - mapOriginPos.X) / mapResolution);
            centerY = (int)((point.Y - mapOriginPos.Y) / mapResolution);
        }
        // int radius = robotPixelDia / 2;

        int minX = Math.Max(centerX - radius, 0);
        int maxX = (int)Math.Max(centerX + radius, mapWidth - 1);
        int minY = Math.Max(centerY - radius, 0);
        int maxY = (int)Math.Max(centerY + radius, mapHeight - 1);

        for (int y = minY; y <= maxY; y++)
        {
            for (int x = minX; x <= maxX; x++)
            {
                var dx = x - centerX;
                var dy = y - centerY;
                if ((dx * dx + dy * dy) < radius * radius)
                {
                    var pixel = tmpImage.GetPixel(x, y);
                    // Only set it if the pixel is white
                    if (pixel.R > 0.8 && pixel.G > 0.8 && pixel.B > 0.8)
                    {
                        tmpImage.SetPixel(x, y, color);
                    }
                }
            }
        }
    }

    private void moveRobotSprite(Vector2 point, float rotation)
    {
        int centerX = (int)((point.X - mapOriginPos.X) / mapResolution);
        int centerY = (int)((point.Y - mapOriginPos.Y) / mapResolution);

        RobotSprite.Position = new(centerX * ImageScale, centerY * ImageScale);
        RobotSprite.Rotation = rotation + (MathF.PI / 2f);
    }

    private void drawMapFromData(bool clearMap)
    {
        if (clearMap)
        {
            tmpImage = Image.CreateEmpty((int)mapWidth, (int)mapHeight, false, Image.Format.Rgb8);
        }

        // tmpImage = Image.CreateEmpty(rosImageSize, rosImageSize, false, Image.Format.Rgb8);
        for (uint i = 0; i < mapWidth; i++)
        {
            for (uint j = 0; j < mapHeight; j++)
            {
                var mapIndex = (j * mapWidth) + i;
                // I want more defined lines in the map. So I am putting a ceiling on it.
                // 0.85 was a little less than the max value I saw, so I am using it as the lowest bound.
                // I also want to see if I can lower the threshold on the robot to get more defined edges.
                var rawValue = 1.0f - (mapData[mapIndex] / 255.0f);
                var value = (rawValue > 0.85f) ? 1.0f : 0.0f;

                // This is probably very slow, but it can work for now.
                // I think I could do this in a shader to make it a bit faster.
                Color pixelColor = new(value, value, value);
                tmpImage.SetPixel((int)i, (int)j, pixelColor);
            }
        }
    }

    // This is a latched topic, so it will only come through once. While localizing. Might be different in slam mode.
    private void mapCallback(nav_msgs.OccupancyGrid map)
    {
        drawMutex.Lock();
        mapData = map.data;
        mapWidth = map.info.width;
        mapHeight = map.info.height;
        mapResolution = map.info.resolution;
        // TODO: build godot with double support
        mapOriginPos.X = map.info.origin.position.x;
        mapOriginPos.Y = map.info.origin.position.y;

        mapOriginRot.X = (float)map.info.origin.orientation.x;
        mapOriginRot.Y = (float)map.info.origin.orientation.y;
        mapOriginRot.Z = (float)map.info.origin.orientation.z;
        mapOriginRot.W = (float)map.info.origin.orientation.w;

        robotPixelDia = (int)(PAL_DIA / mapResolution);
        drawMutex.Unlock();
    }
}
