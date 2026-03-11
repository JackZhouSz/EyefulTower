// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

using nav_msgs = RosSharp.RosBridgeClient.MessageTypes.Nav;
using geo_msgs = RosSharp.RosBridgeClient.MessageTypes.Geometry;
using std_srvs = RosSharp.RosBridgeClient.MessageTypes.Std;
using System.Collections.Generic;

using eyeful_msgs = RosSharp.RosBridgeClient.MessageTypes.EyefulRos;

public partial class ApproxImages : MarginContainer
{
    [Export]
    private Label CountLabel;

    private int imageCount = 0;

    private bool updated = true;

    private Mutex drawMutex = new();

    public override void _Ready()
    {
        CapturePoseSubscriber.Subscribe(getCapturePosition);
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        if (updated)
        {
            drawMutex.Lock();
            CountLabel.Text = $"Camera Images:\n{imageCount}";
            updated = false;
            drawMutex.Unlock();
        }
    }

    private void getCapturePosition(eyeful_msgs.CapturePoseList poses)
    {
        drawMutex.Lock();
        updated = true;
        imageCount = poses.capture_poses.Length * 3 * Config.Instance.GetImageCountPerCapture();
        drawMutex.Unlock();
    }
}
