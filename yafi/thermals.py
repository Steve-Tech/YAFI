# thermals.py
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

@Gtk.Template(resource_path='/au/stevetech/yafi/ui/thermals.ui')
class ThermalsPage(Gtk.Box):
    __gtype_name__ = 'ThermalsPage'

    fan_rpm = Gtk.Template.Child()
    fan_mode = Gtk.Template.Child()
    fan_set_rpm = Gtk.Template.Child()
    fan_set_percent = Gtk.Template.Child()
    fan_percent_scale = Gtk.Template.Child()

    temperatures = Gtk.Template.Child()
    temp_items = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def setup(self, app):
        # Don't let the user change the fans if they can't get back to auto
        if ec_commands.general.get_cmd_versions(
            app.cros_ec, ec_commands.thermal.EC_CMD_THERMAL_AUTO_FAN_CTRL
        ):

            def handle_fan_mode(mode):
                match mode:
                    case 0:  # Auto
                        self.fan_set_rpm.set_visible(False)
                        self.fan_set_percent.set_visible(False)
                        ec_commands.thermal.thermal_auto_fan_ctrl(app.cros_ec)
                    case 1:  # Percent
                        self.fan_set_rpm.set_visible(False)
                        self.fan_set_percent.set_visible(True)
                    case 2:  # RPM
                        self.fan_set_rpm.set_visible(True)
                        self.fan_set_percent.set_visible(False)

            self.fan_mode.connect(
                "notify::selected",
                lambda combo, _: handle_fan_mode(combo.get_selected()),
            )

            if ec_commands.general.get_cmd_versions(
                app.cros_ec, ec_commands.pwm.EC_CMD_PWM_SET_FAN_DUTY
            ):

                def handle_fan_percent(scale):
                    percent = int(scale.get_value())
                    ec_commands.pwm.pwm_set_fan_duty(app.cros_ec, percent)
                    self.fan_set_percent.set_subtitle(f"{percent} %")

                self.fan_percent_scale.connect("value-changed", handle_fan_percent)
            else:
                self.fan_set_percent.set_sensitive(False)

            if ec_commands.general.get_cmd_versions(
                app.cros_ec, ec_commands.pwm.EC_CMD_PWM_SET_FAN_TARGET_RPM
            ):

                def handle_fan_rpm(entry):
                    rpm = int(entry.get_text())
                    ec_commands.pwm.pwm_set_fan_rpm(app.cros_ec, rpm)

                self.fan_set_rpm.connect(
                    "notify::text", lambda entry, _: handle_fan_rpm(entry)
                )
            else:
                self.fan_set_rpm.set_sensitive(False)
        else:
            self.fan_mode.set_sensitive(False)

        # Temperature sensors
        while temp_child := self.temperatures.get_last_child():
            self.temperatures.remove(temp_child)
        self.temp_items.clear()

        try:
            ec_temp_sensors = ec_commands.thermal.get_temp_sensors(app.cros_ec)
        except ec_exceptions.ECError as e:
            if e.ec_status == ec_exceptions.EcStatus.EC_RES_INVALID_COMMAND:
                # Generate some labels if the command is not supported
                ec_temp_sensors = {}
                temps = ec_commands.memmap.get_temps(app.cros_ec)
                for i, temp in enumerate(temps):
                    ec_temp_sensors[f"Sensor {i}"] = (temp, None)
            else:
                raise e

        for key, value in ec_temp_sensors.items():
            new_row = Adw.ActionRow(title=key, subtitle=f"{value[0]}°C")
            new_row.add_css_class("property")
            self.temperatures.append(new_row)
            self.temp_items.append(new_row)

        self._update_thermals(app)

        # Schedule _update_thermals to run every second
        GLib.timeout_add_seconds(1, self._update_thermals, app)

    def _update_thermals(self, app):
        # memmap reads should always be supported
        ec_fans = ec_commands.memmap.get_fans(app.cros_ec)
        self.fan_rpm.set_subtitle(f"{ec_fans[0]} RPM")

        ec_temp_sensors = ec_commands.memmap.get_temps(app.cros_ec)
        # The temp sensors disappear sometimes, so we need to handle that
        for i in range(min(len(self.temp_items), len(ec_temp_sensors))):
            self.temp_items[i].set_subtitle(f"{ec_temp_sensors[i]}°C")

        # Check if this has already failed and skip if it has
        if not ec_commands.pwm.EC_CMD_PWM_GET_FAN_TARGET_RPM in app.no_support:
            try:
                ec_target_rpm = ec_commands.pwm.pwm_get_fan_rpm(app.cros_ec)
                self.fan_set_rpm.set_subtitle(f"{ec_target_rpm} RPM")
            except ec_exceptions.ECError as e:
                # If the command is not supported, we can ignore it
                if e.ec_status == ec_exceptions.EcStatus.EC_RES_INVALID_COMMAND:
                    app.no_support.append(ec_commands.pwm.EC_CMD_PWM_GET_FAN_TARGET_RPM)
                    self.fan_set_rpm.set_subtitle("")
                else:
                    # If it's another error, we should raise it
                    raise e

        return app.current_page == 0
