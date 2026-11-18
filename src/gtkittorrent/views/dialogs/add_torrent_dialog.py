import base64
import os
import threading
import time
import urllib.parse
import urllib.request
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from ...utils.formatters import format_bytes


def _bdecode(data, idx=0):
    """Minimal bencode decoder returning (value, next_index)."""
    if idx >= len(data):
        raise ValueError("Unexpected end of bencode data")
    ch = data[idx:idx + 1]
    if ch == b"i":
        end = data.index(b"e", idx + 1)
        return int(data[idx + 1:end]), end + 1
    if ch == b"l":
        items = []
        idx += 1
        while data[idx:idx + 1] != b"e":
            val, idx = _bdecode(data, idx)
            items.append(val)
        return items, idx + 1
    if ch == b"d":
        mapping = {}
        idx += 1
        while data[idx:idx + 1] != b"e":
            key, idx = _bdecode(data, idx)
            val, idx = _bdecode(data, idx)
            mapping[key] = val
        return mapping, idx + 1
    if ch.isdigit():
        colon = data.index(b":", idx)
        length = int(data[idx:colon])
        start = colon + 1
        return data[start:start + length], start + length
    raise ValueError(f"Invalid bencode token at {idx}")


def _parse_torrent_bytes(raw, fallback_name="torrent"):
    """Parse raw bencoded .torrent bytes and return list of (relative_path, size_bytes)."""
    try:
        meta, _ = _bdecode(raw)
        if not isinstance(meta, dict):
            return []
        info = meta.get(b"info")
        if not isinstance(info, dict):
            return []
        if b"files" in info and isinstance(info[b"files"], list):
            root = info.get(b"name", b"").decode("utf-8", errors="replace")
            result = []
            for entry in info[b"files"]:
                if not isinstance(entry, dict):
                    continue
                size = int(entry.get(b"length", 0))
                parts = [p.decode("utf-8", errors="replace") for p in entry.get(b"path", [])]
                rel = os.path.join(root, *parts) if root else os.path.join(*parts)
                result.append((rel, size))
            return result
        if b"length" in info:
            name = info.get(b"name", fallback_name.encode("utf-8")).decode("utf-8", errors="replace")
            return [(name, int(info[b"length"]))]
    except Exception:
        return []
    return []


def _parse_torrent_files(filepath):
    """Return list of (relative_path, size_bytes) from a .torrent file, or [] on error."""
    if not filepath or not os.path.isfile(filepath):
        return []
    try:
        with open(filepath, "rb") as f:
            raw = f.read()
        return _parse_torrent_bytes(raw, fallback_name=os.path.basename(filepath))
    except Exception:
        return []


def _extract_magnet_info(magnet_url):
    """Return (infohash_hex, display_name) from a magnet URI."""
    try:
        parsed = urllib.parse.urlparse(magnet_url)
        qs = urllib.parse.parse_qs(parsed.query)
        dn = qs.get("dn", [""])[0]
        infohash = ""
        for xt in qs.get("xt", []):
            if xt.lower().startswith("urn:btih:"):
                raw_h = xt[9:].strip()
                if len(raw_h) == 40:
                    infohash = raw_h.lower()
                elif len(raw_h) == 32:
                    infohash = base64.b32decode(raw_h.upper()).hex()
                break
        return infohash, dn
    except Exception:
        return "", ""


