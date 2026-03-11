// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

using std_srvs = RosSharp.RosBridgeClient.MessageTypes.Std;

public partial class CaptureDropdown : RobotOptionButton
{

    public override void _Ready()
    {
        base._Ready();
        Disabled = false;

        CaptureTypeService.SubscribeToService(callback);

        Connect("item_selected", new Godot.Callable(this, "_OnItemSelected"));
        CaptureButton.AddPrecaptureAction(SubmitCurrentValue);
    }

    public void SubmitCurrentValue()
    {
        CaptureTypeService.CallService((CaptureTypeService.CaptureType)GetSelectedId());
    }

    private void _OnItemSelected(int item)
    {
        var selected = GetSelectedId();
        CaptureTypeService.CallService((CaptureTypeService.CaptureType)selected);
    }

    private void callback(std_srvs.SetBool_Response response)
    {
        GD.Print(response.message);
    }
}
