// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

using eyeful_ros = RosSharp.RosBridgeClient.MessageTypes.EyefulRos;

public partial class DriveModeDropdown : RobotOptionButton
{

    public override void _Ready()
    {
        base._Ready();
        Disabled = false;

        SetDriveModeService.SubscribeToService(callback);

        Connect("item_selected", new Godot.Callable(this, "_OnItemSelected"));
        // SetDriveModeService.CallService(GetSelectedId(), batchId);
        CaptureButton.AddPrecaptureAction(SubmitCurrentValue);
    }


    public void SubmitCurrentValue()
    {
        SetDriveModeService.CallService(GetSelectedId(), batchId);
    }

    private void _OnItemSelected(int item)
    {
        var selected = GetSelectedId();
        SetDriveModeService.CallService(selected, batchId);
    }

    private void callback(eyeful_ros.SetDriveModeResponse response)
    {
        GD.Print(response.message);
    }
}
