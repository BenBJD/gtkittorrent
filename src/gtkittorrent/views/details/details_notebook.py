import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gdk
from .general_tab import GeneralTab
from .trackers_tab import TrackersTab
from .peers_tab import PeersTab
from .content_tab import ContentTab
from .speed_tab import SpeedTab
from .log_tab import LogTab

def _choose_icon(candidates):
    """Pick the first icon available in the current icon theme without falling back to image-missing."""
    display = Gdk.Display.get_default()
    if display:
        theme = Gtk.IconTheme.get_for_display(display)
        for name in candidates:
            info = theme.lookup_icon(name, None, 16, 1, Gtk.TextDirection.NONE, 0)
            if info and "image-missing" not in info.get_file().get_path():
                return name
    return candidates[-1]

class DetailsNotebook(Gtk.Box):
    """Complete bottom details panel containing all tabs matching qBittorrent."""

    def __init__(self, client):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.client = client
        self.current_torrent = None

        self.stack = Adw.ViewStack(vexpand=True)

        self.general_tab = GeneralTab(self.client)
        self.stack.add_titled_with_icon(
            self.general_tab, "general", "General",
            _choose_icon(["dialog-information-symbolic", "document-properties-symbolic"])
        )

        self.trackers_tab = TrackersTab(self.client)
        self.stack.add_titled_with_icon(
            self.trackers_tab, "trackers", "Trackers",
            _choose_icon(["network-server-symbolic", "network-workgroup-symbolic"])
        )

        self.peers_tab = PeersTab(self.client)
        self.stack.add_titled_with_icon(
            self.peers_tab, "peers", "Peers",
            _choose_icon(["system-users-symbolic", "avatar-default-symbolic"])
        )

        self.content_tab = ContentTab(self.client)
        self.stack.add_titled_with_icon(
            self.content_tab, "content", "Content",
            _choose_icon(["folder-symbolic", "folder-documents-symbolic"])
        )

        self.speed_tab = SpeedTab(self.client)
        self.stack.add_titled_with_icon(
            self.speed_tab, "speed", "Speed",
            _choose_icon(["speedometer-symbolic", "network-transmit-receive-symbolic"])
        )

        self.log_tab = LogTab(self.client)
        self.stack.add_titled_with_icon(
            self.log_tab, "log", "Execution Log",
            _choose_icon(["utilities-terminal-symbolic", "text-x-generic-symbolic"])
        )

        # Top Switcher Bar
        switcher_bar = Adw.ViewSwitcher(
            stack=self.stack,
            policy=Adw.ViewSwitcherPolicy.WIDE,
            margin_top=4,
            margin_bottom=4
        )
        self.append(switcher_bar)
        self.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        self.append(self.stack)

        self.stack.connect("notify::visible-child-name", self._on_visible_child_changed)
        self.set_size_request(-1, 240)

    def _on_visible_child_changed(self, stack, pspec):
        if self.current_torrent:
            child_name = stack.get_visible_child_name()
            if child_name == "log":
                self.log_tab.refresh_logs()
            elif child_name == "peers":
                self.peers_tab.update(self.current_torrent)

    @property
    def torrent_hash(self):
        return self.current_torrent.hash if self.current_torrent else None

    @property
    def general_label(self):
        class CompLabel:
            def __init__(self, tab):
                self.tab = tab
            def get_text(self):
                return f"{self.tab.lbl_save_path.get_text()} {self.tab.lbl_comment.get_text()}"
        return CompLabel(self.general_tab)

    @property
    def trackers_label(self):
        class CompLabel:
            def __init__(self, tab):
                self.tab = tab
            def get_text(self):
                items = [self.tab.model.get_item(i) for i in range(self.tab.model.get_n_items())]
                return " ".join([f"[{it.status}] {it.url}" for it in items])
        return CompLabel(self.trackers_tab)

    @property
    def content_label(self):
        class CompLabel:
            def __init__(self, tab):
                self.tab = tab
            def get_text(self):
                items = [self.tab.model.get_item(i) for i in range(self.tab.model.get_n_items())]
                return " ".join([f"{it.name}" for it in items])
        return CompLabel(self.content_tab)

    def update(self, torrent_item):
        self.current_torrent = torrent_item
        self.general_tab.update(torrent_item)
        self.trackers_tab.update(torrent_item)
        self.content_tab.update(torrent_item)
        self.peers_tab.update(torrent_item)

    def update_speed(self, dl_rate, up_rate):
        self.speed_tab.add_data_point(dl_rate, up_rate)
