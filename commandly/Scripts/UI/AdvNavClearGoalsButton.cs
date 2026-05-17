// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

public partial class AdvNavClearGoalsButton : AdvNavButton
{
    public override void _Pressed()
    {
        base._Pressed();
        // AdvNavController.ClearGoals();
    }
}
