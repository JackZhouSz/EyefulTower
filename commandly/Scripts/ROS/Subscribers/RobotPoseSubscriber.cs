// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

using geo_msgs = RosSharp.RosBridgeClient.MessageTypes.Geometry;

/**
    I will implement this as a box around the robot. It will be the immediate like, 10 feet?
    So as you move, it will scroll through the map and show that.

    I will need to get the robot position and base it off of that. 
*/

public partial class RobotPoseSubscriber : ROSSubscriber<geo_msgs.Pose>
{
    private static Action<geo_msgs.Pose> mapAction;
    private string subId;
    public override void _Ready()
    {
        base._Ready();

        // Each message is a single position, but every position is sent each capture
        Subscribe("/eyeful/pose", msgCallback);
    }

    private void msgCallback(geo_msgs.Pose pose)
    {
        mapAction(pose);
    }

    public static void Subscribe(Action<geo_msgs.Pose> newAction)
    {
        mapAction += newAction;
    }
}
