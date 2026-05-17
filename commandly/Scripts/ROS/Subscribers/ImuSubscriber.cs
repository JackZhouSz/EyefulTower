// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

using sensor_msgs = RosSharp.RosBridgeClient.MessageTypes.Sensor;

public partial class ImuSubscriber : ROSSubscriber<sensor_msgs.Imu>
{
    private static Action<sensor_msgs.Imu> action;
    private string subId;
    public override void _Ready()
    {
        base._Ready();

        Subscribe("base_imu", imuCallback);
    }

    private void imuCallback(sensor_msgs.Imu pose)
    {
        action(pose);
    }

    public static void Subscribe(Action<sensor_msgs.Imu> newAction)
    {
        action += newAction;
    }
}
