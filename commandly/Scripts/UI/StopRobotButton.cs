// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;
using System.Threading;

public partial class StopRobotButton : RobotButton
{
    [Export]
    private PALControl palController;

    private bool threadRunning = false;

    private static System.Threading.Mutex mutex = new();

    public override void _Ready()
    {
        base._Ready();
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        Disabled |= threadRunning;
    }

    public override void _Pressed()
    {
        base._Pressed();
        threadRunning = true;
        Thread thread = new(networkThread);
        thread.Start();
    }

    private void networkThread()
    {
        mutex.WaitOne();
        palController.StopRobotModule();
        threadRunning = false;
        mutex.ReleaseMutex();
    }
}
