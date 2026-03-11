// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

using std_msgs = RosSharp.RosBridgeClient.MessageTypes.Std;

public partial class JoyPrioritySubscriber : ROSSubscriber<std_msgs.Bool>
{
    private static Action<bool> action;

    private string subId;
    public override void _Ready()
    {
        base._Ready();

        this.Subscribe("joy_priority", stateCallback);
    }

    private void stateCallback(std_msgs.Bool state)
    {
        action(state.data);
    }

    public static void Subscribe(Action<bool> newAction)
    {
        action += newAction;
    }
}
