import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio

class AddTorrentDialog(Adw.Window):
    """Add Torrent dialog for file or URL/Magnet."""
    # TODO: Add ability to change file prioroties before starting
    # And whatever else is missing.

    def __init__(self, parent, client, torrent_file=None, torrent_url=None):
        super().__init__(transient_for=parent, modal=True, title="Add Torrent")
        self.set_default_size(520, 500)
        self.client = client
        self.torrent_file = torrent_file
        self.torrent_url = torrent_url
        self.categories = list(self.client.get_categories().keys()) if self.client else []
        self.prefs = self.client.get_app_preferences() if self.client else {}
        self.default_save_path = self.prefs.get("save_path", "")

        self._build_ui()

    def _build_ui(self):
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(content_box)

        # HeaderBar
        header = Adw.HeaderBar()
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda x: self.close())
        header.pack_start(cancel_btn)

        add_btn = Gtk.Button(label="Add", css_classes=["suggested-action"])
        add_btn.connect("clicked", self._on_add_clicked)
        header.pack_end(add_btn)
        content_box.append(header)

        # Scrolled content
        scrolled = Gtk.ScrolledWindow(vexpand=True)
        content_box.append(scrolled)

        clamp = Adw.Clamp(maximum_size=600, margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        scrolled.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(box)

        # Source Group
        source_group = Adw.PreferencesGroup(title="Torrent Source")
        box.append(source_group)

        if self.torrent_file:
            self.source_entry = Adw.EntryRow(title="Torrent File")
            self.source_entry.set_text(self.torrent_file)
            self.source_entry.set_editable(False)
            source_group.add(self.source_entry)
        else:
            self.source_entry = Adw.EntryRow(title="URL or Magnet")
            self.source_entry.set_text(self.torrent_url or "")
            source_group.add(self.source_entry)

        self.rename_entry = Adw.EntryRow(title="Rename (optional)")
        source_group.add(self.rename_entry)

        # Destination Group
        dest_group = Adw.PreferencesGroup(title="Destination &amp; Organization")
        box.append(dest_group)

        # Save path with browse button
        self.save_path_row = Adw.ActionRow(title="Save to")
        self.save_path_entry = Gtk.Entry(hexpand=True, valign=Gtk.Align.CENTER)
        self.save_path_entry.set_text(self.default_save_path)
        browse_btn = Gtk.Button(icon_name="folder-open-symbolic", valign=Gtk.Align.CENTER)
        browse_btn.connect("clicked", self._on_browse_save_path)
        
        path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        path_box.append(self.save_path_entry)
        path_box.append(browse_btn)
        self.save_path_row.add_suffix(path_box)
        dest_group.add(self.save_path_row)

        # Category DropDown
        self.cat_row = Adw.ComboRow(title="Category")
        cat_model = Gtk.StringList.new(["None"] + self.categories)
        self.cat_row.set_model(cat_model)
        dest_group.add(self.cat_row)

        # Tags Entry
        self.tags_entry = Adw.EntryRow(title="Tags (comma-separated)")
        dest_group.add(self.tags_entry)

        # Options Group
        opts_group = Adw.PreferencesGroup(title="Download Options")
        box.append(opts_group)

        self.start_row = Adw.ActionRow(title="Start torrent immediately")
        self.start_switch = Gtk.Switch(active=True, valign=Gtk.Align.CENTER)
        self.start_row.add_suffix(self.start_switch)
        opts_group.add(self.start_row)

        self.seq_row = Adw.ActionRow(title="Download in sequential order")
        self.seq_switch = Gtk.Switch(active=False, valign=Gtk.Align.CENTER)
        self.seq_row.add_suffix(self.seq_switch)
        opts_group.add(self.seq_row)

        self.fl_row = Adw.ActionRow(title="Download first and last pieces first")
        self.fl_switch = Gtk.Switch(active=False, valign=Gtk.Align.CENTER)
        self.fl_row.add_suffix(self.fl_switch)
        opts_group.add(self.fl_row)

        self.skip_check_row = Adw.ActionRow(title="Skip hash checking")
        self.skip_check_switch = Gtk.Switch(active=False, valign=Gtk.Align.CENTER)
        self.skip_check_row.add_suffix(self.skip_check_switch)
        opts_group.add(self.skip_check_row)

    def _on_browse_save_path(self, btn):
        dialog = Gtk.FileChooserNative(
            title="Select Download Directory",
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            accept_label="_Select",
            cancel_label="_Cancel"
        )
        def on_resp(d, resp):
            if resp == Gtk.ResponseType.ACCEPT:
                f = d.get_file()
                if f:
                    self.save_path_entry.set_text(f.get_path())
            d.destroy()
        dialog.connect("response", on_resp)
        dialog.show()

    def _on_add_clicked(self, btn):
        save_path = self.save_path_entry.get_text().strip() or None
        rename = self.rename_entry.get_text().strip() or None

        cat_idx = self.cat_row.get_selected()
        category = None
        if cat_idx > 0 and (cat_idx - 1) < len(self.categories):
            category = self.categories[cat_idx - 1]

        tags_str = self.tags_entry.get_text().strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else None

        is_paused = not self.start_switch.get_active()
        is_seq = self.seq_switch.get_active()
        is_fl = self.fl_switch.get_active()
        skip_chk = self.skip_check_switch.get_active()

        if self.torrent_file:
            self.client.add_torrent(
                torrent_files=self.torrent_file,
                savepath=save_path,
                category=category,
                tags=tags,
                is_paused=is_paused,
                is_sequential=is_seq,
                is_first_last_piece_priority=is_fl,
                skip_checking=skip_chk,
                rename=rename
            )
        else:
            url = self.source_entry.get_text().strip()
            if url:
                self.client.add_torrent(
                    urls=url,
                    savepath=save_path,
                    category=category,
                    tags=tags,
                    is_paused=is_paused,
                    is_sequential=is_seq,
                    is_first_last_piece_priority=is_fl,
                    skip_checking=skip_chk,
                    rename=rename
                )

        self.close()
