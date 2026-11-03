import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gio, Adw
from ...models.tracker import TrackerItem

class TrackersTab(Gtk.Box):
    """Trackers list tab with Add, Edit, Remove, and Reannounce actions."""

    def __init__(self, client):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.client = client
        self.torrent_hash = None
        self.model = Gio.ListStore(item_type=TrackerItem)

        # Action bar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        self.append(toolbar)

        add_btn = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Add Tracker")
        add_btn.connect("clicked", self._on_add_tracker)
        toolbar.append(add_btn)

        edit_btn = Gtk.Button(icon_name="document-edit-symbolic", tooltip_text="Edit Tracker")
        edit_btn.connect("clicked", self._on_edit_tracker)
        toolbar.append(edit_btn)

        del_btn = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Remove Tracker")
        del_btn.connect("clicked", self._on_delete_tracker)
        toolbar.append(del_btn)

        reannounce_btn = Gtk.Button(icon_name="view-refresh-symbolic", tooltip_text="Reannounce to all trackers")
        reannounce_btn.connect("clicked", self._on_reannounce)
        toolbar.append(reannounce_btn)

        # Scrolled ColumnView
        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.append(scrolled)

        self.selection_model = Gtk.SingleSelection(model=self.model)
        self.column_view = Gtk.ColumnView(model=self.selection_model)
        scrolled.set_child(self.column_view)

        self._setup_columns()

    def _setup_columns(self):
        cols = [
            ("Tier", "tier", 50),
            ("URL", "url", 300),
            ("Status", "status", 100),
            ("Peers", "peers", 70),
            ("Seeds", "seeds", 70),
            ("Leeches", "leeches", 70),
            ("Message", "msg", 200),
        ]
        for title, prop_name, width in cols:
            factory = Gtk.SignalListItemFactory()
            factory.connect("setup", lambda f, item: item.set_child(Gtk.Label(xalign=0, margin_start=4, margin_end=4)))
            
            def bind_col(f, item, p_name=prop_name):
                t_item = item.get_item()
                lbl = item.get_child()
                if t_item and lbl:
                    lbl.set_text(str(getattr(t_item, p_name, "")))
            
            factory.connect("bind", bind_col)
            col = Gtk.ColumnViewColumn(title=title, factory=factory)
            col.set_fixed_width(width)
            col.set_resizable(True)
            self.column_view.append_column(col)

    def update(self, torrent_item):
        if not torrent_item:
            self.torrent_hash = None
            self.model.remove_all()
            return

        self.torrent_hash = torrent_item.hash
        trackers = self.client.get_torrent_trackers(self.torrent_hash) if self.client else []
        self.model.remove_all()
        for t in trackers:
            self.model.append(TrackerItem(t))

    def _on_add_tracker(self, btn):
        if not self.torrent_hash:
            return
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Add Tracker",
            body="Enter tracker URL(s) (one per line):"
        )
        entry = Gtk.Entry(placeholder_text="http://tracker.example.com/announce")
        entry.set_margin_top(12)
        entry.set_margin_bottom(12)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        dialog.set_extra_child(entry)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("add", "Add")
        dialog.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)

        def on_resp(d, resp):
            if resp == "add":
                url = entry.get_text().strip()
                if url:
                    self.client.add_trackers(self.torrent_hash, [url])
                    self.update(type('Dummy', (), {'hash': self.torrent_hash})())
            d.destroy()

        dialog.connect("response", on_resp)
        dialog.show()

    def _on_edit_tracker(self, btn):
        selected = self.selection_model.get_selected_item()
        if not selected or not self.torrent_hash:
            return

        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Edit Tracker",
            body="Modify tracker URL:"
        )
        entry = Gtk.Entry()
        entry.set_text(selected.url)
        entry.set_margin_top(12)
        entry.set_margin_bottom(12)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        dialog.set_extra_child(entry)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)

        def on_resp(d, resp):
            if resp == "save":
                new_url = entry.get_text().strip()
                if new_url and new_url != selected.url:
                    self.client.edit_tracker(self.torrent_hash, selected.url, new_url)
                    self.update(type('Dummy', (), {'hash': self.torrent_hash})())
            d.destroy()

        dialog.connect("response", on_resp)
        dialog.show()

    def _on_delete_tracker(self, btn):
        selected = self.selection_model.get_selected_item()
        if not selected or not self.torrent_hash:
            return
        self.client.remove_trackers(self.torrent_hash, [selected.url])
        self.update(type('Dummy', (), {'hash': self.torrent_hash})())

    def _on_reannounce(self, btn):
        if self.torrent_hash:
            self.client.reannounce_torrent(self.torrent_hash)
