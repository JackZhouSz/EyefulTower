// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

public partial class CameraReadyIcon : HBoxContainer
{
    [Export]
    private Texture2D ready;

    [Export]
    private Texture2D waiting;

    [Export]
    private Texture2D error;

    [Export]
    private Texture2D noinfo;

    [Export]
    private TextureRect status;

    private Texture2D currentMode;
    private bool changed = true;

    public override void _Ready()
    {
        base._Ready();
        status.Texture = waiting;
        currentMode = waiting;
        CameraStateSubscriber.Subscribe(OnStateUpdate);
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        status.Texture = currentMode;
    }



    private void OnStateUpdate(ROSManager.CameraState state)
    {
        currentMode = state switch
        {
            ROSManager.CameraState.READY => ready,
            ROSManager.CameraState.WAITING => waiting,
            ROSManager.CameraState.ERROR => error,
            _ => noinfo,
        };
        changed = true;
    }
}
