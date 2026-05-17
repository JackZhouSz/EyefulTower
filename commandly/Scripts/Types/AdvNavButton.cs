// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

public partial class AdvNavButton : Button
{
    [Export]
    protected AdvancedNavigation AdvNavController;

    public override void _Ready()
    {
        base._Ready();
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        Disabled = AdvNavController.GetCapturing();
    }
}
