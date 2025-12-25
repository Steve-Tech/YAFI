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

from gi.repository import Gtk, Adw, GLib

import cros_ec_python.commands as ec_commands
import cros_ec_python.exceptions as ec_exceptions

@Gtk.Template(resource_path='/au/stevetech/yafi/ui/thermals.ui')
class ThermalsPage(Gtk.Box):
    __gtype_name__ = 'ThermalsPage'

    first_run = True

    fan_rpm = Gtk.Template.Child()
    fan_mode = Gtk.Template.Child()
    fan_set_rpm = Gtk.Template.Child()
    fan_set_percent = Gtk.Template.Child()
    fan_percent_scale = Gtk.Template.Child()
    fan_set_points = Gtk.Template.Child()
    set_points = []
    ec_set_points_supported = False
    ec_set_points = []

    temperatures = Gtk.Template.Child()
    temp_items = []

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def setup(self, app):
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
            off_row = Adw.ActionRow(title=key, subtitle=f"{value[0]}°C")
            off_row.add_css_class("property")
            self.temperatures.append(off_row)
            self.temp_items.append(off_row)

        self._update_thermals(app)

        # Don't let the user change the fans if they can't get back to auto
        if ec_commands.general.get_cmd_versions(
            app.cros_ec, ec_commands.thermal.EC_CMD_THERMAL_AUTO_FAN_CTRL
        ):
            self.ec_set_points_supported = ec_commands.general.check_cmd_version(
                app.cros_ec, ec_commands.thermal.EC_CMD_THERMAL_GET_THRESHOLD, 1
            ) and ec_commands.general.check_cmd_version(
                app.cros_ec, ec_commands.thermal.EC_CMD_THERMAL_SET_THRESHOLD, 1
            )

            def handle_fan_mode(mode):
                match mode:
                    case 0:  # Auto
                        self.fan_set_rpm.set_visible(False)
                        self.fan_set_percent.set_visible(False)
                        ec_commands.thermal.thermal_auto_fan_ctrl(app.cros_ec)
                        self.fan_set_points.set_visible(self.ec_set_points_supported)
                    case 1:  # Percent
                        self.fan_set_points.set_visible(False)
                        self.fan_set_rpm.set_visible(False)
                        self.fan_set_percent.set_visible(True)
                    case 2:  # RPM
                        self.fan_set_points.set_visible(False)
                        self.fan_set_rpm.set_visible(True)
                        self.fan_set_percent.set_visible(False)

            handle_fan_mode(self.fan_mode.get_selected())

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
                    rpm = int(entry.get_value())
                    ec_commands.pwm.pwm_set_fan_rpm(app.cros_ec, rpm)

                self.fan_set_rpm.connect(
                    "notify::value", lambda entry, _: handle_fan_rpm(entry)
                )
            else:
                self.fan_set_rpm.set_sensitive(False)
        else:
            self.fan_mode.set_sensitive(False)

        # Set points
        if self.ec_set_points_supported and self.first_run:
            def handle_set_point(entry, key):
                index = entry.ec_index
                temp = int(entry.get_value())
                # Don't allow an off temp higher than max temp and vice versa
                match key:
                    case "temp_fan_off":
                        if temp > self.ec_set_points[index]["temp_fan_max"]:
                            entry.set_value(self.ec_set_points[index]["temp_fan_off"])
                            return
                    case "temp_fan_max":
                        if temp < self.ec_set_points[index]["temp_fan_off"]:
                            entry.set_value(self.ec_set_points[index]["temp_fan_max"])
                            return
                self.ec_set_points[entry.ec_index][key] = temp
                ec_commands.thermal.thermal_set_thresholds(
                    app.cros_ec, index,
                    self.ec_set_points[index]
                )

            for i, sensor in enumerate(ec_temp_sensors):
                ec_set_point = ec_commands.thermal.thermal_get_thresholds(app.cros_ec, i)
                self.ec_set_points.append(ec_set_point)
                off_row = Adw.SpinRow(
                    title=f"Fan On - {sensor}",
                    subtitle=f"Turn fan on when above temp (°C)",
                )
                off_row.ec_index = i
                # 0K to 65535K for 16bit unsigned range
                # Actually the EC takes 32bits, but let's keep it like this for sanity
                off_row.set_adjustment(Gtk.Adjustment(
                    lower=-273,
                    upper=65_262,
                    page_increment=10,
                    step_increment=1,
                    value=ec_set_point["temp_fan_off"],
                ))
                off_row.connect(
                    "notify::value", lambda entry, _: handle_set_point(entry, "temp_fan_off")
                )
                max_row = Adw.SpinRow(
                    title=f"Fan Max - {sensor}",
                    subtitle=f"Max fan speed when above temp (°C)",
                )
                max_row.ec_index = i
                max_row.set_adjustment(Gtk.Adjustment(
                    lower=-273,
                    upper=65_262,
                    page_increment=10,
                    step_increment=1,
                    value=ec_set_point["temp_fan_max"],
                ))
                max_row.connect(
                    "notify::value", lambda entry, _: handle_set_point(entry, "temp_fan_max")
                )
                self.fan_set_points.add_row(off_row)
                self.fan_set_points.add_row(max_row)

        self.first_run = False

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
