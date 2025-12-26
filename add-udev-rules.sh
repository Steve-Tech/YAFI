#!/bin/bash
set -e
echo Installing udev rules for YAFI to /etc/udev/rules.d/60-yafi.rules
echo KERNEL==\"cros_ec\", TAG+=\"uaccess\" > /etc/udev/rules.d/60-yafi.rules
udevadm control --reload-rules
udevadm trigger
echo udev rules installed successfully.
