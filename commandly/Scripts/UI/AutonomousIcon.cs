// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

public partial class AutonomousIcon : HBoxContainer
{

    [Export]
    private Texture2D autonomousMode;

    [Export]
    private Texture2D joystickMode;

    [Export]
    private TextureRect status;

    private Texture2D currentMode;
    private bool changed = true;

    public override void _Ready()
    {
        base._Ready();
        status.Texture = joystickMode;
        currentMode = joystickMode;
        JoyPrioritySubscriber.Subscribe(OnStateUpdate);
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        status.Texture = currentMode;
    }



    // Note: don't do graphics in these call backs.
    private void OnStateUpdate(bool joystickOn)
    {
        currentMode = joystickOn ? joystickMode : autonomousMode;
    }

}
