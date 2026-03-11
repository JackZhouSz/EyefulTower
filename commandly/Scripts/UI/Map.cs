// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

using nav_msgs = RosSharp.RosBridgeClient.MessageTypes.Nav;
using geo_msgs = RosSharp.RosBridgeClient.MessageTypes.Geometry;
using sensor_msgs = RosSharp.RosBridgeClient.MessageTypes.Sensor;

public partial class Map : TextureRect
{
    [Export]
    private Sprite2D robotAvatar;

    [Export]
    private int uiImageSize = 250;

    [Export]
    private Container centerContainer;

    private sbyte[] mapData;
    private uint mapWidth;
    private uint mapHeight;

    private Vector3 robotPosition = new();

    private float yaw = 0;

    private Image tmpImage;

    private int rosImageSize = 100;

    public override void _Ready()
    {
        base._Ready();
        LocalCostmapSubscriber.Subscribe(mapCallback);
        // RobotPoseSubscriber.Subscribe(robotPoseCallback);
        ImuSubscriber.Subscribe(robotImuCallback);

        tmpImage = Image.CreateEmpty(rosImageSize, rosImageSize, false, Image.Format.Rgb8);

        centerContainer.SetSize(new(uiImageSize, uiImageSize));
    }

    public override void _Process(double delta)
    {
        if (mapData != null)
        {
            // tmpImage?.Free();
            tmpImage = Image.CreateEmpty(rosImageSize, rosImageSize, false, Image.Format.Rgb8);
            for (uint i = 0; i < rosImageSize; i++)
            {
                for (uint j = 0; j < rosImageSize; j++)
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

            tmpImage.Resize(uiImageSize, uiImageSize);
            this.Texture = ImageTexture.CreateFromImage(tmpImage);
        }

        robotAvatar.GlobalRotation = yaw;
    }

    // This is a latched topic, so it will only come through once. While localizing. Might be different in slam mode.
    private void mapCallback(nav_msgs.OccupancyGrid map)
    {
        mapData = map.data;
        mapWidth = map.info.width;
        mapHeight = map.info.height;
    }

    private void robotPoseCallback(geo_msgs.PoseWithCovarianceStamped pose)
    {
        var position = pose.pose.pose.position;
        robotPosition.X = (float)position.x;
        robotPosition.Y = (float)position.y;
        robotPosition.Z = (float)position.z;

        var orientation = pose.pose.pose.orientation;
        Quaternion quat = new((float)orientation.x, (float)orientation.y, (float)orientation.z, (float)orientation.w);

        yaw = quat.GetEuler().Z;
    }

    private void robotImuCallback(sensor_msgs.Imu imu)
    {
        var orientation = imu.orientation;
        Quaternion quat = new((float)orientation.x, (float)orientation.y, (float)orientation.z, (float)orientation.w);

        // I think this has it working with the new arrow asset.
        // I think there is some possiblity of user error because the localcostmap will move, which is a little disorienting.
        // So I might need a different way to do it. But, this is correct as of now.
        // Arrow asset: https://upload.wikimedia.org/wikipedia/commons/b/bd/Eo_circle_blue_arrow-right.svg
        yaw = (-quat.GetEuler().Z) + (MathF.PI / 4);
    }
}
