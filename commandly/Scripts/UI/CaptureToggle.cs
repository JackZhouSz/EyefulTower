// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

using std_srvs = RosSharp.RosBridgeClient.MessageTypes.Std;

public partial class CaptureToggle : CheckButton
{
    private bool init = false;

    public override void _Ready()
    {
        base._Ready();
        Disabled = false;

        // CaptureTypeService.SubscribeToService(callback);
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        if (!init)
        {
            init = true;
            // Doing it on the first frame. It is weird with running right after subscribing the callback.
            // CaptureTypeService.CallService(CaptureTypeService.CaptureType.SINGLE);
        }
    }

    public override void _Toggled(bool toggledOn)
    {
        base._Toggled(toggledOn);

        if (toggledOn)
        {
            CaptureTypeService.CallService(CaptureTypeService.CaptureType.DOUBLE);
        }
        else
        {
            CaptureTypeService.CallService(CaptureTypeService.CaptureType.SINGLE);
        }
    }

    private void callback(std_srvs.SetBool_Response response)
    {
        // GD.Print(response.message);
    }
}
