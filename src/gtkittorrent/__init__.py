"""GTKittorrent - GTK4 / Libadwaita frontend for qBittorrent."""

__version__ = "0.1.0"

from gtkittorrent.app import GTKittorrentApp
from gtkittorrent.settings import Settings
from gtkittorrent.main import main

__all__ = ["GTKittorrentApp", "Settings", "main", "__version__"]
