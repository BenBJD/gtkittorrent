import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio
from gtkittorrent.views.main_window import MainWindow
from gtkittorrent.views.welcome_window import WelcomeWindow
from gtkittorrent.client import QBittorrentClient
from gtkittorrent.settings import Settings

class GTKittorrentApp(Adw.Application):
    def __init__(self):
        super().__init__(
            application_id="io.github.BenBJD.gtkittorrent",
            flags=Gio.ApplicationFlags.HANDLES_OPEN
        )
        self.settings = Settings()
        self.client = QBittorrentClient(
            host=self.settings.get("host"),
            username=self.settings.get("username"),
            password=self.settings.get("password")
        )
        self.win = None
        self.welcome_win = None

    def do_startup(self):
        Adw.Application.do_startup(self)
        import os
        from gi.repository import Gdk
        from gtkittorrent.settings import apply_theme
        apply_theme(self.settings.get("theme", "system"))
        base_dir = os.path.dirname(os.path.abspath(__file__))
        possible_icon_dirs = [
            os.path.join(base_dir, "data", "icons"),
            os.path.join(os.path.dirname(base_dir), "data", "icons"),
            os.path.join(os.path.dirname(os.path.dirname(base_dir)), "data", "icons"),
            "/usr/share/icons",
            "/usr/local/share/icons",
        ]
        display = Gdk.Display.get_default()
        if display:
            theme = Gtk.IconTheme.get_for_display(display)
            for path in possible_icon_dirs:
                if os.path.isdir(path):
                    theme.add_search_path(path)

    def do_activate(self):
        self.win = self.get_active_window()
        if self.win:
            self.win.present()
            return

        is_welcome_completed = self.settings.get("welcome_completed", False)
        if not is_welcome_completed:
            self._show_welcome_screen(is_reconnect=False)
            return

        self.settings.set("configured", True)
        self._show_main_window()
        self.win.start_initial_connection()

    def do_shutdown(self):
        is_local = self.settings.is_current_local() if hasattr(self.settings, "is_current_local") else True
        is_flatpak = self.settings.is_flatpak() if hasattr(self.settings, "is_flatpak") else False
        if self.settings.get("engine_stop_on_exit", False) and is_local and not is_flatpak:
            from gtkittorrent.client.daemon import LocalDaemonManager
            LocalDaemonManager.get_instance().stop_daemon(self.client)
        Adw.Application.do_shutdown(self)

    def do_open(self, files, n_files, hint):
        self.do_activate()
        if not self.win:
            return

        from gtkittorrent.views.dialogs.add_torrent_dialog import AddTorrentDialog
        for f in files:
            path = f.get_path()
            uri = f.get_uri()
            if uri and uri.startswith("magnet:///?"):
                uri = "magnet:?" + uri[len("magnet:///?"):]

            if path and (path.endswith(".torrent") or (f.query_info and "bittorrent" in str(f.query_info("*", 0)))):
                add_dlg = AddTorrentDialog(self.win, self.client, torrent_file=path)
                add_dlg.present()
            elif uri and (uri.startswith("magnet:") or uri.startswith("http://") or uri.startswith("https://")):
                add_dlg = AddTorrentDialog(self.win, self.client, torrent_url=uri)
                add_dlg.present()

    def _on_welcome_connected(self):
        self._show_main_window()
        if self.win and hasattr(self.win, "start_initial_connection"):
            self.win.start_initial_connection()

    def _show_welcome_screen(self, is_reconnect=False):
        self.welcome_win = WelcomeWindow(self, self.settings, self.client, is_reconnect=is_reconnect)
        self.welcome_win.connect("connected", lambda w: self._on_welcome_connected())
        self.welcome_win.present()

    def _show_main_window(self):
        if not self.win:
            self.win = MainWindow(self, self.client)
        self.win.present()