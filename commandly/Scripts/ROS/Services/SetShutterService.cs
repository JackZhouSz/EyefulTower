// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

using eyeful_ros = RosSharp.RosBridgeClient.MessageTypes.EyefulRos;

public partial class SetShutterService : Node
{
    private static Action<eyeful_ros.SetShutterResponse> subAction;

    private static string serviceId;

    public override void _Ready()
    {
    }

    private static void callback(eyeful_ros.SetShutterResponse response)
    {
        subAction(response);
    }

    public static void SubscribeToService(Action<eyeful_ros.SetShutterResponse> newAction)
    {
        subAction += newAction;
    }

    public static void CallService(string shutter, ROSManager.BatchId batchId)
    {
        var shutterMsg = new eyeful_ros.SetShutterRequest
        {
            batch_id = (int)batchId,
            shutter = shutter
        };
        serviceId = ROSManager.Instance.rosSocket.CallService<eyeful_ros.SetShutterRequest, eyeful_ros.SetShutterResponse>("/eyeful/set_shutter", callback, shutterMsg);
    }
}
