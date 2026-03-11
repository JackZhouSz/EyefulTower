// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

using std_srvs = RosSharp.RosBridgeClient.MessageTypes.Std;

public partial class SdFormatterService : Node
{
    private static Action<std_srvs.Trigger_Response> subAction;

    private static string serviceId;

    public override void _Ready()
    {
    }

    private static void callback(std_srvs.Trigger_Response response)
    {
        subAction(response);
    }

    public static void SubscribeToService(Action<std_srvs.Trigger_Response> newAction)
    {
        subAction += newAction;
    }

    public static void CallService()
    {
        serviceId = ROSManager.Instance.rosSocket.CallService<std_srvs.Trigger_Request, std_srvs.Trigger_Response>("/eyeful/format_cameras", callback, new std_srvs.Trigger_Request());
    }
}
