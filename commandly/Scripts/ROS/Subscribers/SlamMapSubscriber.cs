// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

using nav_msgs = RosSharp.RosBridgeClient.MessageTypes.Nav;

/**
    I will implement this as a box around the robot. It will be the immediate like, 10 feet?
    So as you move, it will scroll through the map and show that.

    I will need to get the robot position and base it off of that. 
*/

public partial class SlamMapSubscriber : ROSSubscriber<nav_msgs.OccupancyGrid>
{
    private static Action<nav_msgs.OccupancyGrid> mapAction;
    private string subId;
    private bool firstConnected = true;

    public override void _Ready()
    {
        base._Ready();

        Subscribe("/map", mapCallback);
    }

    public override void _Process(double delta)
    {
        base._Process(delta);

        if (firstConnected && PALControl.Instance.IsConnected())
        {
            firstConnected = false;
            // Subscribe("/map", mapCallback);
        }
    }

    private void mapCallback(nav_msgs.OccupancyGrid map)
    {
        mapAction(map);
    }

    public static void Subscribe(Action<nav_msgs.OccupancyGrid> newAction)
    {
        mapAction += newAction;
    }
}