class AddTorrentUrlDialog(Adw.Window):
    """Dialog for entering a magnet link or torrent URL before configuring download options."""

    def __init__(self, parent, client):
        super().__init__(transient_for=parent, modal=True, title="Add Torrent Link")
        self.parent_win = parent
        self.client = client
        self.set_default_size(500, 210)
        self._build_ui()

    def _build_ui(self):
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(content_box)

        header = Adw.HeaderBar()
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda _b: self.close())
        header.pack_start(cancel_btn)

        self.continue_btn = Gtk.Button(label="Continue", css_classes=["suggested-action"])
        self.continue_btn.connect("clicked", self._on_continue_clicked)
        header.pack_end(self.continue_btn)
        content_box.append(header)

        clamp = Adw.Clamp(maximum_size=520, margin_top=16, margin_bottom=16, margin_start=16, margin_end=16)
        content_box.append(clamp)

        group = Adw.PreferencesGroup(
            title="Torrent Link",
            description="Enter a magnet link or HTTP/HTTPS URL to a .torrent file.",
        )
        clamp.set_child(group)

        self.url_entry = Adw.EntryRow(title="Magnet link or URL")
        self.url_entry.connect("entry-activated", self._on_continue_clicked)
        group.add(self.url_entry)

        self.error_lbl = Gtk.Label(
            label="",
            xalign=0,
            css_classes=["error"],
            margin_top=6,
            visible=False,
        )
        group.add(self.error_lbl)

    def _on_continue_clicked(self, *_args):
        url = self.url_entry.get_text().strip().strip("'\"")
        if not url:
            self.error_lbl.set_text("Please enter a magnet link or URL.")
            self.error_lbl.set_visible(True)
            return
        if not url.lower().startswith(("magnet:", "http://", "https://")):
            self.error_lbl.set_text("Link must start with magnet:, http://, or https://")
            self.error_lbl.set_visible(True)
            return
        self.close()
        dlg = AddTorrentDialog(self.parent_win, self.client, torrent_url=url)
        dlg.present()


