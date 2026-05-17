// Copyright (c) Meta Platforms, Inc. and affiliates.

using System;
using Godot;
using RosSharp.RosBridgeClient;
using sensor_msgs = RosSharp.RosBridgeClient.MessageTypes.Sensor;

// There is some bug where joystick gets turned off in some restart cases. Not sure what.
// Could be a race condition on start up of the app when the robot is already running.

public partial class JoystickPublisher : ROSPublisher<sensor_msgs.Joy>
{

    private string pubId;

    private double messageWait;

    private double timeSinceLastMessage;

    private bool isCapturing = false;

    private bool joystickOn = true;

    private bool publishInProcess = true;

    private bool isAdvertising = false;

    // The mutex should be locked to each frame.
    // If I recieve a message mid frame, it should be processed next frame.
    private Mutex priorityMutex = new();
    private bool startSendingToggle = false;

    public override void _Ready()
    {
        base._Ready();
        if (Input.GetConnectedJoypads().Count > 0)
        {
            this.Advertise("/joy");
            isAdvertising = true;
        }

        messageWait = 1 / messageRate;

        RobotStateSubscriber.Subscribe(StateCallback);
        JoyPrioritySubscriber.Subscribe(OnJoyStateCallback);

        Input.JoyConnectionChanged += OnJoyConnectionChanged;
    }

    public override void _Process(double delta)
    {
        priorityMutex.Lock();
        base._Process(delta);

        if (publishInProcess && !isCapturing && timeSinceLastMessage >= messageWait && Input.GetConnectedJoypads().Count > 0)
        {
            timeSinceLastMessage = 0;

            sensor_msgs.Joy joyMsg = new()
            {
                axes = new float[7],
                buttons = new int[15]
            };

            joyMsg.buttons[9] = ToggleJoystick() ? 1 : 0;

            // I only want to capture if the joystick is not active and I am not capturing.
            if (joystickOn)
            {
                // Default to split stick, where left is forward back, right is rotation
                float analogForward = Input.GetAxis("left_stick_down", "left_stick_up");
                float dpadForward = Input.GetAxis("dpad_down", "dpad_up");
                float forward = analogForward + dpadForward;

                float analogRotation = Input.GetAxis("right_stick_right", "right_stick_left");
                float dpadRotation = Input.GetAxis("dpad_right", "dpad_left");
                float rotation = analogRotation + dpadRotation;

                bool safety = Input.IsActionPressed("safety");

                joyMsg.axes[1] = forward;
                joyMsg.axes[2] = rotation;
                joyMsg.buttons[5] = safety ? 1 : 0;
            }

            // GD.Print(joyMsg);
            Publish(joyMsg);
        }

        timeSinceLastMessage += delta;
        priorityMutex.Unlock();
    }

    private void OnJoyConnectionChanged(long device, bool connected)
    {
        if (!isAdvertising)
        {
            this.Advertise("/joy");
            isAdvertising = true;
        }
    }

    public void SetPiublishInProcess(bool publish)
    {
        publishInProcess = publish;
    }

    private bool ToggleJoystick()
    {
        if (!startSendingToggle)
        {
            startSendingToggle = Input.IsActionJustPressed("auto_toggle");
        }

        return startSendingToggle;
    }

    private void StateCallback(ROSManager.CaptureState captureState)
    {
        isCapturing = captureState == ROSManager.CaptureState.CAPTURING;
    }

    private void OnJoyStateCallback(bool joystickOn)
    {
        priorityMutex.Lock();
        this.joystickOn = joystickOn;
        startSendingToggle = false;
        priorityMutex.Unlock();
    }
}
