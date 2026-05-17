// Copyright (c) Meta Platforms, Inc. and affiliates.

using System;
using System.Collections.Generic;
using Godot;
using RosSharp.RosBridgeClient;
using RosSharp.RosBridgeClient.Protocols;

/**
    This is the base class for the ROS subscriber. This represents a single subscribing node.

    You construct your app in the scene.
*/
public partial class ROSSubscriber<T> : Node where T : Message
{
    [Export]
    protected int messageRate = 50;

    private string subId;

    protected string topic;

    protected SubscriptionHandler<T> callback;

    private RosSocket rosSocket;

    public override void _Ready()
    {
        base._Ready();
    }

    protected void Subscribe(string topicName, SubscriptionHandler<T> callback)
    {
        this.callback = callback;
        topic = topicName;
        if (ROSManager.Instance.Connected)
        {
            // If it is connected, we just do the advertise
            subId = ROSManager.Instance.rosSocket.Subscribe(topic, callback);
        }
        else
        {
            // If it is not connected, we add OnConnection to the queue for when it is.
            ROSManager.Instance.OnConnection += OnConnection;
        }
        // var ws = new WebSocketNetProtocol("ws://10.42.0.1:9090");
        // rosSocket = new(ws);
        // subId = rosSocket.Subscribe(topic, callback);
    }

    private void OnConnection()
    {
        // If subId is null, it is first connection, if it is not, we are most likely reconnecting.
        // So we always want to resubscribe. It seems like on disconnection everything is cleaned up?
        subId = ROSManager.Instance.rosSocket.Subscribe(topic, callback);
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
    }
}
