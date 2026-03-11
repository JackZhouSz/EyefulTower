// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

using geo_msgs = RosSharp.RosBridgeClient.MessageTypes.Geometry;

public partial class AMCLPoseSubscriber : ROSSubscriber<geo_msgs.PoseWithCovarianceStamped>
{
    private static Action<geo_msgs.PoseWithCovarianceStamped> poseAction;
    private string subId;
    public override void _Ready()
    {
        base._Ready();

        Subscribe("amcl_pose", poseCallback);
    }

    private void poseCallback(geo_msgs.PoseWithCovarianceStamped pose)
    {
        poseAction?.Invoke(pose);
    }

    public static void Subscribe(Action<geo_msgs.PoseWithCovarianceStamped> newAction)
    {
        poseAction += newAction;
    }
}
