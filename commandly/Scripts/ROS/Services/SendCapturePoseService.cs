// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

using eyeful_ros = RosSharp.RosBridgeClient.MessageTypes.EyefulRos;

public partial class SendCapturePoseService : Node
{
    private static Action<eyeful_ros.SendCapturePoseResponse> subAction;

    private static string serviceId;

    private static void callback(eyeful_ros.SendCapturePoseResponse response)
    {
        subAction?.Invoke(response);
    }

    public static void SubscribeToService(Action<eyeful_ros.SendCapturePoseResponse> newAction)
    {
        subAction += newAction;
    }

    public static void CallService(Vector2 position)
    {
        var msg = new eyeful_ros.SendCapturePoseRequest();
        msg.pose.position.x = position.X;
        msg.pose.position.y = position.Y;
        msg.pose.position.z = 0;

        msg.pose.orientation.x = 0.0;
        msg.pose.orientation.y = 0.0;
        msg.pose.orientation.z = 0.0;
        msg.pose.orientation.w = 1.0;

        // I didn't realize these were blocking in that way. I assumed if nothing existed, it would error, or error in to the callback.
        serviceId = ROSManager.Instance.rosSocket.CallService<eyeful_ros.SendCapturePoseRequest, eyeful_ros.SendCapturePoseResponse>("/eyeful/send_capture_pose", callback, msg);
    }
}
