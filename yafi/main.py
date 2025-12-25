# main.py
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

import os
import sys
import traceback
import threading
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw, GLib
from .window import YafiWindow
from .thermals import ThermalsPage
from .leds import LedsPage
from .battery import BatteryPage
from .battery_limiter import BatteryLimiterPage
from .hardware import HardwarePage

from cros_ec_python import get_cros_ec


class YafiApplication(Adw.Application):
    """The main application singleton class."""

    def __init__(self):
        super().__init__(application_id='au.stevetech.yafi',
                         flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
                         resource_base_path='/au/stevetech/yafi')

        self.current_page = 0
        self.no_support = []
        self.cros_ec = None
        self.win = None

    def change_page(self, content, page):
        page.setup(self)
        while content_child := content.get_last_child():
            content.remove(content_child)
        content.append(page)

    def do_activate(self):
        """Called when the application is activated.

        We raise the application's main window, creating it if
        necessary.
        """
        self.win = self.props.active_window
        if not self.win:
            self.win = YafiWindow(application=self)

        # Update the splash screen
        splash = getattr(sys, 'frozen', False) and '_PYI_SPLASH_IPC' in os.environ
        if splash:
            import pyi_splash
            pyi_splash.update_text("Detecting EC")

        try:
            self.cros_ec = get_cros_ec()
            pass
        except Exception as e:
            traceback.print_exc()

            self.error = e

            message = (
                str(e)
                + "\n\n"
                + "This application only supports Framework Laptops.\n"
                + "If you are using a Framework Laptop, there are additional troubleshooting steps in the README."
            )
            self.show_error("EC Initalisation Error", message)

            if splash:
                pyi_splash.close()

            self.win.present()
            return

        if splash:
            pyi_splash.update_text("Building Interface")

        self.change_page(self.win.content, ThermalsPage())

        pages = (
            ("Thermals", ThermalsPage()),
            ("LEDs", LedsPage()),
            ("Battery", BatteryPage()),
            ("Battery Limiter", BatteryLimiterPage()),
            ("Sensors", HardwarePage()),
            ("About", None),
        )

        # Build the navbar
        for page in pages:
            row = Gtk.ListBoxRow()
            row.set_child(Gtk.Label(label=page[0]))
            self.win.navbar.append(row)

        def switch_page(page):
            # About page is a special case
            if pages[page][1]:
                self.current_page = page
                self.change_page(self.win.content, pages[page][1])
            else:
                self.on_about_action()

        self.win.navbar.connect("row-activated", lambda box, row: switch_page(row.get_index()))

        if splash:
            pyi_splash.close()

        self.win.present()

    def on_about_action(self, *args):
        """Callback for the app.about action."""
        about = Adw.AboutDialog(
            application_icon="au.stevetech.yafi",
            application_name="Yet Another Framework Interface",
            comments="YAFI is another GUI for the Framework Laptop Embedded Controller.\n\n"
            + "It is written in Python with a GTK4 Adwaita theme, and uses the CrOS_EC_Python library to communicate with the EC.\n\n"
            + "YAFI is not affiliated with Framework Computer Inc. in any way.",
            copyright="© 2025 Stephen Horvath",
            developer_name="Stephen Horvath",
            developers=["Stephen Horvath https://github.com/Steve-Tech"],
            issue_url="https://github.com/Steve-Tech/YAFI/issues",
            license_type=Gtk.License.GPL_2_0,
            version="0.7",
            website="https://github.com/Steve-Tech/YAFI",
        )
        about.add_acknowledgement_section(None, ["Framework Computer Inc. https://frame.work/"])
        about.present(self.props.active_window)

        if hasattr(self, 'debug_info'):
            about.set_debug_info(self.debug_info)
        else:
            threading.Thread(target=lambda: GLib.idle_add(about.set_debug_info, self.generate_debug_info())).start()

    def show_error(self, heading, message):
        dialog = Adw.AlertDialog(heading=heading, body=message)
        dialog.add_response("exit", "Exit")
        dialog.add_response("about", "About")
        dialog.set_default_response("exit")
        dialog.connect("response", lambda d, r: self.on_about_action() if r == "about" else self.win.destroy())
        dialog.present(self.win)

    def generate_debug_info(self):
        if hasattr(self, 'debug_info'):
            return self.debug_info

        info = "YAFI Debug Information\n\n"

        if hasattr(self, 'error'):
            if isinstance(self.error, Exception):
                info += f"{type(self.error).__name__}: {self.error}\n\n"
                info += ''.join(traceback.format_exception(type(self.error), self.error, self.error.__traceback__))
                info += "\n\n"
            else:
                info += f"Error: {self.error}\n\n"

        info += f"Python Version: {sys.version}\n"
        info += f"GTK Version: {Gtk.get_major_version()}.{Gtk.get_minor_version()}.{Gtk.get_micro_version()}\n"
        info += f"Adwaita Version: {Adw.get_major_version()}.{Adw.get_minor_version()}.{Adw.get_micro_version()}\n"

        try:
            import platform
            info += f"Platform: {platform.platform()}\n"
            info += f"Processor: {platform.processor() or platform.machine()}\n"
        except Exception as e:
            info += f"Platform Error: {type(e).__name__}: {e}\n"

        try:
            import importlib.metadata
            info += f"Installed Packages: {[(dist.metadata['Name'], dist.version) for dist in importlib.metadata.distributions()]}\n"
        except Exception as e:
            info += f"Importlib Error: {type(e).__name__}: {e}\n"

        try:
            if sys.platform == "linux":
                with open('/sys/devices/virtual/dmi/id/sys_vendor', 'r') as f:
                    info += f"Manufacturer: {f.read().strip()}\n"
                with open('/sys/devices/virtual/dmi/id/product_name', 'r') as f:
                    info += f"Model: {f.read().strip()}\n"
                with open('/sys/devices/virtual/dmi/id/product_sku', 'r') as f:
                    info += f"SKU: {f.read().strip()}\n"
                with open('/sys/devices/virtual/dmi/id/board_name', 'r') as f:
                    info += f"Board: {f.read().strip()}\n"
                with open('/sys/devices/virtual/dmi/id/bios_vendor', 'r') as f:
                    info += f"BIOS Vendor: {f.read().strip()}\n"
                with open('/sys/devices/virtual/dmi/id/bios_version', 'r') as f:
                    info += f"BIOS Version: {f.read().strip()}\n"
                with open('/sys/devices/virtual/dmi/id/bios_date', 'r') as f:
                    info += f"BIOS Date: {f.read().strip()}\n"
            elif sys.platform == "win32":
                import subprocess
                ps_cmd = (
                    "powershell -Command "
                    "\"$cs = Get-CimInstance -ClassName Win32_ComputerSystem; "
                    "$board = Get-CimInstance -ClassName Win32_BaseBoard; "
                    "$bios = Get-CimInstance -ClassName Win32_BIOS; "
                    "Write-Output $cs.Manufacturer; "
                    "Write-Output $cs.Model; "
                    "Write-Output $cs.SystemSKUNumber; "
                    "Write-Output $board.Product; "
                    "Write-Output $bios.Manufacturer; "
                    "Write-Output $bios.Name; "
                    "Write-Output $bios.ReleaseDate\""
                )
                output = subprocess.check_output(ps_cmd, shell=True).decode().splitlines()
                info += f"Manufacturer: {output[0]}\n"
                info += f"Model: {output[1]}\n"
                info += f"SKU: {output[2]}\n"
                info += f"Board: {output[3]}\n"
                info += f"BIOS Vendor: {output[4]}\n"
                info += f"BIOS Version: {output[5]}\n"
                # Blank line in the output for some reason
                info += f"BIOS Date: {output[7]}\n"
        except Exception as e:
            info += f"System Info Error: {type(e).__name__}: {e}\n"

        if self.cros_ec:
            info += f"EC Interface: {type(self.cros_ec).__name__}\n"
            try:
                    import cros_ec_python.commands as ec_commands
                    info += f"EC Version: {ec_commands.general.get_version(self.cros_ec)["version_string_ro"]}\n"
                    info += f"EC Chip: {ec_commands.general.get_chip_info(self.cros_ec)}\n"
                    info += f"EC Build Info: {ec_commands.general.get_build_info(self.cros_ec)}\n"
                    info += f"EC Protocol Version: {ec_commands.general.proto_version(self.cros_ec)}\n"
                    info += f"EC Protocol Info: {ec_commands.general.get_protocol_info(self.cros_ec)}\n"
            except Exception as e:
                info += f"EC Info Error: {type(e).__name__}: {e}\n"
        
        self.debug_info = info
        return info


def main():
    """The application's entry point."""
    app = YafiApplication()
    return app.run(sys.argv)
