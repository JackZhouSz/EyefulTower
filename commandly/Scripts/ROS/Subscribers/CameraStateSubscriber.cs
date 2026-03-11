// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

using std_msgs = RosSharp.RosBridgeClient.MessageTypes.Std;

public partial class CameraStateSubscriber : ROSSubscriber<std_msgs.Int8>
{
    // I really want a more graceful way to handle messaging, but this can do.
    // I don't like internal signals because you need a reference to the object anyways. Getting that reference requires passing it, or searching.
    // Having, ironically, a ROS like interface would be really useful.
    private static Action<ROSManager.CameraState> cameraStateAction;

    private string subId;
    public override void _Ready()
    {
        base._Ready();

        this.Subscribe("/eyeful/camera_state", stateCallback);
    }

    private void stateCallback(std_msgs.Int8 state)
    {
        cameraStateAction((ROSManager.CameraState)state.data);
    }

    public static void Subscribe(Action<ROSManager.CameraState> newAction)
    {
        cameraStateAction += newAction;
    }
}
