// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

public partial class Config : PanelContainer
{
    [Export]
    private CaptureDropdown captureDropdown;

    [Export]
    private DriveModeDropdown driveMode1;

    [Export]
    private DriveModeDropdown driveMode2;

    public static Config Instance { get; private set; }

    public override void _EnterTree()
    {
        base._EnterTree();

        if (Instance != null && Instance != this)
        {
            QueueFree();
        }
        else
        {
            Instance = this;
        }
    }

    public int GetImageCountPerCapture()
    {
        string captureDropdownOp = captureDropdown.GetItemText(captureDropdown.Selected);
        string driveMode1Op = driveMode1.GetItemText(driveMode1.Selected);
        string driveMode2Op = driveMode2.GetItemText(driveMode2.Selected);

        // Last character is always the number of images taken. It won't ever be double digits.
        int driveMode1Size = driveMode1Op[^1..].ToInt();

        int count = driveMode1Size;
        if (captureDropdownOp.Equals("double", StringComparison.CurrentCultureIgnoreCase))
        {
            int driveMode2Size = driveMode2Op[^1..].ToInt();
            count += driveMode2Size;
        }
        return count;
    }
}
