# Sony A1 Camera Upgrade Process

# Introduction

This will be the process needed to update each camera on the Eyeful Tower to Firmware version 3.01 from version 1.32.

An overview of the Robot to get to know the Eyeful Tower. There are 14 Sony a1 cameras on the stack on top of a robotic base. There are also 2 smaller Intel Realsense cameras, these should not be removed from the robot.

Each camera has a static IP address associated with it, and should stay in the relative position it was originally pulled from. Each mount is also marked with an ID on the box the charging cable each camera will be attached to. Here is a handy table to IP to ID for reference:

| ID | IP |
| :---- | :---- |
| 1 | 192.168.1.40 |
| 2 | 192.168.1.41 |
| 3 | 192.168.1.42 |
| 4 | 192.168.1.43 |
| 5 | 192.168.1.44 |
| 6 | 192.168.1.45 |
| 7 | 192.168.1.46 |
| 8 | 192.168.1.47 |
| 9 | 192.168.1.48 |
| 10 | 192.168.1.49 |
| 11 | 192.168.1.50 |
| 12 | 192.168.1.51 |
| 13 | 192.168.1.52 |
| 14 | 192.168.1.53 |

This table appears later as well during the reinstallation process.

# Camera Removal

There are 13 total cameras that need upgrades, and all need their settings changed. Camera 1 is already on the correct firmware, but needs its settings changed.

While we could keep the cameras on the robot, it may be easier to remove multiple cameras to update and place back. We will want to keep at least 1 camera on the robot for development purposes. When removing the cameras, the robot and cameras should be turned off.

I would suggest removing cameras from the bottom up, as that makes removal easier. They can be removed by unscrewing 4 allen key bolts.

![][image1]

We shouldn’t need to remove the lens protectors during this process, and batteries and chargers will be provided.

## Firmware Update Part 1

Your laptop will need to have USB access. If you are on Mac, it will also need some additional permissions for kernel driver execution, which is explained in the Sony docs for install. I would suggest doing this on a Windows computer, drivers make it a slightly easier process.

The basic overview is that the firmware needs to be installed sequentially.

The cameras are on version 1.32. So, part 1 of the process will look like:

1. Upgrade from v1.32 \-\> v1.35
2. Upgrade from v1.35 \-\> v2.01

Make sure to check the camera firmware before starting the upgrade. This can be done by going to **Menu** → **Setup (Yellow Toolbox)** → **Setup Options** → **Version**. If the version is v3.01, you can skip to the “Post Upgrade Settings” tab.

For now, you can follow the Sony instructions on the 1.32 \-\> 1.35 \-\> 2.01 upgrade:

