// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;
using System.Threading;
using RosSharp.RosBridgeClient;
using sensor_msgs = RosSharp.RosBridgeClient.MessageTypes.Sensor;

public partial class EmergencyStopButton : Button
{
    public static Action EmergencyStopPressed;

    private JoystickPublisher joyPublisher;

    private sensor_msgs.Joy joyMsg;

    private int messagesSent = 0;

    private bool sendStops = false;

    private string pubId;

    private bool leftTrigger = false;
    private bool rightTrigger = false;
    private bool rightBumper = false;

    public override void _Ready()
    {
        base._Ready();
        joyPublisher = new JoystickPublisher();
        joyPublisher.SetPiublishInProcess(false);

        joyMsg = new()
        {
            axes = new float[7],
            buttons = new int[15]
        };

        joyMsg.buttons[9] = 1;

        // pubId = ROSManager.Instance.rosSocket.Advertise<sensor_msgs.Joy>("/joy");
    }

    public override void _Pressed()
    {
        base._Pressed();
        if (!sendStops)
        {
            sendStops = true;
            GD.Print("ESTOP");
            pubId ??= ROSManager.Instance.rosSocket.Advertise<sensor_msgs.Joy>("/joy");
            Thread thread = new(networkedThread);
            thread.Start();

            EmergencyStopPressed?.Invoke();
        }
    }

    private void networkedThread()
    {
        PALControl.Instance.StopNavigation();
        PALControl.Instance.StopRobotModule();

        PALControl.Instance.StartNavigation();
        PALControl.Instance.StartRobotModule();
        sendStops = false;
    }

    public override void _Process(double delta)
    {
        base._Process(delta);
        // GD.Print($"Right: {Input.GetActionStrength("estop_down_right")}");
        if (rightBumper && rightTrigger && leftTrigger)
        {
            _Pressed();
        }

        if (sendStops)
        {
            // joyPublisher.Publish(joyMsg);
            if (ROSManager.Instance.Connected && pubId != null)
            {
                ROSManager.Instance.rosSocket?.Publish(pubId, joyMsg);
            }
        }
    }

    public override void _Input(InputEvent @event)
    {
        base._Input(@event);
        if (@event.IsAction("estop_down_right"))
        {
            if (@event.GetActionStrength("estop_down_right") >= 1.0)
            {
                rightTrigger = true;
            }
            else if (@event.GetActionStrength("estop_down_right") < 1.0)
            {
                rightTrigger = false;
            }
        }

        if (@event.IsAction("estop_down_left"))
        {
            if (@event.GetActionStrength("estop_down_left") >= 1.0)
            {
                leftTrigger = true;
            }
            else if (@event.GetActionStrength("estop_down_left") < 1.0)
            {
                leftTrigger = false;
            }
        }

        if (@event.IsAction("safety"))
        {
            if (@event.IsPressed())
            {
                rightBumper = true;
            }
            else if (@event.IsReleased())
            {
                rightBumper = false;
            }
        }
    }

}
