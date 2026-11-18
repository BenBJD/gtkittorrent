import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gio, Adw
from ...models.file_item import FileItem, build_file_tree


class ContentTab(Gtk.Box):
    """Content/Files tab with tree view, file priorities, and rename capabilities."""

    def __init__(self, client):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.client = client
        self.torrent_hash = None
        self.model = Gio.ListStore(item_type=FileItem)
        self._leaves_by_index = {}

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        self.append(toolbar)

        prio_high_btn = Gtk.Button(label="High Priority")
        prio_high_btn.connect("clicked", lambda _x: self._set_selected_priority(6))
        toolbar.append(prio_high_btn)

        prio_norm_btn = Gtk.Button(label="Normal Priority")
        prio_norm_btn.connect("clicked", lambda _x: self._set_selected_priority(1))
        toolbar.append(prio_norm_btn)

        prio_none_btn = Gtk.Button(label="Do Not Download")
        prio_none_btn.connect("clicked", lambda _x: self._set_selected_priority(0))
        toolbar.append(prio_none_btn)

        rename_btn = Gtk.Button(icon_name="document-edit-symbolic", tooltip_text="Rename File")
        rename_btn.connect("clicked", self._on_rename_file)
        toolbar.append(rename_btn)

        # Scrolled ColumnView with TreeListModel
        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.append(scrolled)

        self.tree_model = Gtk.TreeListModel.new(
            self.model,
            False,
            True,
            lambda item: item.children if item.is_folder else None,
        )
        self.selection_model = Gtk.SingleSelection(model=self.tree_model)
        self.column_view = Gtk.ColumnView(model=self.selection_model)
        scrolled.set_child(self.column_view)

        self._setup_columns()

    @staticmethod
    def _unwrap_item(list_item):
        row = list_item.get_item()
        if isinstance(row, Gtk.TreeListRow):
            return row.get_item()
        return row

    def _setup_columns(self):
        # Name (with TreeExpander + folder/file icon)
        factory_name = Gtk.SignalListItemFactory()

        def setup_name(_f, item):
            expander = Gtk.TreeExpander()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_start=4, margin_end=4)
            icon = Gtk.Image()
            lbl = Gtk.Label(xalign=0, ellipsize=3)
            box.append(icon)
            box.append(lbl)
            expander.set_child(box)
            item.set_child(expander)

        def bind_name(_f, item):
            row = item.get_item()
            expander = item.get_child()
            if not row or not expander:
                return
            expander.set_list_row(row if isinstance(row, Gtk.TreeListRow) else None)
            f_item = row.get_item() if isinstance(row, Gtk.TreeListRow) else row
            box = expander.get_child()
            icon = box.get_first_child()
            lbl = icon.get_next_sibling()
            if f_item:
                icon.set_from_icon_name("folder-symbolic" if f_item.is_folder else "text-x-generic-symbolic")
                lbl.set_text(f_item.display_name or f_item.name)

        factory_name.connect("setup", setup_name)
        factory_name.connect("bind", bind_name)
        col_name = Gtk.ColumnViewColumn(title="Name", factory=factory_name)
        col_name.set_expand(True)
        self.column_view.append_column(col_name)

        # Size
        factory_size = Gtk.SignalListItemFactory()
        factory_size.connect("setup", lambda _f, item: item.set_child(Gtk.Label(xalign=1, margin_start=4, margin_end=4)))
        factory_size.connect(
            "bind",
            lambda _f, item: item.get_child().set_text(
                self._unwrap_item(item).size_str if self._unwrap_item(item) else ""
            ),
        )
        col_size = Gtk.ColumnViewColumn(title="Size", factory=factory_size)
        col_size.set_fixed_width(100)
        self.column_view.append_column(col_size)

        # Progress
        factory_prog = Gtk.SignalListItemFactory()
        factory_prog.connect("setup", lambda _f, item: item.set_child(Gtk.ProgressBar(show_text=True, margin_start=4, margin_end=4)))

        def bind_prog(_f, item):
            f_item = self._unwrap_item(item)
            bar = item.get_child()
            if f_item and bar:
                bar.set_fraction(f_item.progress)

        factory_prog.connect("bind", bind_prog)
        col_prog = Gtk.ColumnViewColumn(title="Progress", factory=factory_prog)
        col_prog.set_fixed_width(140)
        self.column_view.append_column(col_prog)

        # Priority
        factory_prio = Gtk.SignalListItemFactory()
        factory_prio.connect("setup", lambda _f, item: item.set_child(Gtk.Label(xalign=0, margin_start=4, margin_end=4)))
        factory_prio.connect(
            "bind",
            lambda _f, item: item.get_child().set_text(
                self._unwrap_item(item).priority_str if self._unwrap_item(item) else ""
            ),
        )
        col_prio = Gtk.ColumnViewColumn(title="Priority", factory=factory_prio)
        col_prio.set_fixed_width(120)
        self.column_view.append_column(col_prio)

        # Remaining
        factory_rem = Gtk.SignalListItemFactory()
        factory_rem.connect("setup", lambda _f, item: item.set_child(Gtk.Label(xalign=1, margin_start=4, margin_end=4)))
        factory_rem.connect(
            "bind",
            lambda _f, item: item.get_child().set_text(
                self._unwrap_item(item).remaining_str if self._unwrap_item(item) else ""
            ),
        )
        col_rem = Gtk.ColumnViewColumn(title="Remaining", factory=factory_rem)
        col_rem.set_fixed_width(100)
        self.column_view.append_column(col_rem)

    def _refresh_root_aggregates(self):
        for i in range(self.model.get_n_items()):
            node = self.model.get_item(i)
            if node.is_folder:
                node.refresh_folder_aggregates()

    def update(self, torrent_item):
        if not torrent_item:
            self.torrent_hash = None
            self.model.remove_all()
            self._leaves_by_index.clear()
            return

        same_torrent = (self.torrent_hash == torrent_item.hash)
        self.torrent_hash = torrent_item.hash
        files = self.client.get_torrent_contents(self.torrent_hash) if self.client else []

        if same_torrent and len(files) == len(self._leaves_by_index) and all(
            int(f.get("index", i)) in self._leaves_by_index for i, f in enumerate(files)
        ):
            for i, f in enumerate(files):
                idx = int(f.get("index", i))
                self._leaves_by_index[idx].update(f)
            self._refresh_root_aggregates()
        else:
            _, self._leaves_by_index = build_file_tree(files, self.model)

    def _set_selected_priority(self, priority):
        row = self.selection_model.get_selected_item()
        item = row.get_item() if isinstance(row, Gtk.TreeListRow) else row
        if not item or not self.torrent_hash:
            return
        leaves = item.get_descendant_leaves()
        if not leaves:
            return
        self.client.set_file_priority(self.torrent_hash, [lf.index for lf in leaves], priority)
        prio_name = FileItem.PRIORITY_NAMES.get(priority, str(priority))
        for lf in leaves:
            lf.priority = priority
            lf.priority_str = prio_name
        self._refresh_root_aggregates()

    def _on_rename_file(self, _btn):
        row = self.selection_model.get_selected_item()
        item = row.get_item() if isinstance(row, Gtk.TreeListRow) else row
        if not item or not self.torrent_hash or item.is_folder:
            return

        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Rename File",
            body="Enter new file name/path:",
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
                    item.display_name = new_name.rsplit("/", 1)[-1] if "/" in new_name else new_name
            d.destroy()

        dialog.connect("response", on_resp)
        dialog.show()
