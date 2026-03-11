// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;
using RosSharp.RosBridgeClient.MessageTypes.EyefulRos;

using RosSharp.RosBridgeClient.Actionlib;
using RosSharp.RosBridgeClient.MessageTypes.Action;
using RosSharp.RosBridgeClient.Protocols;

public partial class CaptureActionClient : ActionClient<AdvNavPoseAction, AdvNavPoseActionGoal, AdvNavPoseActionResult, AdvNavPoseActionFeedback, AdvNavPoseGoal, AdvNavPoseResult, AdvNavPoseFeedback>
{
    private Action<bool> resultAction;

    public CaptureActionClient()
    {
        this.actionName = "/eyeful/send_capture_pose_action";
        // TODO: This could be a bug with ROS2 action clients in ROS#. They don't seem to like
        // sharing the websocket. Could be ID collisions, but it won't start the action if it is
        // on the shared socket. Creating a new socket for action clients.
        var ws = new WebSocketNetProtocol("ws://10.42.0.1:9090");
        rosSocket = new(ws);
        // this.rosSocket = ROSManager.Instance.rosSocket;

        action = new AdvNavPoseAction();
        goalStatus = new GoalStatus();
    }

    public override AdvNavPoseActionGoal GetActionGoal()
    {
        return action.action_goal;
    }

    public override void SetActionGoal(AdvNavPoseGoal goal, bool feedback = true, int fragmentSize = int.MaxValue, string compression = "none")
    {
        action.action_goal.action = this.actionName;
        action.action_goal.args = goal;
        action.action_goal.feedback = feedback;
        action.action_goal.fragment_size = fragmentSize;
        action.action_goal.compression = compression;
    }

    public void SendPoint(Vector2 point)
    {
        AdvNavPoseGoal advNavPoseGoal = new();
        advNavPoseGoal.pose.position.x = point.X;
        advNavPoseGoal.pose.position.y = point.Y;
        advNavPoseGoal.pose.position.z = 0.0f;

        advNavPoseGoal.pose.orientation.x = 0.0f;
        advNavPoseGoal.pose.orientation.y = 0.0f;
        advNavPoseGoal.pose.orientation.z = 0.0f;
        advNavPoseGoal.pose.orientation.w = 1.0f;

        this.SetActionGoal(advNavPoseGoal);
        this.SendGoal();
    }

    protected override void OnFeedbackReceived()
    {
        // throw new NotImplementedException();
    }

    private void callback(bool success)
    {
        resultAction(success);
    }

    public void SubscribeToResult(Action<bool> newAction)
    {
        resultAction += newAction;
    }

    protected override void OnResultReceived()
    {
        callback(action.action_result.values.finished);
    }

    protected override void OnStatusUpdated()
    {
        // throw new NotImplementedException();
    }
}
