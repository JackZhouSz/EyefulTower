// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

using eyeful_ros = RosSharp.RosBridgeClient.MessageTypes.EyefulRos;

public partial class SetIsoService : Node
{
    private static Action<eyeful_ros.SetIsoResponse> subAction;

    private static string serviceId;

    public override void _Ready()
    {
    }

    private static void callback(eyeful_ros.SetIsoResponse response)
    {
        subAction(response);
    }

    public static void SubscribeToService(Action<eyeful_ros.SetIsoResponse> newAction)
    {
        subAction += newAction;
    }

    public static void CallService(int iso, ROSManager.BatchId batchId)
    {
        var isoMsg = new eyeful_ros.SetIsoRequest
        {
            batch_id = (int)batchId,
            iso = iso
        };
        serviceId = ROSManager.Instance.rosSocket.CallService<eyeful_ros.SetIsoRequest, eyeful_ros.SetIsoResponse>("/eyeful/set_iso", callback, isoMsg);
    }
}
