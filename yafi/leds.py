# leds.py
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

import cros_ec_python.commands as ec_commands
import cros_ec_python.exceptions as ec_exceptions

@Gtk.Template(resource_path='/au/stevetech/yafi/ui/leds.ui')
class LedsPage(Gtk.Box):
    __gtype_name__ = 'LedsPage'

    led_pwr = Gtk.Template.Child()
    led_pwr_scale = Gtk.Template.Child()

    led_kbd = Gtk.Template.Child()
    led_kbd_scale = Gtk.Template.Child()

    led_advanced = Gtk.Template.Child()

    led_pwr_colour = Gtk.Template.Child()

    led_chg_colour = Gtk.Template.Child()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def setup(self, app):
        # Power LED
        try:

            def handle_led_pwr(scale):
                value = int(abs(scale.get_value() - 2))
                ec_commands.framework_laptop.set_fp_led_level(app.cros_ec, value)
                self.led_pwr.set_subtitle(["High", "Medium", "Low"][value])

            current_fp_level = ec_commands.framework_laptop.get_fp_led_level(
                app.cros_ec
            ).value
            self.led_pwr_scale.set_value(abs(current_fp_level - 2))
            self.led_pwr.set_subtitle(["High", "Medium", "Low"][current_fp_level])
            self.led_pwr_scale.connect("value-changed", handle_led_pwr)
        except ec_exceptions.ECError as e:
            if e.ec_status == ec_exceptions.EcStatus.EC_RES_INVALID_COMMAND:
                app.no_support.append(ec_commands.framework_laptop.EC_CMD_FP_LED_LEVEL)
                self.led_pwr.set_visible(False)
            else:
                raise e

        # Keyboard backlight
        if ec_commands.general.get_cmd_versions(
            app.cros_ec, ec_commands.pwm.EC_CMD_PWM_SET_KEYBOARD_BACKLIGHT
        ):

            def handle_led_kbd(scale):
                value = int(scale.get_value())
                ec_commands.pwm.pwm_set_keyboard_backlight(app.cros_ec, value)
                self.led_kbd.set_subtitle(f"{value} %")

            current_kb_level = ec_commands.pwm.pwm_get_keyboard_backlight(app.cros_ec)[
                "percent"
            ]
            self.led_kbd_scale.set_value(current_kb_level)
            self.led_kbd.set_subtitle(f"{current_kb_level} %")
            self.led_kbd_scale.connect("value-changed", handle_led_kbd)
        else:
            self.led_kbd.set_visible(False)

        # Advanced options
        if ec_commands.general.get_cmd_versions(
            app.cros_ec, ec_commands.leds.EC_CMD_LED_CONTROL
        ):

            # Advanced: Power LED
            led_pwr_colour_strings = self.led_pwr_colour.get_model()

            all_colours = ["Red", "Green", "Blue", "Yellow", "White", "Amber"]

            def add_colours(strings, led_id):
                # Auto and Off should already be present
                if strings.get_n_items() <= 2:
                    supported_colours = ec_commands.leds.led_control_get_max_values(
                        app.cros_ec, led_id
                    )
                    for i, colour in enumerate(all_colours):
                        if supported_colours[i]:
                            strings.append(colour)

            add_colours(
                led_pwr_colour_strings, ec_commands.leds.EcLedId.EC_LED_ID_POWER_LED
            )

            def handle_led_colour(combobox, led_id):
                colour = combobox.get_selected() - 2
                match colour:
                    case -2:  # Auto
                        ec_commands.leds.led_control_set_auto(app.cros_ec, led_id)
                    case -1:  # Off
                        ec_commands.leds.led_control(
                            app.cros_ec,
                            led_id,
                            0,
                            [0] * ec_commands.leds.EcLedColors.EC_LED_COLOR_COUNT.value,
                        )
                    case _:  # Colour
                        colour_idx = all_colours.index(
                            combobox.get_selected_item().get_string()
                        )
                        ec_commands.leds.led_control_set_color(
                            app.cros_ec,
                            led_id,
                            100,
                            ec_commands.leds.EcLedColors(colour_idx),
                        )

            self.led_pwr_colour.connect(
                "notify::selected",
                lambda combo, _: handle_led_colour(
                    combo, ec_commands.leds.EcLedId.EC_LED_ID_POWER_LED
                ),
            )

            # Advanced: Charging LED
            led_chg_colour_strings = self.led_chg_colour.get_model()
            
            add_colours(
                led_chg_colour_strings,
                ec_commands.leds.EcLedId.EC_LED_ID_BATTERY_LED,
            )

            self.led_chg_colour.connect(
                "notify::selected",
                lambda combo, _: handle_led_colour(
                    combo, ec_commands.leds.EcLedId.EC_LED_ID_BATTERY_LED
                ),
            )
        else:
            self.led_advanced.set_visible(False)
