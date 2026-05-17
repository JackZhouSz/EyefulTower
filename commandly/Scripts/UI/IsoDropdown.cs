// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

using eyeful_ros = RosSharp.RosBridgeClient.MessageTypes.EyefulRos;

public partial class IsoDropdown : RobotOptionButton
{

    public override void _Ready()
    {
        base._Ready();
        Disabled = false;

        SetIsoService.SubscribeToService(callback);

        Connect("item_selected", new Godot.Callable(this, "_OnItemSelected"));
        // SetIsoService.CallService(GetSelectedId(), batchId);
        CaptureButton.AddPrecaptureAction(SubmitCurrentValue);
    }

    public void SubmitCurrentValue()
    {
        SetIsoService.CallService(GetSelectedId(), batchId);
    }

    private void _OnItemSelected(int item)
    {
        var selected = GetSelectedId();
        SetIsoService.CallService(selected, batchId);
    }

    private void callback(eyeful_ros.SetIsoResponse response)
    {
        GD.Print(response.message);
    }
}
