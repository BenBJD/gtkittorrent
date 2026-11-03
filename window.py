"""Window module re-exporting MainWindow and components for backwards compatibility."""
from gtkittorrent.views.main_window import MainWindow
from gtkittorrent.models.torrent import TorrentItem
from gtkittorrent.views.dialogs.preferences_dialog import PreferencesDialog as SettingsWindow
from gtkittorrent.views.details.details_notebook import DetailsNotebook as DetailsPanel
from gtkittorrent.views.welcome_window import WelcomeWindow

__all__ = [
    'MainWindow',
    'TorrentItem',
    'SettingsWindow',
    'DetailsPanel',
    'WelcomeWindow',
]
