// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

public partial class CaptureButton : RobotButton
{
    private static Action preCaptureActions;

    private bool joystickOn = false;

    [Export]
    private bool MoveForward = true;

    public override void _Ready()
    {
        base._Ready();
        JoyPrioritySubscriber.Subscribe(OnJoyUpdate);
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        Disabled = joystickOn || !ready;
    }

    public override void _Pressed()
    {
        base._Pressed();
        preCaptureActions?.Invoke();

        CaptureService.CallService(MoveForward);
    }

    public static void AddPrecaptureAction(Action _preCaptureAction)
    {
        preCaptureActions += _preCaptureAction;
    }

    private void OnJoyUpdate(bool joystickOn)
    {
        this.joystickOn = joystickOn;
    }

}
