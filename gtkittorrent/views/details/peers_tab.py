import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gio
from ...models.peer import PeerItem

class PeersTab(Gtk.Box):
    """Peers tab displaying connected peers and transfer rates."""

    def __init__(self, client):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.client = client
        self.torrent_hash = None
        self.peer_rid = 0
        self.peers_dict = {}
        self.model = Gio.ListStore(item_type=PeerItem)

        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.append(scrolled)

        self.selection_model = Gtk.SingleSelection(model=self.model)
        self.column_view = Gtk.ColumnView(model=self.selection_model)
        scrolled.set_child(self.column_view)

        self._setup_columns()

    def _setup_columns(self):
        cols = [
            ("IP", "ip", 130),
            ("Port", "port", 70),
            ("Client", "client", 140),
            ("Flags", "flags", 80),
            ("Progress", "progress_str", 90),
            ("Down Speed", "dlspeed_str", 100),
            ("Up Speed", "upspeed_str", 100),
            ("Downloaded", "downloaded_str", 100),
            ("Uploaded", "uploaded_str", 100),
        ]
        for title, prop_name, width in cols:
            factory = Gtk.SignalListItemFactory()
            factory.connect("setup", lambda f, item: item.set_child(Gtk.Label(xalign=0, margin_start=4, margin_end=4)))
            
            def bind_col(f, item, p_name=prop_name):
                p_item = item.get_item()
                lbl = item.get_child()
                if p_item and lbl:
                    lbl.set_text(str(getattr(p_item, p_name, "")))
            
            factory.connect("bind", bind_col)
            col = Gtk.ColumnViewColumn(title=title, factory=factory)
            col.set_fixed_width(width)
            col.set_resizable(True)
            self.column_view.append_column(col)

    def update(self, torrent_item):
        if not torrent_item:
            self.torrent_hash = None
            self.model.remove_all()
            self.peers_dict.clear()
            self.peer_rid = 0
            return

        if self.torrent_hash != torrent_item.hash:
            self.torrent_hash = torrent_item.hash
            self.model.remove_all()
            self.peers_dict.clear()
            self.peer_rid = 0

        data = self.client.sync_torrent_peers(self.torrent_hash, rid=self.peer_rid) if self.client else None
        if not data:
            return

        self.peer_rid = data.get('rid', self.peer_rid)
        peers_data = data.get('peers', {})
        peers_removed = data.get('peers_removed', [])

        # Remove deleted peers
        for p_key in peers_removed:
            if p_key in self.peers_dict:
                item = self.peers_dict.pop(p_key)
                for i in range(self.model.get_n_items()):
                    if self.model.get_item(i) == item:
                        self.model.remove(i)
                        break

        # Update or append
        for p_key, p_info in peers_data.items():
            if p_key in self.peers_dict:
                self.peers_dict[p_key].update(p_info)
            else:
                p_item = PeerItem(p_info)
                self.peers_dict[p_key] = p_item
                self.model.append(p_item)
