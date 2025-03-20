import os

# Register resources if not running in Flatpak
if not os.environ.get('FLATPAK_ID'):
    from gi.repository import Gio
    resource = Gio.Resource.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'yafi.gresource'))
    resource._register()

from .main import main
