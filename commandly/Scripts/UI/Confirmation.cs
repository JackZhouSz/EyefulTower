// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

// TODO: maybe make a more generic manager for dialogs. I will likely wnat one of these for each type of error.
// trying to have everything use 1, even on the same thread, can cause things to get out of sync.
public partial class Confirmation : Panel
{
    [Export]
    private Label label;

    [Export]
    private Control dialogAnswers;

    private Action yesAction;
    private Action noAction;

    public void MakeVisible(Action yesAction, Action noAction, string label, bool showButtons)
    {
        this.Visible = true;
        this.yesAction = yesAction;
        this.noAction = noAction;
        this.label.Text = label;
        dialogAnswers.Visible = showButtons;
    }

    public void Close()
    {
        yesAction = null;
        noAction = null;
        Visible = false;
        dialogAnswers.Visible = false;
        this.label.Text = "";
    }

    public override void _Process(double delta)
    {
        base._Process(delta);

        if (this.Visible)
        {
            if (Input.IsActionJustPressed("ui_cancel"))
            {
                noAction();
                // GD.Print("Cancel");
            }

            if (Input.IsActionJustPressed("ui_accept"))
            {
                yesAction();
                // GD.Print("Accept");
            }
        }
    }
}
