// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

public partial class RobotButton : Button
{
    [Export]
    protected bool activeOnError = false;
    protected bool ready = false;

    public override void _Ready()
    {
        base._Ready();
        Disabled = false;

        RobotStateSubscriber.Subscribe(OnStateUpdate);
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        Disabled = !ready;
    }

    protected virtual void OnStateUpdate(ROSManager.CaptureState state)
    {
        if (activeOnError)
        {
            ready = state == ROSManager.CaptureState.READY || state == ROSManager.CaptureState.ERROR;
        }
        else
        {
            ready = state == ROSManager.CaptureState.READY;
        }
    }
}
