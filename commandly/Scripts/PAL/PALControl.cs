// (c) Meta Platforms, Inc. and affiliates. Confidential and proprietary.

using Godot;
using Renci.SshNet;
using System;
using System.Net.NetworkInformation;
using System.Threading;


// Rename to like "PALNetworkManager". This will setup the SSH connections, and validate that the robot is connected.
public partial class PALControl : Node
{
    public enum SLAMMode
    {
        LOCAL,
        SLAM,
        NONE
    }

    public static PALControl Instance { get; private set; }

    private const string ENV = "source init-pal-env && ";
    private const string PAL_MODULE_START = ENV + "pal module start ";
    private const string PAL_MODULE_RESTART = ENV + "pal module restart ";
    private const string PAL_MODULE_STOP = ENV + "pal module stop ";
    private const string PAL_MODULE_INFO = ENV + "pal module info ";
    private const string LOCALIZATION = "localization";
    private const string SLAM = "slam";
    private const string eyeful_ros_MODULE = "eyeful_ros_module";
    private const string RUNNING = "RUNNING";
    private const string STOPPED = "STOPPED";


    private bool firstConnection = true;
    private bool connected = false;

    private double timeSinceLastTry = 0;

    private int timeOutRetry = 0;

    private double timeout = 10.0;

    private string ip;

    private SshClient palClient;

    private Ping connectPing;

    private PingOptions pingOptions;

    private System.Threading.Mutex timeoutMutex = new();

    private SLAMMode mode;

    public SLAMMode GetCurrentMode()
    {
        return mode;
    }

    public int? StartLocalization()
    {
        var stopStatus = StopSlam();
        if (StopSlam() == 0)
        {
            int? exit = palClient.RunCommand(PAL_MODULE_START + LOCALIZATION).ExitStatus;
            if (exit == 0)
            {
                mode = SLAMMode.LOCAL;
            }
            return exit;
        }
        else
        {
            GD.PrintErr("ERROR: Could not stop the slam module. Not starting localization.");
            return stopStatus;
        }
    }

    public int? StartSlam()
    {
        var stopStatus = StopLocalization();
        if (StopLocalization() == 0)
        {
            int? exit = palClient.RunCommand(PAL_MODULE_START + SLAM).ExitStatus;
            if (exit == 0)
            {
                mode = SLAMMode.SLAM;
            }
            return exit;
        }
        else
        {
            GD.PrintErr("ERROR: Could not stop the localization module. Not starting slam.");
            return stopStatus;
        }
    }

    public int? RestartNavigation()
    {
        var command = palClient.RunCommand(PAL_MODULE_RESTART + "navigation");

        return command.ExitStatus;
    }

    public int? StopNavigation()
    {
        var command = palClient.RunCommand(PAL_MODULE_STOP + "navigation");

        return command.ExitStatus;
    }

    public int? StartNavigation()
    {
        var command = palClient.RunCommand(PAL_MODULE_START + "navigation");

        return command.ExitStatus;
    }

    public int? StopRobotModule()
    {
        var command = palClient.RunCommand(PAL_MODULE_STOP + eyeful_ros_MODULE);
        if (command.ExitStatus == 0)
        {
            mode = SLAMMode.NONE;
        }
        return command.ExitStatus;
    }

    public int? StartRobotModule()
    {
        var command = palClient.RunCommand(PAL_MODULE_START + eyeful_ros_MODULE);
        if (command.ExitStatus == 0)
        {
            mode = SLAMMode.NONE;
        }
        return command.ExitStatus;
    }

    public int? RestartRobotModule()
    {
        var command = palClient.RunCommand(PAL_MODULE_RESTART + eyeful_ros_MODULE);
        if (command.ExitStatus == 0)
        {
            mode = SLAMMode.NONE;
        }
        return command.ExitStatus;
    }

