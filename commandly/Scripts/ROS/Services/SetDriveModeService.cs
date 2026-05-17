// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

using eyeful_ros = RosSharp.RosBridgeClient.MessageTypes.EyefulRos;

public partial class SetDriveModeService : Node
{
    private static Action<eyeful_ros.SetDriveModeResponse> subAction;

    private static string serviceId;

    public override void _Ready()
    {
    }

    private static void callback(eyeful_ros.SetDriveModeResponse response)
    {
        subAction(response);
    }

    public static void SubscribeToService(Action<eyeful_ros.SetDriveModeResponse> newAction)
    {
        subAction += newAction;
    }

    public static void CallService(int driveMode, ROSManager.BatchId batchId)
    {
        var driveModeMsg = new eyeful_ros.SetDriveModeRequest
        {
            batch_id = (int)batchId,
            drive_mode = driveMode
        };
        serviceId = ROSManager.Instance.rosSocket.CallService<eyeful_ros.SetDriveModeRequest, eyeful_ros.SetDriveModeResponse>("/eyeful/set_drive_mode", callback, driveModeMsg);
    }
}
