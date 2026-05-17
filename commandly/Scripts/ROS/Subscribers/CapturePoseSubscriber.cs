// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

using eyeful_msgs = RosSharp.RosBridgeClient.MessageTypes.EyefulRos;

/**
    I will implement this as a box around the robot. It will be the immediate like, 10 feet?
    So as you move, it will scroll through the map and show that.

    I will need to get the robot position and base it off of that. 
*/

public partial class CapturePoseSubscriber : ROSSubscriber<eyeful_msgs.CapturePoseList>
{
    private static Action<eyeful_msgs.CapturePoseList> mapAction;
    private string subId;
    public override void _Ready()
    {
        base._Ready();
        // Each message is a single position, but every position is sent each capture
        Subscribe("/eyeful/capture_positions", msgCallback);
    }

    private void msgCallback(eyeful_msgs.CapturePoseList pos)
    {
        mapAction(pos);
    }

    public static void Subscribe(Action<eyeful_msgs.CapturePoseList> newAction)
    {
        mapAction += newAction;
    }
}
