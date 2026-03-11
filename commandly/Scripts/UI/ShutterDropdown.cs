// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

using eyeful_ros = RosSharp.RosBridgeClient.MessageTypes.EyefulRos;

public partial class ShutterDropdown : RobotOptionButton
{

    public override void _Ready()
    {
        base._Ready();
        Disabled = false;

        SetShutterService.SubscribeToService(callback);

        Connect("item_selected", new Godot.Callable(this, "_OnItemSelected"));
        CaptureButton.AddPrecaptureAction(SubmitCurrentValue);
        // SetShutterService.CallService(GetItemText(GetSelectedId()), batchId);
    }

    public void SubmitCurrentValue()
    {
        SetShutterService.CallService(GetItemText(GetSelectedId()), batchId);
    }

    private void _OnItemSelected(int item)
    {
        var selected = GetItemText(item);
        SetShutterService.CallService(selected, batchId);
    }

    private void callback(eyeful_ros.SetShutterResponse response)
    {
        GD.Print(response.message);
    }
}
