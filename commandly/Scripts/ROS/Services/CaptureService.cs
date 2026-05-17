// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

using std_srvs = RosSharp.RosBridgeClient.MessageTypes.Std;
using eyeful_ros = RosSharp.RosBridgeClient.MessageTypes.EyefulRos;

public partial class CaptureService : Node
{
    private static Action<eyeful_ros.TriggerCaptureResponse> subAction;

    private static string serviceId;

    private static void callback(eyeful_ros.TriggerCaptureResponse response)
    {
        subAction?.Invoke(response);
    }

    public static void SubscribeToService(Action<eyeful_ros.TriggerCaptureResponse> newAction)
    {
        subAction += newAction;
    }

    public static void CallService(bool moveForward)
    {
        // I didn't realize these were blocking in that way. I assumed if nothing existed, it would error, or error in to the callback.
        var msg = new eyeful_ros.TriggerCaptureRequest();
        msg.move_forward = moveForward;
        serviceId = ROSManager.Instance.rosSocket.CallService<eyeful_ros.TriggerCaptureRequest, eyeful_ros.TriggerCaptureResponse>("/eyeful/capture", callback, msg);
    }
}
