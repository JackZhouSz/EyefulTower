// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

public partial class AutonomousStatus : ColorRect
{

    [Export]
    private Color autonomousMode = new(0, 1, 0);

    [Export]
    private Color joystickMode = new(1, 0, 0);

    private Color currentColor;
    private bool changed = true;

    public override void _Ready()
    {
        base._Ready();
        Color = joystickMode;
        currentColor = joystickMode;
        JoyPrioritySubscriber.Subscribe(OnStateUpdate);
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        Color = currentColor;
    }



    // Note: don't do graphics in these call backs.
    private void OnStateUpdate(bool joystickOn)
    {
        currentColor = joystickOn ? joystickMode : autonomousMode;
    }
}
