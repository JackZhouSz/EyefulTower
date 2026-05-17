// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

using sensor_msgs = RosSharp.RosBridgeClient.MessageTypes.Sensor;

public partial class Camera : TextureRect
{
    [Export]
    private float CameraScale = 1.5f;

    [Export]
    private int TabIndex = 0;

    [Export]
    private TabContainer menuTabContainer;

    private byte[] imgData;
    private uint imgWidth;
    private uint imgHeight;

    private int initW = 320;
    private int initH = 180;

    private Image tmpImage;
    private Image bufferImage;

    public override void _Ready()
    {
        base._Ready();
        CameraSubscriber.Subscribe(cameraCallback);

        tmpImage = Image.CreateEmpty(initW, initH, false, Image.Format.Rgb8);
    }

    // TODO: move this to a shader. It is pretty slow. But I think it's actually mostly network?
    // Framerate is pretty slow, but there is big delay.
    public override void _Process(double delta)
    {
        if (imgData != null && menuTabContainer.CurrentTab == TabIndex)
        {
            tmpImage = Image.CreateEmpty(initW, initH, false, Image.Format.Rgb8);
            var vals = imgHeight * imgWidth;
            int dataOffset;
            for (int i = 0; i < vals; ++i)
            {
                dataOffset = i * 3;
                float r = (float)(imgData[dataOffset] / 255.0f);
                float g = (float)(imgData[dataOffset + 1] / 255.0f);
                float b = (float)(imgData[dataOffset + 2] / 255.0f);

                Color pixelColor = new(r, g, b);

                var imgX = i % imgWidth;
                var imgY = i / imgWidth;

                tmpImage.SetPixel((int)imgX, (int)imgY, pixelColor);
            }

            tmpImage.Resize((int)(initW * CameraScale), (int)(initH * CameraScale));
            this.Texture = ImageTexture.CreateFromImage(tmpImage);

            // Setting this to null. We don't need to process every frame.
            imgData = null;
        }
    }

    private void cameraCallback(sensor_msgs.Image img)
    {
        imgData = img.data;
        imgWidth = img.width;
        imgHeight = img.height;
    }
}
