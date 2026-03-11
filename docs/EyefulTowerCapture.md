# Introduction

The Eyeful Tower is used to capture HDR images of environments for realistic recreation.

It consists of a robotic base called a PAL TIAGo and a tower of 14 cameras arranged in an array.

Information on the Robot and more nitty gritty details can be found on PAL’s website: [https://docs.pal-robotics.com/sdk-dev/hardware/tiago/mobile-base\#tiago-mobile-base](https://docs.pal-robotics.com/sdk-dev/hardware/tiago/mobile-base#tiago-mobile-base)

![][image21]

The robot is partially autonomous. It is also teleoperated using the provided Commandly app. This app is used to get statuses back from the robot, manage cameras, and start captures. It will be installed on the companion Linux laptop.

![][image10]

# Commandly

Commandly is the program we will be using to control the robot. It provides UI for sensor and capture feedback.

Before starting the app, you will want to be on the hotspot connected to the robot. The companion laptop should connect to it automatically.

## Tabs

### Sensors

![][image10]

## Commandly Sensors Tab

The sensors tab has all of the information coming from the robot. The icons on the left are different statuses the robot is in. The middle has a context camera feed for driving the robot. The right is a local costmap of obstacles the robot sees.

A note on the camera: the bottom of the frame is about 2 feet in front of the robot, so if an object passes below it, it is less than 2 feet away, and a capture will not fully happen.

| UI Element | Description |
| :---- | :---- |
| Drive | Whether the robot is able to be controlled with the joystick. |
| Autonomous | Whether the robot can do autonomous functions, like capturing. |
| Camera Ready | Cameras are initialized and ready for captures. |
| Capture Ready | The current state of the capture |
| Camera Images | The number of images on each camera. |
| Capture | Moves the robot about 2 feet forward before doing a capture. Greyed out when in Drive mode. |
| Capture in Place | Does a capture without moving the robot. Greyed out when in Drive mode. |
| Start Mapping/Stop Mapping | Clears the Map and starts a mapping session. Becomes “Stop Mapping” while mapping. |
| Emergency Stop | Stops the robot if something happens. You will need to restart the robot after this |

#### Mapping

Mapping is done before a capture to allow for the robot to do partial autonomy and for easier teleoperation.

The “Start Mapping” button will clear the map and put the robot in mapping mode.

![][image4]

You can stop mapping by hitting the same button. Once mapped, the robot will show up in the map as an Orange circle with an arrow on the front pointing forward.
If the map is too large, there will be scroll bars that appear, allowing for mapping of large areas.

### Config

![][image18]

## Commandly Config Tab

The Config tab will have settings that will be applied to the robot during captures, and some extra management functionalities.

On the left column:

| Drop Down | Description |
| ----- | ----- |
| Capture Type | This will be how the cameras do a capture. Double captures capture 2 sets of images, each set called a “bracket”. Single will capture a single bracket of images.  In single mode, only the config values labelled “First” are used. |
| First/Second Shutter | The length the shutter is opened in seconds for each bracket set. |
| First/Second ISO | The ISO value for each bracket set. |
| First/Second Drive Mode | The “Drive Mode” for each set of brackets.     This controls how many images are taken in a bracket, and the brightness in each image using an offset. |

The buttons in the right column:

| Button Name | Description |
| ----- | ----- |
| Format Camera | Formats all of the cameras. Should be done before and after each run. |
| Restart Robot | Restarts the server on the robot. |
| Stop Robot | Stops the server on the robot. Should be done before transferring images. |

Hovering over each UI component with the mouse will give a short description of what it does.

## Controls

A controller can be used to control both the robot and the UI.

## ![][image17]

This Logitech controller was the one provided with the robot and will come with the companion laptop. Xbox Series X/S controllers are also supported on the companion laptop.

### Controls

There are 2 states the controller can be in, Drive Mode and UI Mode.

#### UI Mode

UI Mode will let you control the UI itself. The robot will not move while you are doing this.

| UI Mode Controls |  |
| :---- | :---- |
| D-Pad | UI Navigation |
| Left Joystick | UI Navigation |
| Right Joystick | N/A |
| A | Accept |
| B | Cancel |
| X | N/A |
| Y | N/A |
| RB | Goes Right tab |
| LB | Goes to Left tab |
| RT | N/A |
| LT | N/A |
| Start | Toggles between Drive Mode and UI Mode |

#### Drive Mode

In Drive Mode, you will be able to operate the robot. Drive mode will also disable all buttons.

| Drive Mode Controls |  |
| :---- | :---- |
| D-Pad | Up/Down \- Forward/Back Left/Right \- Rotation |
| Left Joystick | Moves Robot forward and back |
| Right Joystick | Rotates Robot |
| A | N/A |
| B | N/A |
| X | N/A |
| Y | N/A |
| RB | Safety, press this to move the robot |
| LB | Safety, press this to move the robot |
| RT | N/A |
| LT | N/A |
| Start | Toggles between Drive Mode and UI Mode |

# Starting the Robot

The process is simple, but should be done in the correct order.

# Controller Connection

The controller is wirelessly connected using a dongle. It will either be in the laptop or connected to the robot in the USB port on the tower.

During preparation and transportation, you should put the dongle in the port on the robot tower.

These are the controls

| PAL Controller Controls |  |
| :---- | :---- |
| D-Pad | N/A |
| Left Joystick | Moves Robot forward and back |
| Right Joystick | Rotates Robot |
| A | N/A |
| B | N/A |
| X | N/A |
| Y | N/A |
| RB | Safety, press this to move the robot |
| LB | N/A |
| RT | N/A |
| LT | N/A |
| Start | Toggles between Drive Mode and Autonomous Mode |

# Starting Cameras

The cameras should be started first. This will allow for the network systems in each to start up. The cameras, if they are referred to individually will be referred to with their identifier which is the number on the side of the robot.

On the front left of the camera will be the power switch. You will want to turn all 14 cameras on to start.
![][image20]

Once all cameras appear on, validate that each screen is illuminated. Camera 13’s screen may not come on, but that is normal. It is too close to camera 14 for it to activate, but the camera will be on. If it doesn’t seem to connect, there will be future troubleshooting steps.

Once they are all on, validate they are charged enough to do a capture (above 70% should be good for a fairly long capture).

# Starting Robot

The robot will likely be plugged in. The plug is latched, so make sure to depress the button on top before pulling the plug out. Make sure it is charged enough to do a capture.

Once unplugged, there will be a screen with buttons around it. Press the silver button for about a second and it will power on.

![][image5]

Once on, give it about 90 seconds to boot up. You can still drive it around while it boots up and connects to the cameras.

# Pre-Capture Preparation

At this point, I will assume you have the robot on, and are in the location that you intend to capture.

## Mapping

Before starting the capture we will want to map the room. There will be a map in the UI, it is likely wrong. You can be in the room during this process, just do not stand in front of the robot.

Hitting the “Start Mapping” button in the “Sensors” section of Commandly will clear the map. Start driving the robot around the room and the map will begin filling in. I suggest doing a lap or two in the area you intend to capture. Validate the map looks accurate and there are no noisy areas that the robot didn’t get correctly.

Then hit “Stop Mapping” and an orange icon with an arrow will show up on the map. That is the robot.
![][image9]

## Camera and Lens Preparation

At this point, the cameras should be on, and connected to the robot. We will want to format the SD cards on the cameras. In Commandly go to “Config” and hit the “Format SD Cards” button.
![][image19]

![][image6]


Unless instructed, do not change any other settings in the config section.

There will be lens caps on the cameras, we will want to make sure those are removed from all cameras, and placed somewhere that won’t be seen during the capture. When taking the lens cap off, they come off by pulling, not twisting. There is a ring holding the outer part of the lens that could come off if trying to twist the lens cap off like a bottle cap.

Hold the body of the camera, and pull the cap away from the camera with small side to side twisting motions to remove the cap.

![][image8]

## Lens cap to remove

We will also want to clean the lenses off before starting. These can cause artifacts later on through the data pipeline. You can use lens wipes and a dust blower for removing things from the lenses.

![][image1]![][image12]

## Room Prep

### Scale Bars, Color Matrix, and On Air Sign

We need to place a couple things in the room for the capture to be able to be calibrated.

There are 3 scale bars that should be placed in the X, Y, and Z axes of the room. You should place them along different walls, and arranged in a way that one is visible within each capture. This will make it easier for the pipeline to find the scale bars and apply the scale properly.

![][image11]![][image13]


We will also need to place the color calibration matrix somewhere that is visible during the capture. On a table can work.
![][image16]

On the Eyeful Tower, there will be an “On Air” sign. You will want to hang that on the doorknob of the room you are capturing.
![][image14]

### Clear Obstructions

You will also want to make sure the floor is clear of obstructions or loose tiles. The robot has caster wheels on the bottom that can easily get caught on floors with differing elevation.

Another thing to check is that computers in the room are locked and do not contain any sensitive information on the screens.

## Start Capture

Once the room is mapped, the lens caps are off, the lenses are clean, and the calibration objects are in the room you can start capturing\!

# Capture Checklist

Here is a simple reference of what needs done to start a capture:

1. Map the room
2. Format the cameras
3. Put down scale bars
4. Put down color calibration matrix
5. Put “On Air” sign on the door
6. Remove lens caps and clean lenses

# Post-Capture Process

## Robot Process

Before preparing the robot for transport, check each camera and validate the images on the camera with the value in Commandly. They should match, and the number should be evenly divisible by 14\.

Clean the lenses, and put the lens caps back on. Make sure to collect the scale bars and color matrix.

Transport the robot back to the docking system, making sure to follow the transportation guidelines in the Robot Details section.

Plug the robot in near the docking system, and plug the network cable in to one of the open ports on the switch.
![][image2]![][image25]

Once it is plugged in the capture process is done\!

## Troubleshooting

### Replacing Lens Caps

Be careful putting the lens caps back on. It is easy to bump the shutter button and take extra photos. If this happens you can manually delete the photos taken.

The other cameras and the “Camera Images” part of Commandly should have the proper number of images the camera should have. Erase the most recent images first until it matches.

# Robot Details

## Cameras and Lenses

The Cameras are Sony a1 cameras with Entaniya Fisheye HAL 200 lenses with a 200 degree FOV.

## ![][image7] Image taken from the bottom camera on the robot.

The Sony cameras shoot 50mp images at 8640x6750. All of the camera are running the same firmware with the same settings.

The cameras each have a static IP address assigned to them at certain positions. This table is from the guide above:

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

The ID is the number on the side of the robot designating the cameras position. Camera 1 is at the bottom of the robot. It is perpendicular to the ground. Cameras 2 to 13 are angled slightly towards the ceiling on the same plane. Camera 14 is pointed directly at the ceiling, parallel to the ground.

![][image15]

### Camera Care Tips

When transporting the robot, the lens caps MUST be on the cameras. Lens caps should only be removed once in the capture space

 While capturing, be sure to be aware of the location of the robot as to not hit the lenses into anything or damage the surroundings. Camera 1 protrudes out slightly from the footprint of the robot. This should not be an issue during captures, since you should not be getting that close to walls anyways. In general operation if a tight turn is needed, keep that in mind.

The cameras should be off during storage. Batteries should be kept above 20%, so be wary during captures if they are going on for long.

If a battery dies, there is a chance that you need to physically remove them even if they are charged. This could be a quirk with some cameras, or potentially the firmware. Some cameras have been observed dying, then needing batteries popped out before registering the batteries as not being dead.

If all of the cameras need to be removed from the tower, start from the bottom and go up (1 \-\> 14). This gets the cameras out of the way. When putting the back on, go the opposite direction (14 \-\> 1).

If it is required to view the screen of camera 13 for validating it’s on or changing settings, use a camera on a phone and put it into the view finder.
![][image22]


The cameras have 2 512gb SD cards, so keep that in mind during the capture process. Each image captured will make a JPEG that is about 5mb and a RAW/ARW that is about 50mb.

The cameras are powered by the robot over USB C. They will still slowly degrade power, however, and at different rates. So keeping an eye on the battery of the cameras during a capture is a good idea.

When cleaning the lenses pay attention to any plastic bits of the lens caps that might have fallen off of the caps. Be sure those are cleaned off during the cleaning process.

### Intel Real Sense

There is an Intel Real Sense cameras mounted on the robot. They are purely context cameras for use during operation. It is mounted above camera 1\.
![][image24]

## PAL Robot

The base is a PAL Tiago. It is a partially autonomous robot with a differential drive.

A detailed rundown of the exact hardware and ports can be found here: [https://docs.pal-robotics.com/25.01/hardware/tiago/mobile-base.html\#tiago-mobile-base](https://docs.pal-robotics.com/25.01/hardware/tiago/mobile-base.html#tiago-mobile-base)

The robot also has a controller. This is the primary controller we use with it. It uses a wireless dongle. It will either go in to the companion laptop for robot operation during captures, or in to a port on the side of the tower to control it directly during debugging or transportation.

![][image3]

When the controller is used with the companion laptop controls are in the Commandly section of this doc.

When it is plugged directly in to the base they are here: [https://docs.pal-robotics.com/25.01/management/gamepad.html\#controls](https://docs.pal-robotics.com/25.01/management/gamepad.html#controls)

The robot will have 2 networks associated to it. It has a wireless hotspot and a wired network with a network switch on top of the base:

| Network Type | IP |
| ----- | ----- |
| Wireless Hotspot | 10.42.0.1 |
| Wired Network | 192.168.1.100 |

### Robot Care Tips

#### Transportation

When transporting, always stand directly next to the robot or in front. You should be within arms reach of the robot at all times during transportation in public areas of the building. When coming out from or around a corner, be ahead of the robot so you are not blindly taking corners.

Be wary of bumps and sharp falls offs when driving. The caster wheels are a hard rubber, but still rubber and can be damaged by sharp corners. When going over bumps:

1. Align the robot to drive directly over the bump, not at an angle, a few feet out from the bump.
2. Hold on to the handles on the tower while going over the bump.
3. Accelerate to full speed to get over and only stop when the robot is fully over
4. Allow the robot to settle and stop moving before continuing.

When driving the robot in to an elevator, put it in the back corner. The LIDAR on the robot can trigger the LIDAR sensors in the elevator doors.
![][image23]

## The robot is pointing in a corner of the elevator

#### General Tips

Keep the battery above 50%, and don’t start captures when below 70%. We do not want the robot dying during a capture. No images would be lost, but we lose some metadata related to the capture map and current capture count. Keep in mind that the cameras are also powered by the same battery powering the robot, so it can drain faster than expected while not moving.

Do not get too close to corners and walls when capturing. Getting too close will get less then stellar data. It will also mess with the robots localization. It uses features in the map to determine where it is, if you are in a featureless corner, it is hard for it to figure out where it is, and triggering a capture can be dangerous and cause it to drive in to the wall.

During captures, do not get close enough to the door to prevent it from opening. If for whatever reason you need to emergency stop the robot, and it is in the way of the door, you will not be able to open that door if it swings to the inside. If you need to get a feel for where the door opens when on the map, be inside the room when getting close to the door.

Plug the robot in when docked. We do not want the robot dying while transferring images and we want it ready for the next capture. The robot also charges the cameras, so make sure it is plugged in when the cameras are on and docked.

Avoid deep/shaggy carpet. The caster wheels would not be able to handle that.

The emergency stop button does work, and you should not be afraid to press it. You will want to power cycle the robot when it is done. Make sure to fully twist it so it comes out before turning back on.

Keep in mind for now, the robot only makes a 2D map, so under tables are considered valid, but with the rig it will not fit.

# Troubleshooting

## Camera Ready Red

Validate all of the cameras are on, then restart the server from the config screen using the “RestartRobot” button.

## Camera and controls lagging

Enter the room and let the camera catch up. This seems to be a latency issue with the real sense cameras that slows down the rest of the app.

## App has Not Connecting screen

Make sure that the companion laptop is connected to the robots hotspot.

## Robot has jerky motion

This is likely from the caster wheels being in an off angle. Move the robot forward slowly to align the wheels.

## Camera not Charging or Yellow USB Light is blinking

The fast blinking USB light means that the camera is not charging or charging slowly because of a bad connection.
If the LED is not lit, the camera is likely done charging.

Some steps you can try to fix this, in order of ease:

1. Power cycle camera
2. Power cycle robot
3. Replug in the USB-C cable in the tower and camera
4. Swap USB-C cable for a new one.
5. Reseat battery
6. Swap battery

This is likely caused by a bad battery so swapping it out if nothing else works will almost certainly fix the problem (It has fixed it on at least 4 cameras before on the tower). One last thing you can do to validate it is a battery issue, is try charging the camera using an external USB-C charger, like a laptop one. If it still blinks, then it is almost certainly the battery.

Here’s a Sony link on some of the other blink codes: [https://www.sony.com/electronics/support/articles/00013415](https://www.sony.com/electronics/support/articles/00013415)

## SD Format Fail

If you get a prompt that the SD Card format failed, restart the cameras, and then restart the robot app and try again.

# Troubleshooting

## Camera Ready Red

Validate all of the cameras are on, then restart the server from the config screen using the “RestartRobot” button.

## Camera and controls lagging

Enter the room and let the camera catch up. This seems to be a latency issue with the real sense cameras that slows down the rest of the app.

## App has Not Connecting screen

Make sure that the companion laptop is connected to the robots hotspot.

## Robot has jerky motion

This is likely from the caster wheels being in an off angle. Move the robot forward slowly to align the wheels.

## Camera not Charging or Yellow USB Light is blinking

The fast blinking USB light means that the camera is not charging or charging slowly because of a bad connection.
If the LED is not lit, the camera is likely done charging.

Some steps you can try to fix this, in order of ease:

1. Power cycle camera
2. Power cycle robot
3. Replug in the USB-C cable in the tower and camera
4. Swap USB-C cable for a new one.
5. Reseat battery
6. Swap battery

This is likely caused by a bad battery so swapping it out if nothing else works will almost certainly fix the problem (It has fixed it on at least 4 cameras before on the tower). One last thing you can do to validate it is a battery issue, is try charging the camera using an external USB-C charger, like a laptop one. If it still blinks, then it is almost certainly the battery.

Here’s a Sony link on some of the other blink codes: [https://www.sony.com/electronics/support/articles/00013415](https://www.sony.com/electronics/support/articles/00013415)

## SD Format Fail

If you get a prompt that the SD Card format failed, restart the cameras, and then restart the robot app and try again.

[image1]: assets/eyeful_tower_capture/image1.jpg

[image2]: assets/eyeful_tower_capture/image2.jpg

[image3]: assets/eyeful_tower_capture/image3.jpg

[image4]: assets/eyeful_tower_capture/image9.png

[image5]: assets/eyeful_tower_capture/image4.png

[image6]: assets/eyeful_tower_capture/image5.png

[image7]: assets/eyeful_tower_capture/image6.jpg

[image8]: assets/eyeful_tower_capture/image7.jpg

[image9]: assets/eyeful_tower_capture/image9.png

[image10]: assets/eyeful_tower_capture/image8.png

[image11]: assets/eyeful_tower_capture/image10.jpg

[image12]: assets/eyeful_tower_capture/image11.jpg

[image13]: assets/eyeful_tower_capture/image12.jpg

[image14]: assets/eyeful_tower_capture/image13.jpg

[image15]: assets/eyeful_tower_capture/image14.jpg

[image16]: assets/eyeful_tower_capture/image15.jpg

[image17]: assets/eyeful_tower_capture/image16.jpg

[image18]: assets/eyeful_tower_capture/image17.png

[image19]: assets/eyeful_tower_capture/image18.png

[image20]: assets/eyeful_tower_capture/image19.jpg

[image21]: assets/eyeful_tower_capture/image20.jpg

[image22]: assets/eyeful_tower_capture/image21.jpg

[image23]: assets/eyeful_tower_capture/image22.jpg

[image24]: assets/eyeful_tower_capture/image23.jpg

[image25]: assets/eyeful_tower_capture/image24.jpg

[image26]: assets/eyeful_tower_capture/image25.png
