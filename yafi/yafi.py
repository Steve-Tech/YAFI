import sys
import os
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from cros_ec_python import get_cros_ec
import cros_ec_python.commands as ec_commands

class YAFI(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.cros_ec = get_cros_ec()

    def _change_page(self, builder, page):
        content = builder.get_object("content")
        while content_child := content.get_last_child():
            content.remove(content_child)
        content.append(page)

    def _update_thermals(self, fan_rpm, temp_items):
        ec_fans = ec_commands.memmap.get_fans(self.cros_ec)
        fan_rpm.set_subtitle(f"{ec_fans[0]} RPM")

        ec_temp_sensors = ec_commands.memmap.get_temps(self.cros_ec)
        for i, item in enumerate(temp_items):
            item.set_subtitle(f"{ec_temp_sensors[i]}°C")

        return self.current_page == 0

    def _thermals_page(self, builder):
        # Load the thermals.ui file
        thermals_builder = Gtk.Builder()
        thermals_builder.add_from_file(os.path.join(self.script_dir, "ui/thermals.ui"))

        # Get the root widget from the thermals.ui file
        thermals_root = thermals_builder.get_object("thermals-root")

        self._change_page(builder, thermals_root)

        fan_rpm = thermals_builder.get_object("fan-rpm")
        fan_mode = thermals_builder.get_object("fan-mode")
        fan_set_rpm = thermals_builder.get_object("fan-set-rpm")
        fan_set_percent = thermals_builder.get_object("fan-set-percent")
        fan_percent_scale = thermals_builder.get_object("fan-percent-scale")

        def handle_fan_mode(mode):
            match mode:
                case 0:  # Auto
                    fan_set_rpm.set_visible(False)
                    fan_set_percent.set_visible(False)
                    ec_commands.thermal.thermal_auto_fan_ctrl(self.cros_ec)
                case 1: # Percent
                    fan_set_rpm.set_visible(False)
                    fan_set_percent.set_visible(True)
                case 2: # RPM
                    fan_set_rpm.set_visible(True)
                    fan_set_percent.set_visible(False)

        fan_mode.connect("notify::selected", lambda combo, _: handle_fan_mode(combo.get_selected()))

        def handle_fan_percent(scale):
            percent = int(scale.get_value())
            ec_commands.pwm.pwm_set_fan_duty(self.cros_ec, percent)
            fan_set_percent.set_subtitle(f"{percent} %")

        fan_percent_scale.connect("value-changed", handle_fan_percent)

        def handle_fan_rpm(entry):
            rpm = int(entry.get_text())
            ec_commands.pwm.pwm_set_fan_rpm(self.cros_ec, rpm)

        fan_set_rpm.connect("notify::text", lambda entry, _: handle_fan_rpm(entry))

        temperatures = thermals_builder.get_object("temperatures")
        temp_items = []

        ec_temp_sensors = ec_commands.thermal.get_temp_sensors(self.cros_ec)
        for key, value in ec_temp_sensors.items():
            new_row = Adw.ActionRow(title=key, subtitle=f"{value[0]}°C")
            new_row.add_css_class("property")
            temperatures.append(new_row)
            temp_items.append(new_row)

        self._update_thermals(fan_rpm, temp_items)

        # Schedule _update_thermals to run every second
        GLib.timeout_add_seconds(1, self._update_thermals, fan_rpm, temp_items)

    def _leds_page(self, builder):
        # Load the leds.ui file
        leds_builder = Gtk.Builder()
        leds_builder.add_from_file(os.path.join(self.script_dir, "ui/leds.ui"))

        # Get the root widget from the leds.ui file
        leds_root = leds_builder.get_object("leds-root")

        self._change_page(builder, leds_root)

    def _battery_page(self, builder):
        # Load the battery.ui file
        battery_builder = Gtk.Builder()
        battery_builder.add_from_file(os.path.join(self.script_dir, "ui/battery.ui"))

        # Get the root widget from the battery.ui file
        battery_root = battery_builder.get_object("battery-root")

        self._change_page(builder, battery_root)

    def _hardware_page(self, builder):
        # Load the hardware.ui file
        hardware_builder = Gtk.Builder()
        hardware_builder.add_from_file(os.path.join(self.script_dir, "ui/hardware.ui"))

        # Get the root widget from the hardware.ui file
        hardware_root = hardware_builder.get_object("hardware-root")

        self._change_page(builder, hardware_root)

    def _about_page(self, app_builder):
        # Open About dialog
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(self.script_dir, "ui/about.ui"))

        about = builder.get_object("about-root")
        about.set_modal(True)
        about.set_transient_for(self.win)

        # Reset the selection in the navbar
        navbar = app_builder.get_object("navbar")
        about.connect("close-request", lambda _: navbar.select_row(navbar.get_row_at_index(self.current_page)))
        
        about.present()

    def on_activate(self, app):
        # Create a Builder
        builder = Gtk.Builder()
        builder.add_from_file(os.path.join(self.script_dir, "ui/yafi.ui"))

        self.current_page = 0
        self._thermals_page(builder)

        pages = (("Thermals", self._thermals_page), ("LEDs", self._leds_page), ("Battery", self._battery_page), ("Hardware", self._hardware_page), ("About", self._about_page))

        # Build the navbar
        navbar = builder.get_object("navbar")
        for page in pages:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=page[0]))
            navbar.append(row)

        def switch_page(page):
            # About page is a special case
            if page != len(pages) - 1:
                self.current_page = page
            pages[page][1](builder)
        
        navbar.connect("row-activated", lambda box, row: switch_page(row.get_index()))

        # Obtain and show the main window
        self.win = builder.get_object("root")
        self.win.set_application(self)
        self.win.present()

app = YAFI(application_id="au.stevetech.yafi")
app.run(sys.argv)
