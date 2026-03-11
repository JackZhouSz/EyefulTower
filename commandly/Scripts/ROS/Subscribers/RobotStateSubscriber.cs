// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;
using System.Threading;
using std_msgs = RosSharp.RosBridgeClient.MessageTypes.Std;

public partial class RobotStateSubscriber : ROSSubscriber<std_msgs.Int8>
{
    // I really want a more graceful way to handle messaging, but this can do.
    // I don't like internal signals because you need a reference to the object anyways. Getting that reference requires passing it, or searching.
    // Having, ironically, a ROS like interface would be really useful.
    private static Action<ROSManager.CaptureState> captureStateAction;

    [Export]
    Confirmation confirmationPanel;

    [Export(PropertyHint.MultilineText)]
    private string errorDialogue;

    private Godot.Mutex stateMutex = new();
    private ROSManager.CaptureState currentState;

    private double timeSinceLastUpdate = 0.0;

    private bool isInError = false;

    private double timeout = 10;

    private string subId;
    public override void _Ready()
    {
        base._Ready();

        this.Subscribe("/eyeful/capture_state", stateCallback);
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        timeSinceLastUpdate += delta;

        if (timeSinceLastUpdate > timeout)
        {
            captureStateAction(ROSManager.CaptureState.ERROR);
            GD.Print($"Broken. Time since last update: {timeSinceLastUpdate}");
            timeSinceLastUpdate = 0.0;
            // CheckError(ROSManager.CaptureState.ERROR);
        }

        // Should I be locking and unloacking every frame?
        stateMutex.Lock();
        CheckError(currentState);
        stateMutex.Unlock();
    }

    private void stateCallback(std_msgs.Int8 state)
    {
        captureStateAction((ROSManager.CaptureState)state.data);
        timeSinceLastUpdate = 0.0;
        // CheckError((ROSManager.CaptureState)state.data);
        stateMutex.Lock();
        currentState = (ROSManager.CaptureState)state.data;
        stateMutex.Unlock();
    }

    private void CheckError(ROSManager.CaptureState newState)
    {
        if (newState == ROSManager.CaptureState.ERROR && !isInError)
        {
            isInError = true;
            // Do the popup
            confirmationPanel.MakeVisible(yesOptoion, noOption, errorDialogue, true);
        }
        else if (newState != ROSManager.CaptureState.ERROR)
        {
            isInError = false;
        }
    }

    public static void Subscribe(Action<ROSManager.CaptureState> newAction)
    {
        captureStateAction += newAction;
    }

    private void noOption()
    {
        confirmationPanel.Close();
    }

    private void yesOptoion()
    {
        confirmationPanel.Close();
        Thread thread = new(yesThread);
        thread.Start();
    }

    private void yesThread()
    {
        PALControl.Instance.RestartRobotModule();
    }
}
