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

from gi.repository import Adw
from gi.repository import Gtk
from gi.repository import GLib

import cros_ec_python.commands as ec_commands
import cros_ec_python.exceptions as ec_exceptions

@Gtk.Template(resource_path='/au/stevetech/yafi/ui/battery.ui')
class BatteryPage(Gtk.Box):
    __gtype_name__ = 'BatteryPage'

    chg_limit_enable = Gtk.Template.Child()
    chg_limit = Gtk.Template.Child()
    chg_limit_scale = Gtk.Template.Child()
    bat_limit = Gtk.Template.Child()
    bat_limit_scale = Gtk.Template.Child()
    chg_limit_override = Gtk.Template.Child()
    chg_limit_override_btn = Gtk.Template.Child()

    bat_ext_group = Gtk.Template.Child()
    bat_ext_enable = Gtk.Template.Child()
    bat_ext_stage = Gtk.Template.Child()
    bat_ext_trigger_time = Gtk.Template.Child()
    bat_ext_reset_time = Gtk.Template.Child()
    bat_ext_trigger = Gtk.Template.Child()
    bat_ext_reset = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def setup(self, app):
        # Charge limiter
        try:
            ec_limit = ec_commands.framework_laptop.get_charge_limit(app.cros_ec)
            ec_limit_enabled = ec_limit != (0, 0)
            self.chg_limit_enable.set_active(ec_limit_enabled)
            if ec_limit_enabled:
                self.chg_limit_scale.set_value(ec_limit[0])
                self.bat_limit_scale.set_value(ec_limit[1])
                self.chg_limit.set_sensitive(True)
                self.bat_limit.set_sensitive(True)
                self.chg_limit_override.set_sensitive(True)

            def handle_chg_limit_change(min, max):
                ec_commands.framework_laptop.set_charge_limit(
                    app.cros_ec, int(min), int(max)
                )

            def handle_chg_limit_enable(switch):
                active = switch.get_active()
                if active:
                    handle_chg_limit_change(
                        self.chg_limit_scale.get_value(), self.bat_limit_scale.get_value()
                    )
                else:
                    ec_commands.framework_laptop.disable_charge_limit(app.cros_ec)

                self.chg_limit.set_sensitive(active)
                self.bat_limit.set_sensitive(active)
                self.chg_limit_override.set_sensitive(active)

            self.chg_limit_enable.connect(
                "notify::active", lambda switch, _: handle_chg_limit_enable(switch)
            )
            self.chg_limit_scale.connect(
                "value-changed",
                lambda scale: handle_chg_limit_change(
                    scale.get_value(), self.bat_limit_scale.get_value()
                ),
            )
            self.bat_limit_scale.connect(
                "value-changed",
                lambda scale: handle_chg_limit_change(
                    self.chg_limit_scale.get_value(), scale.get_value()
                ),
            )

            self.chg_limit_override_btn.connect(
                "clicked",
                lambda _: ec_commands.framework_laptop.override_charge_limit(
                    app.cros_ec
                ),
            )
        except ec_exceptions.ECError as e:
            if e.ec_status == ec_exceptions.EcStatus.EC_RES_INVALID_COMMAND:
                app.no_support.append(ec_commands.framework_laptop.EC_CMD_CHARGE_LIMIT)
                self.chg_limit_enable.set_sensitive(False)
            else:
                raise e

        # Battery Extender
        try:
            ec_extender = ec_commands.framework_laptop.get_battery_extender(
                app.cros_ec
            )
            self.bat_ext_enable.set_active(not ec_extender["disable"])
            self.bat_ext_stage.set_sensitive(not ec_extender["disable"])
            self.bat_ext_trigger_time.set_sensitive(not ec_extender["disable"])
            self.bat_ext_reset_time.set_sensitive(not ec_extender["disable"])
            self.bat_ext_trigger.set_sensitive(not ec_extender["disable"])
            self.bat_ext_reset.set_sensitive(not ec_extender["disable"])

            self.bat_ext_stage.set_subtitle(str(ec_extender["current_stage"]))
            self.bat_ext_trigger_time.set_subtitle(
                format_timedelta(ec_extender["trigger_timedelta"])
            )
            self.bat_ext_reset_time.set_subtitle(
                format_timedelta(ec_extender["reset_timedelta"])
            )
            self.bat_ext_trigger.set_value(ec_extender["trigger_days"])
            self.bat_ext_reset.set_value(ec_extender["reset_minutes"])

            def handle_extender_enable(switch):
                active = switch.get_active()
                ec_commands.framework_laptop.set_battery_extender(
                    app.cros_ec,
                    not active,
                    int(self.bat_ext_trigger.get_value()),
                    int(self.bat_ext_reset.get_value()),
                )
                self.bat_ext_stage.set_sensitive(active)
                self.bat_ext_trigger_time.set_sensitive(active)
                self.bat_ext_reset_time.set_sensitive(active)
                self.bat_ext_trigger.set_sensitive(active)
                self.bat_ext_reset.set_sensitive(active)

            self.bat_ext_enable.connect(
                "notify::active", lambda switch, _: handle_extender_enable(switch)
            )
            self.bat_ext_trigger.connect(
                "notify::value",
                lambda scale, _: ec_commands.framework_laptop.set_battery_extender(
                    app.cros_ec,
                    not self.bat_ext_enable.get_active(),
                    int(scale.get_value()),
                    int(self.bat_ext_reset.get_value()),
                ),
            )
            self.bat_ext_reset.connect(
                "notify::value",
                lambda scale, _: ec_commands.framework_laptop.set_battery_extender(
                    app.cros_ec,
                    not self.bat_ext_enable.get_active(),
                    int(self.bat_ext_trigger.get_value()),
                    int(scale.get_value()),
                ),
            )
        except ec_exceptions.ECError as e:
            if e.ec_status == ec_exceptions.EcStatus.EC_RES_INVALID_COMMAND:
                app.no_support.append(
                    ec_commands.framework_laptop.EC_CMD_BATTERY_EXTENDER
                )
                self.bat_ext_group.set_visible(False)
            else:
                raise e

        # Schedule _update_battery to run every second
        GLib.timeout_add_seconds(
            1,
            self._update_battery,
            app
        )

    def _update_battery(self, app):
        if ec_commands.framework_laptop.EC_CMD_BATTERY_EXTENDER in app.no_support:
            return False

        try:
            ec_extender = ec_commands.framework_laptop.get_battery_extender(
                app.cros_ec
            )

            self.bat_ext_stage.set_subtitle(str(ec_extender["current_stage"]))
            self.bat_ext_trigger_time.set_subtitle(
                format_timedelta(ec_extender["trigger_timedelta"])
            )
            self.bat_ext_reset_time.set_subtitle(
                format_timedelta(ec_extender["reset_timedelta"])
            )
        except ec_exceptions.ECError as e:
            if e.ec_status == ec_exceptions.EcStatus.EC_RES_INVALID_COMMAND:
                app.no_support.append(
                    ec_commands.framework_laptop.EC_CMD_BATTERY_EXTENDER
                )
                return False
            else:
                raise e

        return app.current_page == 2

def format_timedelta(timedelta):
    days = f"{timedelta.days} days, " if timedelta.days else ""
    hours, remainder = divmod(timedelta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return days + f"{hours}:{minutes:02}:{seconds:02}"
