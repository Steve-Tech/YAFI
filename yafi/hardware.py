# hardware.py
#
# Copyright 2025 Stephen Horvath
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# SPDX-License-Identifier: GPL-2.0-or-later

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import GLib

import cros_ec_python.commands as ec_commands
import cros_ec_python.exceptions as ec_exceptions

@Gtk.Template(resource_path='/au/stevetech/yafi/ui/hardware.ui')
class HardwarePage(Gtk.Box):
    __gtype_name__ = 'HardwarePage'

    hw_chassis = Gtk.Template.Child()
    hw_chassis_label = Gtk.Template.Child()

    hw_priv_cam = Gtk.Template.Child()
    hw_priv_cam_sw = Gtk.Template.Child()
    hw_priv_mic = Gtk.Template.Child()
    hw_priv_mic_sw = Gtk.Template.Child()

    hw_fp_pwr = Gtk.Template.Child()
    hw_fp_pwr_en = Gtk.Template.Child()
    hw_fp_pwr_dis = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def setup(self, app):
        # Fingerprint Power (Untested)
        if ec_commands.general.get_cmd_versions(
            app.cros_ec, ec_commands.framework_laptop.EC_CMD_FP_CONTROL
        ):
            self.hw_fp_pwr_en.connect(
                "clicked",
                lambda _: ec_commands.framework_laptop.fp_control(app.cros_ec, True),
            )

            self.hw_fp_pwr_dis.connect(
                "clicked",
                lambda _: ec_commands.framework_laptop.fp_control(app.cros_ec, False),
            )
            self.hw_fp_pwr.set_visible(True)
        else:
            self.hw_fp_pwr.set_visible(False)

        self._update_hardware(app)

        # Schedule _update_hardware to run every second
        GLib.timeout_add_seconds(1, self._update_hardware, app)

    def _update_hardware(self, app):
        success = False
        # Chassis
        if not ec_commands.framework_laptop.EC_CMD_CHASSIS_INTRUSION in app.no_support:
            try:
                ec_chassis = ec_commands.framework_laptop.get_chassis_intrusion(
                    app.cros_ec
                )

                self.hw_chassis_label.set_label(str(ec_chassis["total_open_count"]))

                ec_chassis_open = ec_commands.framework_laptop.get_chassis_open_check(
                    app.cros_ec
                )
                self.hw_chassis.set_subtitle(
                    "Currently " + ("Open" if ec_chassis_open else "Closed")
                )

                success = True
            except ec_exceptions.ECError as e:
                if e.ec_status == ec_exceptions.EcStatus.EC_RES_INVALID_COMMAND:
                    app.no_support.append(
                        ec_commands.framework_laptop.EC_CMD_CHASSIS_INTRUSION
                    )
                    self.hw_chassis.set_visible(False)
                else:
                    raise e

        # Privacy Switches
        if (
            not ec_commands.framework_laptop.EC_CMD_PRIVACY_SWITCHES_CHECK_MODE
            in app.no_support
        ):
            try:
                ec_privacy = ec_commands.framework_laptop.get_privacy_switches(
                    app.cros_ec
                )
                self.hw_priv_cam_sw.set_active(ec_privacy["camera"])
                self.hw_priv_mic_sw.set_active(ec_privacy["microphone"])

                success = True
            except ec_exceptions.ECError as e:
                if e.ec_status == ec_exceptions.EcStatus.EC_RES_INVALID_COMMAND:
                    app.no_support.append(
                        ec_commands.framework_laptop.EC_CMD_PRIVACY_SWITCHES_CHECK_MODE
                    )
                    self.hw_priv_cam.set_visible(False)
                    self.hw_priv_mic.set_visible(False)
                else:
                    raise e

        return app.current_page == 3 and success
