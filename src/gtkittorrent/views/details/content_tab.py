import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gio, Adw
from ...models.file_item import FileItem

class ContentTab(Gtk.Box):
    """Content/Files tab with file priorities and rename capabilities."""

    def __init__(self, client):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.client = client
        self.torrent_hash = None
        self.model = Gio.ListStore(item_type=FileItem)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        self.append(toolbar)

        prio_high_btn = Gtk.Button(label="High Priority")
        prio_high_btn.connect("clicked", lambda x: self._set_selected_priority(6))
        toolbar.append(prio_high_btn)

        prio_norm_btn = Gtk.Button(label="Normal Priority")
        prio_norm_btn.connect("clicked", lambda x: self._set_selected_priority(1))
        toolbar.append(prio_norm_btn)

        prio_none_btn = Gtk.Button(label="Do Not Download")
        prio_none_btn.connect("clicked", lambda x: self._set_selected_priority(0))
        toolbar.append(prio_none_btn)

        rename_btn = Gtk.Button(icon_name="document-edit-symbolic", tooltip_text="Rename File")
        rename_btn.connect("clicked", self._on_rename_file)
        toolbar.append(rename_btn)

        # Scrolled ColumnView
        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.append(scrolled)

        self.selection_model = Gtk.SingleSelection(model=self.model)
        self.column_view = Gtk.ColumnView(model=self.selection_model)
        scrolled.set_child(self.column_view)

        self._setup_columns()

    def _setup_columns(self):
        # Name
        factory_name = Gtk.SignalListItemFactory()
        factory_name.connect("setup", lambda f, item: item.set_child(Gtk.Label(xalign=0, margin_start=4, margin_end=4, ellipsize=3)))
        def bind_name(f, item):
            f_item = item.get_item()
            lbl = item.get_child()
            if f_item and lbl:
                lbl.set_text(f_item.name)
        factory_name.connect("bind", bind_name)
        col_name = Gtk.ColumnViewColumn(title="Name", factory=factory_name)
        col_name.set_expand(True)
        self.column_view.append_column(col_name)

        # Size
        factory_size = Gtk.SignalListItemFactory()
        factory_size.connect("setup", lambda f, item: item.set_child(Gtk.Label(xalign=1, margin_start=4, margin_end=4)))
        factory_size.connect("bind", lambda f, item: item.get_child().set_text(item.get_item().size_str if item.get_item() else ""))
        col_size = Gtk.ColumnViewColumn(title="Size", factory=factory_size)
        col_size.set_fixed_width(100)
        self.column_view.append_column(col_size)

        # Progress
        factory_prog = Gtk.SignalListItemFactory()
        factory_prog.connect("setup", lambda f, item: item.set_child(Gtk.ProgressBar(show_text=True, margin_start=4, margin_end=4)))
        def bind_prog(f, item):
            f_item = item.get_item()
            bar = item.get_child()
            if f_item and bar:
                bar.set_fraction(f_item.progress)
        factory_prog.connect("bind", bind_prog)
        col_prog = Gtk.ColumnViewColumn(title="Progress", factory=factory_prog)
        col_prog.set_fixed_width(140)
        self.column_view.append_column(col_prog)

        # Priority
        factory_prio = Gtk.SignalListItemFactory()
        factory_prio.connect("setup", lambda f, item: item.set_child(Gtk.Label(xalign=0, margin_start=4, margin_end=4)))
        factory_prio.connect("bind", lambda f, item: item.get_child().set_text(item.get_item().priority_str if item.get_item() else ""))
        col_prio = Gtk.ColumnViewColumn(title="Priority", factory=factory_prio)
        col_prio.set_fixed_width(120)
        self.column_view.append_column(col_prio)

        # Remaining
        factory_rem = Gtk.SignalListItemFactory()
        factory_rem.connect("setup", lambda f, item: item.set_child(Gtk.Label(xalign=1, margin_start=4, margin_end=4)))
        factory_rem.connect("bind", lambda f, item: item.get_child().set_text(item.get_item().remaining_str if item.get_item() else ""))
        col_rem = Gtk.ColumnViewColumn(title="Remaining", factory=factory_rem)
        col_rem.set_fixed_width(100)
        self.column_view.append_column(col_rem)

    def update(self, torrent_item):
        if not torrent_item:
            self.torrent_hash = None
            self.model.remove_all()
            return

        self.torrent_hash = torrent_item.hash
        files = self.client.get_torrent_contents(self.torrent_hash) if self.client else []
        
        # If item count matches, update in-place
        if len(files) == self.model.get_n_items():
            for i, f in enumerate(files):
                self.model.get_item(i).update(f)
        else:
            self.model.remove_all()
            for f in files:
                self.model.append(FileItem(f))

    def _set_selected_priority(self, priority):
        item = self.selection_model.get_selected_item()
        if not item or not self.torrent_hash:
            return
        self.client.set_file_priority(self.torrent_hash, [item.index], priority)
        item.priority = priority
        item.priority_str = FileItem.PRIORITY_NAMES.get(priority, str(priority))

    def _on_rename_file(self, btn):
        item = self.selection_model.get_selected_item()
        if not item or not self.torrent_hash:
            return

        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Rename File",
            body="Enter new file name/path:"
        )
        entry = Gtk.Entry()
        entry.set_text(item.name)
        entry.set_margin_top(12)
        entry.set_margin_bottom(12)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        dialog.set_extra_child(entry)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Rename")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)

        def on_resp(d, resp):
            if resp == "save":
                new_name = entry.get_text().strip()
                if new_name and new_name != item.name:
                    self.client.rename_file(self.torrent_hash, item.name, new_name)
                    item.name = new_name
            d.destroy()

        dialog.connect("response", on_resp)
        dialog.show()
