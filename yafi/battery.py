# battery.py
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


@Gtk.Template(resource_path="/au/stevetech/yafi/ui/battery.ui")
class BatteryPage(Gtk.Box):
    __gtype_name__ = "BatteryPage"

    batt_status = Gtk.Template.Child()

    batt_charge = Gtk.Template.Child()
    batt_health = Gtk.Template.Child()
    batt_cycles_label = Gtk.Template.Child()
    batt_volts_label = Gtk.Template.Child()
    batt_watts_label = Gtk.Template.Child()
    batt_cap_rem_label = Gtk.Template.Child()
    batt_cap_full_label = Gtk.Template.Child()

    batt_manu = Gtk.Template.Child()
    batt_model = Gtk.Template.Child()
    batt_serial = Gtk.Template.Child()
    batt_type = Gtk.Template.Child()
    batt_orig_cap = Gtk.Template.Child()
    batt_orig_volts = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def setup(self, app):
        battery = ec_commands.memmap.get_battery_values(app.cros_ec)
        self.batt_manu.set_subtitle(battery["manufacturer"])
        self.batt_model.set_subtitle(battery["model"])
        self.batt_serial.set_subtitle(battery["serial"])
        self.batt_type.set_subtitle(battery["type"])
        self.batt_orig_cap.set_subtitle(f"{self._get_watts(battery, 'design_capacity'):.2f}Wh")
        self.batt_orig_volts.set_subtitle(f"{battery['design_voltage']/1000}V")
        self._update_battery(app, battery)
        # Schedule _update_battery to run every second
        GLib.timeout_add_seconds(1, self._update_battery, app)

    def _get_watts(self, battery, key, volt_key="design_voltage"):
        return (battery[key] * battery[volt_key]) / 1000_000

    def _update_battery(self, app, battery=None):
        if battery is None:
            battery = ec_commands.memmap.get_battery_values(app.cros_ec)

        status_messages = []
        if battery["invalid_data"]:
            status_messages.append("Invalid Data")
        if not battery["batt_present"]:
            status_messages.append("No Battery")
        if battery["ac_present"]:
            status_messages.append("Plugged in")
        if battery["level_critical"]:
            status_messages.append("Critical")
        if battery["discharging"]:
            status_messages.append("Discharging")
        if battery["charging"]:
            status_messages.append("Charging")
        self.batt_status.set_subtitle(", ".join(status_messages))

        self.batt_charge.set_fraction(
            battery["capacity"] / battery["last_full_charge_capacity"]
        )
        self.batt_health.set_fraction(
            battery["last_full_charge_capacity"] / battery["design_capacity"]
        )
        self.batt_cycles_label.set_label(str(battery["cycle_count"]))
        self.batt_volts_label.set_label(f"{battery['volt']/1000:.2f}V")
        self.batt_watts_label.set_label(
            f"{self._get_watts(battery, 'rate', 'volt') * (-1 if battery['charging'] else 1):.2f}W"
        )
        self.batt_cap_rem_label.set_label(
            f"{self._get_watts(battery, 'capacity'):.2f}Wh"
        )
        self.batt_cap_full_label.set_label(
            f"{self._get_watts(battery, 'last_full_charge_capacity'):.2f}Wh"
        )

        return app.current_page == 2
