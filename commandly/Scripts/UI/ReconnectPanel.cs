// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;

public partial class ReconnectPanel : Panel
{
    public override void _Ready()
    {
        base._Ready();
        this.Visible = false;
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        this.Visible = !ROSManager.Instance.Connected;
    }
}
