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

import sys
import traceback
import gi
from gi.repository import Gio

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Gio, Adw
from .window import YafiWindow
from .thermals import ThermalsPage
from .leds import LedsPage
from .battery import BatteryPage
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

        try:
            self.cros_ec = get_cros_ec()
            pass
        except Exception as e:
            traceback.print_exc()

            message = (
                str(e)
                + "\n\n"
                + "This application only supports Framework Laptops.\n"
                + "If you are using a Framework Laptop, there are additional troubleshooting steps in the README."
            )
            self.show_error("EC Initalisation Error", message)
            self.win.present()
            return

        self.change_page(self.win.content, ThermalsPage())

        pages = (
            ("Thermals", ThermalsPage()),
            ("LEDs", LedsPage()),
            ("Battery", BatteryPage()),
            ("Hardware", HardwarePage()),
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

        self.win.present()

    def on_about_action(self, *args):
        """Callback for the app.about action."""
        about = Adw.AboutDialog(
            application_icon="au.stevetech.yafi",
            application_name="Yet Another Framework Interface",
            comments="YAFI is another GUI for the Framework Laptop Embedded Controller.\n"
            + "It is written in Python with a GTK3 theme, and uses the `CrOS_EC_Python` library to communicate with the EC.",
            copyright="© 2025 Stephen Horvath",
            developer_name="Stephen Horvath",
            developers=["Stephen Horvath"],
            issue_url="https://github.com/Steve-Tech/YAFI/issues",
            license_type=Gtk.License.GPL_2_0,
            version="0.2",
            website="https://github.com/Steve-Tech/YAFI",
        )
        about.add_acknowledgement_section(None, ["Framework Computer Inc. https://frame.work/"])
        about.present(self.props.active_window)

    def show_error(self, heading, message):
        dialog = Adw.AlertDialog(heading=heading, body=message)
        dialog.add_response("exit", "Exit")
        dialog.connect("response", lambda d, r: self.win.destroy())
        dialog.present(self.win)


def main():
    """The application's entry point."""
    app = YafiApplication()
    return app.run(sys.argv)
