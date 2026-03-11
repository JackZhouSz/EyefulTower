// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;
using System.Threading;
using System.Threading.Tasks;
using eyeful_ros = RosSharp.RosBridgeClient.MessageTypes.EyefulRos;

public partial class AdvancedNavigation : PanelContainer
{
    [Export]
    private SlamMapContainer slamMapContainer;

    private int failures = 0;

    private bool capturing = false;

    private System.Threading.Mutex captureMutex = new();
    private System.Threading.Mutex slamMapMutex = new();

    private AutoResetEvent captureEvent = new(false);

    private eyeful_ros.SendCapturePoseResponse currResponse;

    private bool actionSuccess = false;

    private CaptureActionClient captureActionClient;

    public override void _Ready()
    {
        base._Ready();
        RobotStateSubscriber.Subscribe(OnStateUpdate);
        captureActionClient = new();
        captureActionClient.SubscribeToResult(actionCallback);
        captureActionClient.Initialize();
        this.VisibilityChanged += OnviSibilityChanged;
    }

    private void EmergencyStop()
    {
        this.slamMapMutex.ReleaseMutex();
        this.captureMutex.ReleaseMutex();
    }

    private void OnviSibilityChanged()
    {
        slamMapContainer.GetSLAMMap().FetchMap();
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        // GD.Print($"Active?: {this.Visible}");
    }

    public void ClearGoals()
    {
        slamMapMutex.WaitOne();
        slamMapContainer.GetSLAMMap().ClearGoalPoints();
        slamMapMutex.ReleaseMutex();
    }

    public void RemovePreviousGoal()
    {
        slamMapMutex.WaitOne();
        slamMapContainer.GetSLAMMap().RemoveLastPoint();
        slamMapMutex.ReleaseMutex();
    }

    public bool GetCapturing()
    {
        captureMutex.WaitOne();
        bool _capturing = capturing;
        captureMutex.ReleaseMutex();
        return _capturing;
    }

    public void StartCapture()
    {
        if (!capturing)
        {
            capturing = true;
            failures = 0;
            new Task(captureLoop).Start();
        }
    }

    private void captureLoop()
    {
        slamMapMutex.WaitOne();
        slamMapContainer.GetSLAMMap().CanPlaceGoals(false);
        // Making a new collection incase this is a pointer effected by the removed
        var points = slamMapContainer.GetSLAMMap().GetGoalPoints().ToArray();
        foreach (var point in points)
        {
            GD.Print($"Sending point: {point.X} {point.Y}");
            // SendCapturePoseService.CallService(point);
            captureActionClient.SendPoint(point);
            captureEvent.WaitOne();

            // currResponse should be set
            if (!actionSuccess)
            {
                failures++;
            }
            else
            {
                // slamMapContainer.GetSLAMMap().AddCapturePosition(point);
                slamMapContainer.GetSLAMMap().RemovePoint(point);
            }
        }
        slamMapContainer.GetSLAMMap().CanPlaceGoals(true);
        slamMapMutex.ReleaseMutex();
        GD.Print($"Failures: {failures}");
        captureMutex.WaitOne();
        capturing = false;
        captureMutex.ReleaseMutex();
    }

    private void actionCallback(bool success)
    {
        actionSuccess = success;
        captureEvent.Set();
    }

    protected virtual void OnStateUpdate(ROSManager.CaptureState state)
    {
        captureMutex.WaitOne();
        capturing = state == ROSManager.CaptureState.CAPTURING;
        captureMutex.ReleaseMutex();
    }
}
