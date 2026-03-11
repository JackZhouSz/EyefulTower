// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

public partial class CaptureIcon : HBoxContainer
{
    [Export]
    private Texture2D ready;

    [Export]
    private Texture2D capturing;

    [Export]
    private Texture2D waitingConnection;

    [Export]
    private Texture2D noinfo;

    [Export]
    private TextureRect status;

    private Texture2D currentMode;
    private bool changed = true;

    public override void _Ready()
    {
        base._Ready();
        status.Texture = waitingConnection;
        currentMode = waitingConnection;
        RobotStateSubscriber.Subscribe(OnStateUpdate);
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        status.Texture = currentMode;
    }



    private void OnStateUpdate(ROSManager.CaptureState state)
    {
        currentMode = state switch
        {
            ROSManager.CaptureState.READY => ready,
            ROSManager.CaptureState.CAPTURING => capturing,
            _ => noinfo,
        };
        changed = true;
    }
}
