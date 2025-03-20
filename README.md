# Yet Another Framework Interface

YAFI is another GUI for the Framework Laptop Embedded Controller.
It is written in Python with a GTK4 Adwaita theme, and uses the `CrOS_EC_Python` library to communicate with the EC.

## Features

### Fan Control and Temperature Monitoring

![Thermals Page](docs/1-thermals.png)

### LED Control

![LEDs Page](docs/2-leds.png)

### Battery Limiting

![Battery Page](docs/3-battery.png)

#### Battery Extender

![Battery Extender](docs/3a-battery-ext.png)

### Hardware Info

![Hardware Page](docs/4-hardware.png)

## Installation

### udev Rules (MUST READ)

To allow YAFI to communicate with the EC, you need to copy the `60-cros_ec_python.rules` file to `/etc/udev/rules.d/` and reload the rules with `sudo udevadm control --reload-rules && sudo udevadm trigger`.

### Flatpak

Build and install the Flatpak package with `flatpak-builder --install --user build au.stevetech.yafi.json`.

You can also create a flatpak bundle with `flatpak-builder --repo=repo build au.stevetech.yafi.json` and install it with `flatpak install --user repo au.stevetech.yafi.flatpak`.
