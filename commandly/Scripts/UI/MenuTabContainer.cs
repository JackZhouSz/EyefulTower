// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

public partial class MenuTabContainer : TabContainer
{
    [Export]
    private Control configFirstFocus;

    [Export]
    private Control sensorFirstFocus;

    [Export]
    private Control advNavFirstFocus;

    private int lastTab = 0;
    private Control lastFocus;
    private bool joystickOn = false;
    private bool update = false;

    public override void _Ready()
    {
        base._Ready();
        Action<Control> callback = this.OnFocusChanged;
        GetViewport().Connect("gui_focus_changed", Callable.From(callback));
        FocusMode = FocusModeEnum.All;
        TabFocusMode = FocusModeEnum.All;
        lastTab = CurrentTab;
        GetTabBar().GrabFocus();

        JoyPrioritySubscriber.Subscribe(OnJoyPriorityCallback);
    }

    private void OnJoyPriorityCallback(bool joystickOn)
    {
        if (this.joystickOn != joystickOn)
        {
            this.joystickOn = joystickOn;
            update = true;
        }
    }


    public override void _Process(double delta)
    {
        base._Process(delta);

        if (update)
        {
            if (joystickOn)
            {
                FocusMode = FocusModeEnum.None;
                TabFocusMode = FocusModeEnum.None;
                lastTab = CurrentTab;
                // CurrentTab = 0;
            }
            else
            {
                FocusMode = FocusModeEnum.All;
                TabFocusMode = FocusModeEnum.All;
                // CurrentTab = lastTab;
                lastFocus?.GrabFocus();
            }
            update = false;
        }

        ProcessInput();
    }

    public void GetFocus()
    {
        FocusMode = FocusModeEnum.All;
        TabFocusMode = FocusModeEnum.All;
        GetTabBar().GrabFocus();
    }

    public void LoseFocus()
    {
        FocusMode = FocusModeEnum.None;
        TabFocusMode = FocusModeEnum.None;
        // GetCurrentTabControl().ReleaseFocus();
    }

    private void ProcessInput()
    {
        if (!joystickOn && FocusMode != FocusModeEnum.None)
        {
            if (Input.IsActionJustPressed("ui_right_tab"))
            {
                SelectNextAvailable();
                // GetCurrentTabControl().FocusMode = FocusModeEnum.All;
                GetTabBar().GrabFocus();
                SetNextNeighbor();
            }

            if (Input.IsActionJustPressed("ui_left_tab"))
            {
                SelectPreviousAvailable();
                // GetCurrentTabControl().FocusMode = FocusModeEnum.All;
                GetTabBar().GrabFocus();
                SetNextNeighbor();
            }
        }
    }

    private void SetNextNeighbor()
    {
        string tabName = GetTabBar().GetTabTitle(CurrentTab);

        if (tabName == "Config")
        {
            GetTabBar().FocusNeighborBottom = configFirstFocus.GetPath();
        }
        else if (tabName == "Sensors")
        {
            GetTabBar().FocusNeighborBottom = sensorFirstFocus.GetPath();
        }
        // else if (tabName == "AdvNav")
        // {
        //     GetTabBar().FocusNeighborBottom = advNavFirstFocus.GetPath();
        // }
    }

    private void OnFocusChanged(Control control)
    {
        lastFocus = control;
    }
}
