// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using System;
using System.Net.NetworkInformation;
using RosSharp.RosBridgeClient;
using RosSharp.RosBridgeClient.Protocols;
using System.Text;


/**
    This needs a rework. I want to to be able to start the app, and wait for connection.
    That might involve having the subscribers and things using this to submit an action like
    "OnConnection" that will do the init stuff once we have a connection. And this will retry in
    process until it connects? Also should probably be a singleton.
*/

public partial class ROSManager : Node
{

    public static ROSManager Instance { get; private set; }

    public enum CaptureState
    {
        ERROR = -1,
        READY = 0,
        CAPTURING = 1,
        FORMATTING = 2,
        NOT_READY = 3,
    }

    public enum CameraState
    {
        ERROR = -1,
        READY = 0,
        WAITING = 1,
    }

    public enum BatchId
    {
        FIRST = 0,
        SECOND = 1
    }

    // Static IP of the PAL robot
    private static string ip = "10.42.0.1";
    private static readonly string port = "9090";
    private static string uri = "ws://10.42.0.1:9090";

    private bool connected = false;

    private double timeSinceLastTry = 10000;

    private double timeout = 10.0;

    private double reconnectTime = 5.0;

    private int timeOutRetry = 0;

    private Ping connectPing;

    private PingOptions pingOptions;

    private System.Threading.Mutex timeoutMutex = new();

    public RosSocket rosSocket { get; private set; }

    public Action OnConnection { get; set; }

    public bool Connected { get; private set; }

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

        string palIp = OS.GetEnvironment("PAL_IP");

        if (palIp != null)
        {
            ip = palIp;
            uri = $"ws://{ip}:{port}";
        }

        connectPing = new();
        connectPing.PingCompleted += new PingCompletedEventHandler(PingCallback);
        pingOptions = new(64, true);
    }

    public override void _Process(double delta)
    {
        base._Process(delta);

        if (!Connected)
        {
            TryConnect(delta);
        }
        else
        {
            TestConnect(delta);
        }
    }

    public override void _ExitTree()
    {
        base._ExitTree();
        rosSocket.Close();
    }

    private void TryConnect(double delta)
    {
        if (timeSinceLastTry > reconnectTime)
        {
            timeSinceLastTry = 0;
            // The websocket almost seems to segfault when it tries to connect to an IP that isn't connected.
            // I will want to report this bug.
            DoPing(reconnectTime);
        }
        timeSinceLastTry += delta;
    }

    private void TestConnect(double delta)
    {
        timeoutMutex.WaitOne();
        if (timeSinceLastTry > timeout)
        {
            DoPing(timeout);
            timeSinceLastTry = 0;
        }
        timeSinceLastTry += delta;
        timeoutMutex.ReleaseMutex();
    }

    private void DoPing(double _timeout)
    {
        int timeout = (int)(_timeout * 1000);
        connectPing.SendAsync(ip, timeout, pingOptions);
    }

    private void PingCallback(object sender, PingCompletedEventArgs pingEvent)
    {
        // If there are no issues, and I am not connected, connect
        if (pingEvent.Error == null && pingEvent.Reply.Status == IPStatus.Success && !Connected)
        {
            var ws = new WebSocketNetProtocol(uri);
            rosSocket = new(ws);
            Connected = true;
            // Reset the timeout on a successful connection
            timeoutMutex.WaitOne();
            timeout = 10.0;
            timeOutRetry = 0;
            timeoutMutex.ReleaseMutex();
            // It is on the subscribers to handle if it reconnects
            OnConnection();
        }
        else if (pingEvent.Error != null || pingEvent.Reply.Status != IPStatus.Success)
        {
            // If we timeout, we retry. Keep a counter and on 5 fails, we let it fail.
            if (pingEvent.Error == null && pingEvent.Reply.Status == IPStatus.TimedOut && timeOutRetry < 3)
            {
                GD.Print($"ROS Timeout. Retry: {timeOutRetry}");
                // We shorten the timeout so we fail a bit faster.
                timeoutMutex.WaitOne();
                timeout = 2.0;
                timeOutRetry++;
                timeoutMutex.ReleaseMutex();
                return;
            }

            // Reset the timeout on a full failure
            timeoutMutex.WaitOne();
            timeout = 10.0;
            timeoutMutex.ReleaseMutex();

            Connected = false;
            GD.Print("ROS Connection failed. Reconnecting.");
            try
            {
                rosSocket?.Close();
            }
            catch (Exception)
            {
                GD.Print("ROS connection closed.");
            }
        }
    }
}
