// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System.Threading;

public partial class StartMappingButton : Button
{
    readonly string STOP_LABEL = "Stop Mapping";
    readonly string START_LABEL = "Start Mapping";

    private bool isMapping = false;

    private bool threadRunning = false;

    private static System.Threading.Mutex mutex = new();

    [Export]
    private SlamMapContainer slamMapContainer;

    public override void _Ready()
    {
        base._Ready();
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        Disabled = threadRunning;
    }

    public override void _Pressed()
    {
        base._Pressed();
        isMapping = !isMapping;

        if (isMapping)
        {
            this.Text = STOP_LABEL;
            slamMapContainer.GetSLAMMap().StartMapUpdates();
            threadRunning = true;
            Thread thread = new(networkThread);
            thread.Start();
        }
        else
        {
            this.Text = START_LABEL;
            slamMapContainer.GetSLAMMap().StopMapUpdates();
        }

    }

    private void networkThread()
    {
        mutex.WaitOne();
        PALControl.Instance.StopSlam();
        PALControl.Instance.StartSlam();
        threadRunning = false;
        GD.Print("DONE");
        mutex.ReleaseMutex();
    }
}
