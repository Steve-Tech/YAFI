import sys
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

class YAFI(Adw.Application):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.connect('activate', self.on_activate)

    def _change_page(self, builder, page):
        content = builder.get_object("content")
        while content_child := content.get_last_child():
            content.remove(content_child)
        content.append(page)

    def _thermals_page(self, builder):
        # Load the thermals.ui file
        thermals_builder = Gtk.Builder()
        thermals_builder.add_from_file("thermals.ui")

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
                case 1: # Percent
                    fan_set_rpm.set_visible(False)
                    fan_set_percent.set_visible(True)
                case 2: # RPM
                    fan_set_rpm.set_visible(True)
                    fan_set_percent.set_visible(False)

        fan_rpm.set_subtitle("1200 RPM")

        fan_mode.connect("notify::selected", lambda combo, _: handle_fan_mode(combo.get_selected()))

        fan_percent_scale.connect(
            "value-changed",
            lambda scale: fan_set_percent.set_subtitle(f"{int(scale.get_value())} %"),
        )

        temperatures = thermals_builder.get_object("temperatures")

        for i in ((25.0, "Sensor 1"), (30.0, "Sensor 2"), (35.0, "Sensor 3"), (40.0, "Sensor 4")):
            new_row = Adw.ActionRow(title=i[1], subtitle=f"{i[0]}°C")
            new_row.add_css_class("property")
            temperatures.append(new_row)

    def _leds_page(self, builder):
        # Load the leds.ui file
        leds_builder = Gtk.Builder()
        leds_builder.add_from_file("leds.ui")

        # Get the root widget from the leds.ui file
        leds_root = leds_builder.get_object("leds-root")

        self._change_page(builder, leds_root)

    def _battery_page(self, builder):
        # Load the battery.ui file
        battery_builder = Gtk.Builder()
        battery_builder.add_from_file("battery.ui")

        # Get the root widget from the battery.ui file
        battery_root = battery_builder.get_object("battery-root")

        self._change_page(builder, battery_root)

    def _hardware_page(self, builder):
        # Load the hardware.ui file
        hardware_builder = Gtk.Builder()
        hardware_builder.add_from_file("hardware.ui")

        # Get the root widget from the hardware.ui file
        hardware_root = hardware_builder.get_object("hardware-root")

        self._change_page(builder, hardware_root)

    def on_activate(self, app):
        # Create a Builder
        builder = Gtk.Builder()
        builder.add_from_file("yafi.ui")

        self._thermals_page(builder)

        pages = (("Thermals", self._thermals_page), ("LEDs", self._leds_page), ("Battery", self._battery_page), ("Hardware", self._hardware_page), ("About", self._leds_page))

        # Build the navbar
        navbar = builder.get_object("navbar")
        for page in pages:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=page[0]))
            navbar.append(row)
        
        navbar.connect("row-activated", lambda box, row: pages[row.get_index()][1](builder))

        # Obtain and show the main window
        self.win = builder.get_object("root")
        self.win.set_application(self)
        self.win.present()

app = YAFI(application_id="au.stevetech.yafi")
app.run(sys.argv)
