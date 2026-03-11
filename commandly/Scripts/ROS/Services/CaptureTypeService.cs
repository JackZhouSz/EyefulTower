// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

using std_srvs = RosSharp.RosBridgeClient.MessageTypes.Std;

public partial class CaptureTypeService : Node
{
    public enum CaptureType
    {
        DOUBLE = 1,
        SINGLE = 0,
    }

    private static Action<std_srvs.SetBool_Response> subAction;

    private static string serviceId;

    private static void callback(std_srvs.SetBool_Response response)
    {
        subAction?.Invoke(response);
    }

    public static void SubscribeToService(Action<std_srvs.SetBool_Response> newAction)
    {
        subAction += newAction;
    }

    public static void CallService(CaptureType captureType)
    {
        var msg = new std_srvs.SetBool_Request
        {
            data = captureType == CaptureType.DOUBLE
        };

        // and not hold up the whole app. Calling these on their own thread could help, and then a timeout to kill the thread if it doesn't
        // complete.
        // I didn't realize these were blocking in that way. I assumed if nothing existed, it would error, or error in to the callback.
        serviceId = ROSManager.Instance.rosSocket.CallService<std_srvs.SetBool_Request, std_srvs.SetBool_Response>("/eyeful/set_capture_type", callback, msg);
    }
}
