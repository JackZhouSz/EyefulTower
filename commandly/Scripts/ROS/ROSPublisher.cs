// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using System;
using System.Collections.Generic;
using Godot;
using RosSharp.RosBridgeClient;

/**
    This is the base class for the ROS publishers. This represents a single publishing node.

    It enforces that a single publisher, publishes to a single topic. If you want multiple publishers,
    you need to make multiple Godot Nodes.

    You construct your app in the scene.
*/
public partial class ROSPublisher<T> : Node where T : Message
{
    [Export]
    protected int messageRate = 50;

    private string pubId;

    protected string topic;

    public void Advertise(string topicName)
    {
        topic = topicName;
        if (ROSManager.Instance.Connected)
        {
            // If it is connected, we just do the advertise
            pubId = ROSManager.Instance.rosSocket.Advertise<T>(topicName);
        }
        else
        {
            // If it is not connected, we add OnConnection to the queue for when it is.
            ROSManager.Instance.OnConnection += OnConnection;
        }
    }

    private void OnConnection()
    {
        // TODO: This isn't just a joy issue, but when we disconnect and reconnect, all ros things seems to be in
        // "catch up" where they will try to show what they missed, and it is causing lag. This is relaed to the
        // RealSense.
        if (pubId == null)
        {
            pubId = ROSManager.Instance.rosSocket.Advertise<T>(topic);
            GD.Print($"OnConnection null: {pubId}");
        }
        else
        {
            GD.Print("Publisher Reconnected");
            pubId = null;
            pubId = ROSManager.Instance.rosSocket.Advertise<T>(topic);
            GD.Print($"OnConnection Advertising: {pubId}");
        }
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
    }

    public void Publish(T msg)
    {
        if (ROSManager.Instance.Connected && pubId != null)
        {
            ROSManager.Instance.rosSocket?.Publish(pubId, msg);
        }
    }
}