class AddTorrentDialog(Adw.Window):
    """Add Torrent options dialog for a .torrent file or URL/Magnet."""

    CONTENT_LAYOUTS = ["Original", "Subfolder", "NoSubfolder"]
    FILE_PRIORITIES = [0, 1, 6, 7]
    FILE_PRIORITY_LABELS = ["Do not download", "Normal", "High", "Maximum"]

    def __init__(self, parent, client, torrent_file=None, torrent_url=None):
        super().__init__(transient_for=parent, modal=True, title="Add Torrent")
        self.parent_win = parent
        self.client = client
        self.torrent_file = torrent_file
        self.torrent_url = torrent_url

        raw_cats = self.client.get_categories() if self.client else {}
        self.categories_data = raw_cats if isinstance(raw_cats, dict) else {}
        self.categories = list(self.categories_data.keys())

        raw_tags = self.client.get_tags() if self.client else []
        self.available_tags = list(raw_tags) if isinstance(raw_tags, (list, tuple)) else []

        raw_prefs = self.client.get_app_preferences() if self.client else {}
        self.prefs = raw_prefs if isinstance(raw_prefs, dict) else {}
        self.default_save_path = self.prefs.get("save_path", "") or ""
        self.manual_save_path = self.default_save_path
        self._was_auto = False

        self.torrent_files_info = _parse_torrent_files(self.torrent_file) if self.torrent_file else []
        self._file_rows = []
        self._closed = False
        self._submitted = False
        self._temp_added_hash = None
        self._metadata_ready = bool(self.torrent_files_info)

        self.set_default_size(960, 620)
        self.connect("close-request", self._on_close_request)

        self._build_ui()

        if self.torrent_url and not self.torrent_files_info:
            self._start_url_metadata_fetch()

    def _get_settings(self):
        return getattr(self.parent_win, "settings", None) if self.parent_win else None

    def _switch_row(self, group, title, active=False, subtitle=None):
        row = Adw.ActionRow(title=title)
        if subtitle:
            row.set_subtitle(subtitle)
        switch = Gtk.Switch(active=bool(active), valign=Gtk.Align.CENTER)
        row.add_suffix(switch)
        row.set_activatable_widget(switch)
        group.add(row)
        return row, switch

    def _build_ui(self):
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(content_box)

        # HeaderBar
        header = Adw.HeaderBar()
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda _b: self.close())
        header.pack_start(cancel_btn)

        add_btn = Gtk.Button(label="Add", css_classes=["suggested-action"])
        add_btn.connect("clicked", self._on_add_clicked)
        header.pack_end(add_btn)
        content_box.append(header)

        main_area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, vexpand=True)
        content_box.append(main_area)

        # Left pane: options
        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        main_area.append(scrolled)

        clamp = Adw.Clamp(maximum_size=600, margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        scrolled.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(box)

        # Source summary (read-only)
        source_group = Adw.PreferencesGroup(title="Torrent")
        box.append(source_group)

        if self.torrent_file:
            row_title = "File"
            source_text = os.path.basename(self.torrent_file)
        else:
            _, dn = _extract_magnet_info(self.torrent_url or "")
            row_title = dn if dn else "Link"
            source_text = self.torrent_url or ""

        self.source_row = Adw.ActionRow(
            title=GLib.markup_escape_text(row_title),
            subtitle=GLib.markup_escape_text(source_text),
            subtitle_lines=2,
        )
        source_group.add(self.source_row)

        # Save at Group
        dest_group = Adw.PreferencesGroup(title="Save at")
        box.append(dest_group)

        self.tmm_row = Adw.ComboRow(
            title="Torrent Management Mode",
            model=Gtk.StringList.new(["Manual", "Automatic"]),
        )
        auto_tmm = bool(self.prefs.get("auto_tmm_enabled", False))
        self.tmm_row.set_selected(1 if auto_tmm else 0)
        dest_group.add(self.tmm_row)

        self.save_path_row = Adw.ActionRow(title="Save files to location")
        self.save_path_entry = Gtk.Entry(hexpand=True, valign=Gtk.Align.CENTER)
        self.save_path_entry.set_text(self.default_save_path)
        self.save_path_browse_btn = Gtk.Button(icon_name="folder-open-symbolic", valign=Gtk.Align.CENTER)
        self.save_path_browse_btn.connect("clicked", lambda _b: self._on_browse_dir(self.save_path_entry, "Select Download Directory"))
        path_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        path_box.append(self.save_path_entry)
        path_box.append(self.save_path_browse_btn)
        self.save_path_row.add_suffix(path_box)
        dest_group.add(self.save_path_row)

        temp_enabled = bool(self.prefs.get("temp_path_enabled", False))
        self.incomplete_switch_row, self.incomplete_switch = self._switch_row(
            dest_group,
            "Use another path for incomplete torrent",
            temp_enabled,
        )

        self.incomplete_path_row = Adw.ActionRow(title="Save path")
        self.incomplete_path_entry = Gtk.Entry(hexpand=True, valign=Gtk.Align.CENTER)
        self.incomplete_path_entry.set_text(self.prefs.get("temp_path", "") or "")
        self.incomplete_browse_btn = Gtk.Button(icon_name="folder-open-symbolic", valign=Gtk.Align.CENTER)
        self.incomplete_browse_btn.connect("clicked", lambda _b: self._on_browse_dir(self.incomplete_path_entry, "Select Incomplete Directory"))
        inc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        inc_box.append(self.incomplete_path_entry)
        inc_box.append(self.incomplete_browse_btn)
        self.incomplete_path_row.add_suffix(inc_box)
        dest_group.add(self.incomplete_path_row)

        # Torrent Settings Group
        opts_group = Adw.PreferencesGroup(title="Torrent settings")
        box.append(opts_group)

        self.rename_entry = Adw.EntryRow(title="Rename torrent")
        opts_group.add(self.rename_entry)

        self.cat_row = Adw.ComboRow(
            title="Category",
            model=Gtk.StringList.new(["None"] + self.categories),
        )
        settings = self._get_settings()
        default_cat = settings.get("default_add_category", "") if settings else ""
        if isinstance(default_cat, str) and default_cat in self.categories:
            self.cat_row.set_selected(self.categories.index(default_cat) + 1)
        opts_group.add(self.cat_row)

        _, self.default_cat_switch = self._switch_row(
            opts_group,
            "Set as default category",
            bool(isinstance(default_cat, str) and default_cat and default_cat in self.categories),
        )

        self.tags_entry = Adw.EntryRow(title="Tags (comma-separated)")
        if self.available_tags:
            self.tags_menu_btn = Gtk.MenuButton(
                icon_name="pan-down-symbolic",
                valign=Gtk.Align.CENTER,
                css_classes=["flat"],
                tooltip_text="Select existing tags",
            )
            self.tags_menu_btn.set_popover(self._build_tags_popover())
            self.tags_entry.add_suffix(self.tags_menu_btn)
        opts_group.add(self.tags_entry)

        stopped = bool(self.prefs.get("add_stopped_enabled", self.prefs.get("start_paused_enabled", False)))
        self.start_row, self.start_switch = self._switch_row(opts_group, "Start torrent", not stopped)
        _, self.top_queue_switch = self._switch_row(
            opts_group, "Add to top of queue", self.prefs.get("add_to_top_of_queue", False)
        )
        self.seq_row, self.seq_switch = self._switch_row(opts_group, "Download in sequential order", False)
        self.fl_row, self.fl_switch = self._switch_row(opts_group, "Download first and last pieces first", False)
        self.skip_check_row, self.skip_check_switch = self._switch_row(opts_group, "Skip hash checking", False)

        self.content_layout_row = Adw.ComboRow(
            title="Content layout",
            model=Gtk.StringList.new(["Original", "Create subfolder", "Don't create subfolder"]),
        )
        layout = self.prefs.get("torrent_content_layout", "Original")
        self.content_layout_row.set_selected(
            self.CONTENT_LAYOUTS.index(layout) if layout in self.CONTENT_LAYOUTS else 0
        )
        opts_group.add(self.content_layout_row)

        self.dl_limit_row = Adw.SpinRow(
            title="Limit download rate",
            subtitle="KiB/s (0 = unlimited)",
            adjustment=Gtk.Adjustment(lower=0, upper=1048576, step_increment=10, page_increment=100),
        )
        opts_group.add(self.dl_limit_row)

        self.up_limit_row = Adw.SpinRow(
            title="Limit upload rate",
            subtitle="KiB/s (0 = unlimited)",
            adjustment=Gtk.Adjustment(lower=0, upper=1048576, step_increment=10, page_increment=100),
        )
        opts_group.add(self.up_limit_row)

        # Wire TMM, category, and incomplete path interactions
        self.tmm_row.connect("notify::selected", self._sync_tmm_state)
        self.cat_row.connect("notify::selected", self._on_category_changed)
        self.incomplete_switch.connect("notify::active", self._sync_tmm_state)
        self.save_path_entry.connect("changed", self._on_save_path_edited)
        self._sync_tmm_state()

        # Right pane: Files list (always visible; shows spinner while fetching URL/magnet metadata)
        main_area.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))
        main_area.append(self._build_files_pane())

    def _build_tags_popover(self):
        pop = Gtk.Popover()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        pop.set_child(box)
        self._tag_checks = {}
        for tag in self.available_tags:
            cb = Gtk.CheckButton(label=tag)
            cb.connect("toggled", self._on_tag_check_toggled)
            self._tag_checks[tag] = cb
            box.append(cb)
        return pop

    def _on_tag_check_toggled(self, _cb):
        current = [t.strip() for t in self.tags_entry.get_text().split(",") if t.strip()]
        checked = [tag for tag, cb in self._tag_checks.items() if cb.get_active()]
        # Preserve any manually typed tags not in available_tags
        custom = [t for t in current if t not in self._tag_checks]
        self.tags_entry.set_text(", ".join(checked + custom))

    def _build_files_pane(self):
        pane = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        pane.set_size_request(400, -1)

        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.files_select_all_cb = Gtk.CheckButton(active=True, tooltip_text="Select / deselect all files")
        self.files_select_all_cb.connect("toggled", self._on_files_select_all_toggled)
        header_box.append(self.files_select_all_cb)
        header_box.append(Gtk.Label(label="Files", css_classes=["heading"], xalign=0, hexpand=True))
        total_bytes = sum(sz for _, sz in self.torrent_files_info)
        self.files_total_lbl = Gtk.Label(label=format_bytes(total_bytes), css_classes=["dim-label"])
        header_box.append(self.files_total_lbl)
        pane.append(header_box)

        self.files_filter_entry = Gtk.SearchEntry(placeholder_text="Filter files...")
        self.files_filter_entry.connect("search-changed", self._on_files_filter_changed)
        pane.append(self.files_filter_entry)

        self.files_status_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            halign=Gtk.Align.CENTER,
            valign=Gtk.Align.CENTER,
            vexpand=True,
        )
        self.files_spinner = Gtk.Spinner()
        self.files_status_lbl = Gtk.Label(label="", css_classes=["dim-label"], wrap=True)
        self.files_status_box.append(self.files_spinner)
        self.files_status_box.append(self.files_status_lbl)

        self.files_scroller = Gtk.ScrolledWindow(vexpand=True, css_classes=["card"])
        self.files_listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE)
        self.files_scroller.set_child(self.files_listbox)

        self.files_stack = Gtk.Stack(vexpand=True)
        self.files_stack.add_named(self.files_scroller, "list")
        self.files_stack.add_named(self.files_status_box, "status")
        pane.append(self.files_stack)

        if self.torrent_files_info:
            self._populate_files_list(self.torrent_files_info)
            self.files_stack.set_visible_child_name("list")
        else:
            self.files_spinner.start()
            self.files_status_lbl.set_text("Fetching torrent metadata...")
            self.files_stack.set_visible_child_name("status")

        return pane

    def _populate_files_list(self, files_info):
        while True:
            child = self.files_listbox.get_first_child()
            if child is None:
                break
            self.files_listbox.remove(child)
        self._file_rows = []
        self.torrent_files_info = list(files_info)
        prio_model = Gtk.StringList.new(self.FILE_PRIORITY_LABELS)
        for rel_path, size in self.torrent_files_info:
            row = Gtk.ListBoxRow()
            row_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, margin_top=6, margin_bottom=6, margin_start=8, margin_end=8)
            cb = Gtk.CheckButton(active=True)
            lbl = Gtk.Label(label=rel_path, xalign=0, hexpand=True, ellipsize=3)  # PANGO_ELLIPSIZE_END
            lbl.set_tooltip_text(rel_path)
            sz_lbl = Gtk.Label(label=format_bytes(size), css_classes=["dim-label"])
            prio_dd = Gtk.DropDown(model=prio_model, selected=1, valign=Gtk.Align.CENTER)

            syncing = [False]

            def on_cb_toggled(btn, dd=prio_dd, guard=syncing):
                if guard[0]:
                    return
                guard[0] = True
                if not btn.get_active():
                    dd.set_selected(0)
                elif dd.get_selected() == 0:
                    dd.set_selected(1)
                guard[0] = False
                self._update_selected_files_size()

            def on_prio_changed(dd, _pspec, btn=cb, guard=syncing):
                if guard[0]:
                    return
                guard[0] = True
                btn.set_active(dd.get_selected() != 0)
                guard[0] = False
                self._update_selected_files_size()

            cb.connect("toggled", on_cb_toggled)
            prio_dd.connect("notify::selected", on_prio_changed)

            row_box.append(cb)
            row_box.append(lbl)
            row_box.append(sz_lbl)
            row_box.append(prio_dd)
            row.set_child(row_box)
            self.files_listbox.append(row)
            self._file_rows.append((row, cb, prio_dd, rel_path, size))

        self._update_selected_files_size()
        self._update_save_path_subtitle()

    def _start_url_metadata_fetch(self):
        url = (self.torrent_url or "").strip()
        if not url:
            self._on_metadata_fetch_failed("No URL provided.")
            return

        if url.startswith(("http://", "https://")):
            def http_worker():
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "gtkittorrent"})
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        raw = resp.read()
                    files = _parse_torrent_bytes(raw)
                    if not self._closed:
                        if files:
                            GLib.idle_add(self._on_metadata_files_loaded, files)
                        else:
                            GLib.idle_add(self._on_metadata_fetch_failed, "Could not parse torrent file list.")
                except Exception as e:
                    if not self._closed:
                        GLib.idle_add(self._on_metadata_fetch_failed, f"Failed to fetch metadata: {e}")

            threading.Thread(target=http_worker, daemon=True).start()
            return

        if url.startswith("magnet:") and self.client:
            infohash, _ = _extract_magnet_info(url)
            if not infohash:
                self._on_metadata_fetch_failed("File list unavailable before adding.")
                return

            def magnet_worker():
                try:
                    existing = self.client.get_torrents() or []
                    already_exists = any(
                        (t.get("hash", "") if isinstance(t, dict) else getattr(t, "hash", "")).lower() == infohash
                        for t in existing
                    )
                    if not already_exists:
                        ok = self.client.add_torrent(
                            urls=url,
                            is_paused=False,
                            stop_condition="MetadataReceived",
                        )
                        if not ok:
                            if not self._closed:
                                GLib.idle_add(self._on_metadata_fetch_failed, "Waiting for metadata unavailable.")
                            return
                        self._temp_added_hash = infohash

                    for _ in range(120):
                        if self._closed or self._submitted:
                            return
                        contents = self.client.get_torrent_contents(infohash) or []
                        if contents:
                            files = [
                                (
                                    c.get("name", "") if isinstance(c, dict) else getattr(c, "name", ""),
                                    int(c.get("size", 0) if isinstance(c, dict) else getattr(c, "size", 0)),
                                )
                                for c in contents
                            ]
                            if not self._closed:
                                GLib.idle_add(self._on_metadata_files_loaded, files)
                            return
                        time.sleep(0.5)

                    if not self._closed:
                        GLib.idle_add(self._on_metadata_fetch_failed, "Timed out waiting for peer metadata.")
                except Exception as e:
                    if not self._closed:
                        GLib.idle_add(self._on_metadata_fetch_failed, f"Metadata fetch failed: {e}")

            threading.Thread(target=magnet_worker, daemon=True).start()
        else:
            self._on_metadata_fetch_failed("File list unavailable before adding.")

    def _on_metadata_files_loaded(self, files):
        if self._closed:
            return
        self.files_spinner.stop()
        self._metadata_ready = True
        self._populate_files_list(files)
        self.files_stack.set_visible_child_name("list")

    def _on_metadata_fetch_failed(self, message):
        if self._closed:
            return
        self.files_spinner.stop()
        self.files_spinner.set_visible(False)
        self.files_status_lbl.set_text(message)
        self.files_stack.set_visible_child_name("status")

    def _on_close_request(self, *_args):
        self._closed = True
        if not self._submitted and self._temp_added_hash and self.client:
            h = self._temp_added_hash
            self._temp_added_hash = None
            threading.Thread(
                target=lambda: self.client.delete_torrent([h], delete_files=True),
                daemon=True,
            ).start()
        return False

    def _on_files_select_all_toggled(self, cb):
        active = cb.get_active()
        for _row, file_cb, _dd, _path, _sz in self._file_rows:
            file_cb.set_active(active)

    def _on_files_filter_changed(self, entry):
        query = entry.get_text().strip().lower()
        for row, _cb, _dd, rel_path, _sz in self._file_rows:
            row.set_visible(not query or query in rel_path.lower())

    def _update_selected_files_size(self, *_args):
        total = sum(sz for _row, cb, _dd, _path, sz in self._file_rows if cb.get_active())
        self.files_total_lbl.set_text(format_bytes(total))

    def _get_selected_category(self):
        idx = self.cat_row.get_selected()
        if idx > 0 and (idx - 1) < len(self.categories):
            return self.categories[idx - 1]
        return None

    def _get_category_save_path(self, category_name):
        if not category_name:
            return self.default_save_path
        cat_info = self.categories_data.get(category_name) or {}
        cat_path = cat_info.get("savePath", "") if isinstance(cat_info, dict) else getattr(cat_info, "savePath", "")
        if cat_path:
            return cat_path
        if self.default_save_path:
            return os.path.join(self.default_save_path, category_name)
        return category_name

    def _on_save_path_edited(self, entry):
        if self.tmm_row.get_selected() == 0:
            self.manual_save_path = entry.get_text()

    def _on_category_changed(self, *_args):
        if self.tmm_row.get_selected() == 1:
            self.save_path_entry.set_text(self._get_category_save_path(self._get_selected_category()))
            self._update_save_path_subtitle()

    def _sync_tmm_state(self, *_args):
        is_auto = self.tmm_row.get_selected() == 1
        if is_auto and not self._was_auto:
            self.manual_save_path = self.save_path_entry.get_text()

        self.save_path_row.set_sensitive(not is_auto)
        self.incomplete_switch_row.set_sensitive(not is_auto)
        self.incomplete_path_row.set_sensitive((not is_auto) and self.incomplete_switch.get_active())

        if is_auto:
            self.save_path_entry.set_text(self._get_category_save_path(self._get_selected_category()))
        elif self._was_auto:
            self.save_path_entry.set_text(self.manual_save_path)

        self._was_auto = is_auto
        self._update_save_path_subtitle()

    def _update_save_path_subtitle(self):
        parts = []
        if self.torrent_files_info:
            total = sum(sz for _, sz in self.torrent_files_info)
            parts.append(f"{format_bytes(total)} needed")
        path = self.save_path_entry.get_text().strip()
        if self.client and path and hasattr(self.client, "get_free_space"):
            free = self.client.get_free_space(path)
            if isinstance(free, (int, float)) and free >= 0:
                parts.append(f"{format_bytes(free)} free")
        self.save_path_row.set_subtitle(" · ".join(parts))

    def _on_browse_dir(self, target_entry, title):
        dialog = Gtk.FileChooserNative(
            title=title,
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            accept_label="_Select",
            cancel_label="_Cancel",
        )
        def on_resp(d, resp):
            if resp == Gtk.ResponseType.ACCEPT:
                f = d.get_file()
                if f:
                    target_entry.set_text(f.get_path())
                    self._update_save_path_subtitle()
            d.destroy()
        dialog.connect("response", on_resp)
        dialog.show()

    def _on_add_clicked(self, _btn):
        is_auto = self.tmm_row.get_selected() == 1
        save_path = None if is_auto else (self.save_path_entry.get_text().strip() or None)
        use_dl_path = None if is_auto else self.incomplete_switch.get_active()
        dl_path = (
            (self.incomplete_path_entry.get_text().strip() or None)
            if (not is_auto and use_dl_path)
            else None
        )

        rename = self.rename_entry.get_text().strip() or None
        category = self._get_selected_category()

        settings = self._get_settings()
        if settings:
            if self.default_cat_switch.get_active() and category:
                settings.set("default_add_category", category)
            elif not self.default_cat_switch.get_active():
                settings.set("default_add_category", "")

        tags_str = self.tags_entry.get_text().strip()
        tags = [t.strip() for t in tags_str.split(",") if t.strip()] if tags_str else None

        is_paused = not self.start_switch.get_active()
        add_top = self.top_queue_switch.get_active()
        is_seq = self.seq_switch.get_active()
        is_fl = self.fl_switch.get_active()
        skip_chk = self.skip_check_switch.get_active()
        content_layout = self.CONTENT_LAYOUTS[self.content_layout_row.get_selected()]

        dl_kib = int(self.dl_limit_row.get_value())
        up_kib = int(self.up_limit_row.get_value())
        dl_limit = dl_kib * 1024 if dl_kib > 0 else None
        up_limit = up_kib * 1024 if up_kib > 0 else None

        file_priorities = None
        if self.torrent_files_info and hasattr(self, "_file_rows"):
            prios = [
                self.FILE_PRIORITIES[dd.get_selected()]
                for _r, _cb, dd, _p, _s in self._file_rows
            ]
            if any(p != 1 for p in prios):
                file_priorities = prios

        common_kwargs = dict(
            savepath=save_path,
            category=category,
            tags=tags,
            is_paused=is_paused,
            is_sequential=is_seq,
            is_first_last_piece_priority=is_fl,
            skip_checking=skip_chk,
            rename=rename,
            use_auto_torrent_management=is_auto,
            use_download_path=use_dl_path,
            download_path=dl_path,
            add_to_top_of_queue=add_top,
            content_layout=content_layout,
            download_limit=dl_limit,
            upload_limit=up_limit,
            file_priorities=file_priorities,
        )

        self._submitted = True
        if self._temp_added_hash and self.client:
            h = self._temp_added_hash
            if hasattr(self.client, "set_auto_management"):
                self.client.set_auto_management([h], is_auto)
            if not is_auto and save_path:
                self.client.set_location([h], save_path)
            if category:
                self.client.set_category([h], category)
            if tags:
                self.client.add_tags([h], tags)
            if rename:
                self.client.rename_torrent(h, rename)
            if dl_limit:
                self.client.set_download_limit([h], dl_limit)
            if up_limit:
                self.client.set_upload_limit([h], up_limit)
            if is_seq:
                self.client.toggle_sequential_download([h])
            if is_fl:
                self.client.toggle_first_last_piece_priority([h])
            if add_top:
                self.client.top_priority([h])
            if file_priorities is not None:
                by_prio = {}
                for idx, prio in enumerate(file_priorities):
                    by_prio.setdefault(prio, []).append(idx)
                for prio, ids in by_prio.items():
                    if prio != 1:
                        self.client.set_file_priority(h, ids, prio)
            if is_paused:
                self.client.pause_torrent([h])
            else:
                self.client.resume_torrent([h])
        elif self.torrent_file:
            self.client.add_torrent(torrent_files=self.torrent_file, **common_kwargs)
        elif self.torrent_url:
            url = self.torrent_url.strip()
            if url:
                self.client.add_torrent(urls=url, **common_kwargs)

        self.close()
