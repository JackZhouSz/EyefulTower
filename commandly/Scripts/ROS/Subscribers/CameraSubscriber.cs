// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

using sensor_msgs = RosSharp.RosBridgeClient.MessageTypes.Sensor;

public partial class CameraSubscriber : ROSSubscriber<sensor_msgs.Image>
{

    private static Action<sensor_msgs.Image> subAction;
    private string subId;
    public override void _Ready()
    {
        base._Ready();

        Subscribe("/camera/camera/color/image_raw", imageCallback);
    }

    private void imageCallback(sensor_msgs.Image img)
    {
        subAction(img);
    }

    public static void Subscribe(Action<sensor_msgs.Image> newAction)
    {
        subAction += newAction;
    }

}
