// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;
using System.Threading;

/**
    This button will control whether to stop or start slam or localization.

    Cases to handle:
    1. Localization on
        * Button is "Start Slam"
    2. Slam on
        * Button is "Start Localization"
    3. Neither
        * Button is "Start Localization"
    4. Both
        *  Button is "Stop Both" and is red

    Maybe I should add a status area that can also reflect this
*/
public partial class MappingStateButton : Button
{
    private const string START_MAPPING = "Start Mapping";
    private const string STOP_MAPPING = "Stop Mapping";

    private static System.Threading.Mutex mutex = new();

    [Export]
    private PALControl palController;

    private bool slamActive = false;
    private bool localActive = false;
    private Func<int?> buttonFunction;
    private bool threadRunning = false;
    private string newText = "";

    public override void _Ready()
    {
        base._Ready();
        slamActive = palController.IsSlamRunning();
        localActive = palController.IsLocalizationRunning();
        SetState();
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        Disabled = threadRunning;

        if (!Disabled)
        {
            this.Text = newText;
        }
    }

    private void SetState()
    {
        if (slamActive && !localActive)
        {
            newText = STOP_MAPPING;
            buttonFunction = palController.StartLocalization;
        }
        else if (localActive && !slamActive)
        {
            newText = START_MAPPING;
            buttonFunction = palController.StartSlam;
        }
        else if (!localActive && !slamActive)
        {
            newText = START_MAPPING;
            buttonFunction = palController.StartLocalization;
        }
        else
        {
            newText = "Mapping State Issue...";
            buttonFunction = palController.StopAllMapping;
            Disabled = true;
        }
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
        buttonFunction();
        slamActive = palController.IsSlamRunning();
        localActive = palController.IsLocalizationRunning();
        SetState();
        threadRunning = false;
        mutex.ReleaseMutex();
    }

}