    public int? StopLocalization()
    {
        var command = palClient.RunCommand(PAL_MODULE_STOP + LOCALIZATION);
        if (command.ExitStatus == 0)
        {
            mode = SLAMMode.NONE;
        }
        return command.ExitStatus;
    }

    public int? StopSlam()
    {
        var command = palClient.RunCommand(PAL_MODULE_STOP + SLAM);
        return command.ExitStatus;
    }

    public int? StopAllMapping()
    {
        var stopSlam = StopSlam();
        if (stopSlam == 0)
        {
            return StopLocalization();
        }
        else
        {
            return stopSlam;
        }
    }

    public bool IsLocalizationRunning()
    {
        var command = palClient.RunCommand(PAL_MODULE_INFO + LOCALIZATION);
        return command.Result.Contains(RUNNING);
    }

    public bool IsSlamRunning()
    {
        var command = palClient.RunCommand(PAL_MODULE_INFO + SLAM);
        return command.Result.Contains(RUNNING);
    }

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
        string palUser = OS.GetEnvironment("PAL_USER");
        string palPass = OS.GetEnvironment("PAL_PASS");

        if (palIp != null && palPass != null && palUser != null)
        {
            palClient = new SshClient(palIp, palUser, palPass);
            ip = palIp;
        }
        else
        {
            GD.PrintErr("PAL Environment variables not set. Not starting SSH server.");
        }

        connectPing = new();
        connectPing.PingCompleted += new PingCompletedEventHandler(PingCallback);
        pingOptions = new(64, true);
    }

    public override void _Process(double delta)
    {
        base._Process(delta);

        if (!connected)
        {
            TryConnect(delta);
        }
        else
        {
            TestConnect(delta);
        }
    }

    private void TryConnect(double delta)
    {
        if (timeSinceLastTry > 1.0)
        {
            try
            {
                palClient.Connect();
                connected = true;
                if (firstConnection)
                {
                    Thread thread = new(FirstConnectionProcess);
                    thread.Start();
                }
                GD.Print("Connected");
            }
            catch (Exception e)
            {
                GD.Print($"SSH not connected: {e}");
            }
            timeSinceLastTry = 0;
        }
        timeSinceLastTry += delta;
    }

    private void FirstConnectionProcess()
    {
        // if (!IsLocalizationRunning()) {
        //     StopAllMapping();
        //     StartSlam();
        // }
        firstConnection = false;
    }

    public bool IsConnected()
    {
        return connected;
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

    public override void _ExitTree()
    {
        base._ExitTree();

        palClient?.Disconnect();
    }

    private void DoPing(double _timeout)
    {
        int timeout = (int)(_timeout * 1000);
        connectPing.SendAsync(ip, timeout, pingOptions);
    }

    private void PingCallback(object sender, PingCompletedEventArgs pingEvent)
    {
        // If there are no issues, and I am not connected, connect
        if (pingEvent.Error == null && pingEvent.Reply.Status == IPStatus.Success && !connected)
        {
            connected = true;
            timeoutMutex.WaitOne();
            timeOutRetry = 0;
            timeout = 10.0;
            timeoutMutex.ReleaseMutex();
            GD.Print("SSH Connected.");
        }
        else if (pingEvent.Error != null || pingEvent.Reply.Status != IPStatus.Success)
        {
            // If we timeout, we retry. Keep a counter and on 5 fails, we let it fail.
            if (pingEvent.Error == null && pingEvent.Reply.Status == IPStatus.TimedOut && timeOutRetry < 3)
            {
                timeoutMutex.WaitOne();
                timeOutRetry++;
                timeout = 2.0;
                timeoutMutex.ReleaseMutex();
                GD.Print($"SSH Timeout. Retry: {timeOutRetry}");
                return;
            }
            timeoutMutex.WaitOne();
            timeOutRetry = 0;
            timeoutMutex.ReleaseMutex();

            if (palClient.IsConnected)
            {
                palClient.Disconnect();
            }

            connected = false;
            GD.Print("SSH Connection failed. Retrying.");
        }
    }
}
