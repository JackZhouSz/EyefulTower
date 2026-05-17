// Copyright (c) Meta Platforms, Inc. and affiliates.

using Godot;
using System;

using std_srvs = RosSharp.RosBridgeClient.MessageTypes.Std;

public partial class FormatButton : RobotButton
{

    [Export(PropertyHint.MultilineText)]
    private string dialogueValue;

    [Export]
    Confirmation confirmationPanel;

    [Export]
    private MenuTabContainer tabContainer;


    private string labelValue;

    private bool formatting = false;

    private bool reset = false;

    public override void _Ready()
    {
        base._Ready();
        Disabled = false;
        formatting = false;

        SdFormatterService.SubscribeToService(callback);
        RobotStateSubscriber.Subscribe(StateCallback);
        confirmationPanel.Close();
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        Disabled = formatting || !ready;

        if (reset && !formatting)
        {
            reset = false;
            // label.Text = labelValue;
            // dialogAnswers.Visible = true;
            // confirmationPanel.Visible = false;
            confirmationPanel.Close();
            tabContainer.GetFocus();
            GD.Print("RESET");
        }
    }

    private void StateCallback(ROSManager.CaptureState captureState)
    {
        formatting = captureState == ROSManager.CaptureState.FORMATTING;
    }

    private void callback(std_srvs.Trigger_Response response)
    {
        reset = true;
        formatting = true;
    }

    public override void _Pressed()
    {
        base._Pressed();
        formatting = true;
        confirmationPanel.MakeVisible(yesPressed, noPressed, dialogueValue, true);
        tabContainer.LoseFocus();
    }

    private void noPressed()
    {
        formatting = false;
        confirmationPanel.Close();
        tabContainer.GetFocus();
    }

    private void yesPressed()
    {
        SdFormatterService.CallService();
        formatting = true;
        // dialogAnswers.Visible = false;
        // label.Text = "Formatting...";
        confirmationPanel.MakeVisible(yesPressed, noPressed, "Formatting...", false);
    }

}