* [Mac Firmware installation instructions](https://www.sony.com/electronics/support/e-mount-body-ilce-1-series/ilce-1/software/00260271) (Start at the Preparation section)
* [Windows Firmware installation instructions](https://www.sony.com/electronics/support/e-mount-body-ilce-1-series/ilce-1/software/00260268) (Start at the Preparation section)

Depending on the platform you are using, driver install will differ. Once the drivers are installed, keep these in mind:

* Close all other application software before updating the system software.
* Use a fully charged rechargeable battery pack (**NP-FZ100**).
* Do not remove the battery during the update as the sudden loss of power may render the camera inoperable.
* Remove the memory card from the camera before starting the update process.
* The system software update will take **approximately 15 minutes**. Do not allow your computer to go into **Sleep** mode during this time.
  **Note:** If the computer does go into **Sleep** mode and the update is interrupted, the entire update process will need to be restarted.
* Do not connect the camera to any other device except your computer.
* Do not connect the camera and computer until instructed to do so.
* Ensure that your computer is connected to the internet.
* Follow the instructions in the **System Software Updater** window:
  On the camera, select **Menu** → **Setup** → **USB** → **USB Connection**, and then check if **Mass Storage** has been selected. If a mode other than **Mass Storage** is selected, select **Mass Storage**.

In testing, I have seen it take between 15 to 30 minutes. Keep that in mind when doing updates.

## Firmware Update Part 2

The camera(s) should be on firmware version 2.01 at this point.

The next stage will be a little different. We will be loading a DAT file on to the SD cards of the cameras, and then going through a different process. You can download the DAT file, or it will be provided in the Firmware section of these docs.

You will want to use the card in Slot 1 of the camera(s) you are updating. Once, you have that, you can follow these steps to install it:
[Firmware v3.01 Upgrade](https://www.sony.com/electronics/support/e-mount-body-ilce-1-series/ilce-1/software/00343095)

The basic overview is the camera will look in the SD card for the new firmware file, and will allow you to install it from the **Menu** → **Setup (Yellow Toolbox)** → **Setup Options** → **Version** screen.

A couple things to keep in mind:

* The camera will go fully black. This is Ok. The instructions will mention blink codes to keep an eye out for while the update is happening.
* Don’t worry about deleting the DAT file. We will format the cameras again before using them.

Once the camera is upgraded to firmware v3.01, you can move on to the Post Upgrade Settings tab to finish the setup process.

NOTE: We are using the SD Card from camera 1\. It has been reattached, it just needs the SD card back in it.

# Post Upgrade Settings

After you have a camera update to firmware v3.01, you will want to apply the settings needed for captures.

Once you turn the camera back on after the upgrade, it will ask for setting up using an app or connecting to a phone. Skip all of those dialogs. You can also set the time and date at this time. Use MM/DD/YYY for the date option.

## Software Settings

These will be the settings that will be needed for each section in the camera. Each dropdown below will correspond to the section in the camera’s settings. Any Grey options in the list below can be ignored. Also, if the option is in the camera, but not this list, it can also be ignored.

Alternatively to manual setting, you can also load them from the SD card used to updated the camera. {Put those steps here}.

### Shooting

1. Image Quality
   1. JPEG/HEIF Switch: JPEG
   2. Image Quality Settings:
      1. File Format: RAW & JPEG (RAW+J)
      2. RAW File Type: lossless compressed raw (RAW L)
      3. JPEG Quality: X-Fine
      4. JPEG Image Size: 50M
   3. Long exposure NR: Off
      1. NOTE: Need to be in single shot mode (top left knob) and in Auto Shutter mode to change this setting. At this point, Auto Shutter should be set, make sure to set the left knob to the single square. You need to press the middle button of the knob to be able to turn it.
   4. Color Space: AdobeRGB
   5. Lens compensation \-\> leave default (Shading Auto/ChromAb Auto/Dist. Off)
2. Media
   1. Rec. Media Settings
      1. \[Image\] Recording Media: Simult. Recording
      2. Auto Switch Media: On
3. File
   1. File/Folder Settings
      1. File Number: Reset
   2. Copyright Info
      1. Write Copyright Info: On
      2. Set Photographer: "Retfab {ID}".
         1.  ID Will be on the front of the camera on the right side under the "a1" logo.
         2. WARNING: This is NOT loaded with the SD card settings.
      3. Set Copyright: (leave blank)
   3. Write Serial Number: On
4. Shooting Mode
5. Drive Mode
   1. Bracket Settings
      1. Bracket Type: Cont. Bracket 1.0EV9
      2. Selftimer during Bracket: Off
      3. Bracket order: set to “- → 0 → \+”
6. Shutter/Silent
   1. Shutter Type: Electronic Shutter
   2. Anti-flicker Set.: Off
7. Image Stabilization
8. Zoom
9. Shooting Display
   1. Grid Line Display: On

### Exposure/Color

1. Exposure
   1. ISO 500
2. Exposure Comp
3. Metering
   1. Metering Mode: Multi
   2. Face Priority in Multi Metering: Off
4. Flash
5. White balance
   1. White balance: Day White
6. Color/tone
   1. D-Range Optimizer: Off
   2. Creative look: ST
7. Zebra display
   1. Zebra display on
   2. Zebra level: 95

### Focus

1. AF/MF
2. Focus Area
3. Face/Eye af
4. Focus Assistant
5. Peaking Display
   1. Peaking Display: On
   2. Peaking Color: Yellow

### Playback

   Nothing

### Network

1. Cnct./Remote Sht.
   1. Smartphone Connection
   2. Remote Shoot Function
      1. Remote Shooting: On
      2. Connect without Pairing: Enable
   3. Remote Shoot Setting
      1. Still Img. Save Dest.: Camera Only
      2. Save Image size: 2M
      3. Save JPEG Size: Large Size
2. FTP Transfer
   1. FTP Transfer Func.
      1. FTP Function: On
      2. Server Setting: Server 1
         1. Display Name: host
         2. Destination Settings:
            1. Host Name: 192.168.1.00
            2. Secure Protocol: off
            3. Port: 21
         3. Directory Settings
            1. Specify Directory: Last digit of IP address
            2. Directory Hierarchy: Standard
            3. Same File Name: Does not overwrite
         4. Passive Mode: On
   2. FTP Transfer (Take a picture so this option is available)
      1. Target Group: All Media
   3. Auto FTP Transfer: Off
   4. RAW+J/H Transfer Target: Raw+J & RAW+H
   5. Transfer JPEG Size: Large Size
   6. Transfer Target: Proxy Only
   7. FTP Power Save: Off
3. Wired LAN
   1. Wired LAN Connect: On
   2. IP Address Setting
      1. IP Address Setting: Manual
      2. IP Address: (Look at yellow sticker on camera)
      3. Subnet Mask: 255.255.255.0
      4. Default Gateway: 192.168.1.1
4. Network Option
   1. Access Authen. Settings: Off
      1. NOTE: To turn this Off, you need to go to Wired LAN \-\> Wired LAN Connect \-\> Off. After you set Access Authen. Settings to Off, turn Wired LAN Connect back On
      2. NOTE: Check that Connect Without Pairing is Enabled. Changing this setting seems to Disable that.

### Setup

1. Area/Date
   1. Check that area/date/time looks correct
2. Reset/Save settings
3. Operation Customize
   1. Custom Key settings (still images, first in the list)
   2. Rear1 (5): FTP Transfer (you need to navigate to Network-\>Transfer/Remote-\>FTP Transfer to find it in the selection menu)
4. Dial Customize
   1. Lock Operation Parts: All
5. Touch Operation
   1. Touch Operation: Off
6. Finder/Monitor
   1. Display Quality: High
   2. Finder frame rate: Standard
7. Display Option
8. Power Setting Option
   1. Power Save Start Time: 5min
9. Sound option
   1. Volume Settings: 1
10. USB
11. External Output
12. Setup Option
    1. IR remote control: Off
    2. Auto Pixel mapping: On

## Physical Knobs

Validate that the camera knobs match the ones in these images:
![][image2]![][image3]

## Post Software Setup

After all of the settings are set, you can validate them against the example camera.

You likely removed the camera from the robot, you will need to place the camera back on the correct mount. Before reinstalling cameras, make sure the robot, and all cameras are turned off before reinstalling a camera.

Each mount will have an ID on the charging box with a number. Below is a table of IP to ID:

| ID | IP |
| :---- | :---- |
| 1 | 192.168.1.40 |
| 2 | 192.168.1.41 |
| 3 | 192.168.1.42 |
| 4 | 192.168.1.43 |
| 5 | 192.168.1.44 |
| 6 | 192.168.1.45 |
| 7 | 192.168.1.46 |
| 8 | 192.168.1.47 |
| 9 | 192.168.1.48 |
| 10 | 192.168.1.49 |
| 11 | 192.168.1.50 |
| 12 | 192.168.1.51 |
| 13 | 192.168.1.52 |
| 14 | 192.168.1.53 |

Mounting will require installing one large bolt on the middle of the camera, and three attached to the lens lock.
![][image4]

Once it is mounted. There will be 2 flaps on the right side of the camera that need opened. You will plug in the USB cable on the corresponding box, and the Ethernet cable mounted to the same location. The ethernet cable will also be labeled with the ID.

![][image5]

[image1]: assets/camera_upgrade_process/image2.jpg

[image2]: assets/camera_upgrade_process/image1.jpg

[image3]: assets/camera_upgrade_process/image3.jpg

[image4]: assets/camera_upgrade_process/image2.jpg

[image5]: assets/camera_upgrade_process/image4.jpg
