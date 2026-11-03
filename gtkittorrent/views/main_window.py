import gi
import os
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, Gio, GLib, Adw, Pango

from ..models.torrent import TorrentItem
from .sidebar import Sidebar
from .torrent_table import TorrentTable
from .details.details_notebook import DetailsNotebook
from .status_bar import StatusBar
from .dialogs.add_torrent_dialog import AddTorrentDialog
from .dialogs.preferences_dialog import PreferencesDialog
from .dialogs.instance_dialog import InstanceDialog
from .welcome_window import WelcomeWindow

class MainWindow(Adw.Window):
    """Main application window providing complete qBittorrent desktop functionality."""

    def __init__(self, app, client):
        super().__init__(application=app, title="GTKittorrent")
        self.app = app
        self.client = client
        self.sync_rid = 0
        self.items_by_hash = {}

        self.set_default_size(1024, 768)

        # Toast Overlay
        self.toast_overlay = Adw.ToastOverlay()
        self.set_content(self.toast_overlay)

        # Main Layout Box
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.toast_overlay.set_child(self.main_box)

        # 1. HeaderBar
        self._setup_headerbar()
        self._update_instance_ui()

        # 2. Main Paned Layout
        self.v_paned = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        self.v_paned.set_vexpand(True)
        self.main_box.append(self.v_paned)

        # Top Horizontal Paned: Sidebar + TorrentTable
        self.h_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.v_paned.set_start_child(self.h_paned)

        # Sidebar
        self.sidebar = Sidebar(self.client)
        self.sidebar.connect("filter-changed", self._on_sidebar_filter_changed)
        self.sidebar.connect("priority-clicked", lambda s, action: self._on_priority_clicked(action))
        self.h_paned.set_start_child(self.sidebar)

        # Backwards compatibility attributes for priority buttons
        self.top_prio_btn = self.sidebar.top_prio_btn
        self.up_prio_btn = self.sidebar.up_prio_btn
        self.down_prio_btn = self.sidebar.down_prio_btn
        self.bottom_prio_btn = self.sidebar.bottom_prio_btn

        # Torrent Table
        self.torrent_table = TorrentTable(self.client, settings=getattr(self.app, "settings", None))
        self.torrent_table.connect("selection-changed", self._on_selection_changed)
        self.torrent_table.connect("torrent-activated", self._on_torrent_activated)
        self.torrent_table.connect("refresh-requested", lambda t: self.refresh_torrents())
        self.h_paned.set_end_child(self.torrent_table)

        # Bottom Details Notebook
        self.details_notebook = DetailsNotebook(self.client)
        self.v_paned.set_end_child(self.details_notebook)
        self.v_paned.set_position(460)
        self.h_paned.set_position(220)

        # 3. Status Bar
        self.status_bar = StatusBar(self.client)
        self.main_box.append(self.status_bar)

        # Backwards compatibility accessor for model
        self.model = self.torrent_table.raw_store
        self.selection_model = self.torrent_table.selection_model
        self.details_panel = self.details_notebook

        # Refresh Timer
        self.refresh_torrents()
        GLib.timeout_add_seconds(2, self.refresh_torrents)

    def _setup_headerbar(self):
        self.header = Adw.HeaderBar()
        self.header.set_centering_policy(Adw.CenteringPolicy.LOOSE)
        self.title_widget = Adw.WindowTitle(title="GTKittorrent")
        self.header.set_title_widget(self.title_widget)
        self.main_box.append(self.header)

        # Toggle Sidebar button
        self.toggle_sidebar_btn = Gtk.Button(icon_name="sidebar-show-symbolic", tooltip_text="Toggle Sidebar")
        self.toggle_sidebar_btn.connect("clicked", self._on_toggle_sidebar)
        self.header.pack_start(self.toggle_sidebar_btn)

        # Instance Chooser MenuButton
        self.instance_btn = Gtk.MenuButton(tooltip_text="Switch qBittorrent Instance")
        self.instance_btn.add_css_class("flat")
        self.instance_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.instance_icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
        self.instance_label = Gtk.Label(label="Instance")
        self.instance_label.set_ellipsize(Pango.EllipsizeMode.END)
        self.instance_label.set_max_width_chars(18)
        self.instance_arrow = Gtk.Image.new_from_icon_name("pan-down-symbolic")

        self.instance_btn_box.append(self.instance_icon)
        self.instance_btn_box.append(self.instance_label)
        self.instance_btn_box.append(self.instance_arrow)
        self.instance_btn.set_child(self.instance_btn_box)

        self.instance_popover = Gtk.Popover()
        self.instance_popover.connect("notify::visible", lambda p, pspec: self._on_popover_visible(p))
        self.instance_btn.set_popover(self.instance_popover)
        self.header.pack_start(self.instance_btn)

        self.header.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # Add File Button
        self.add_btn = Gtk.Button(icon_name="list-add-symbolic", tooltip_text="Add Torrent File")
        self.add_btn.connect("clicked", self._on_add_file_clicked)
        self.header.pack_start(self.add_btn)

        # Add URL Button
        self.add_url_btn = Gtk.Button(icon_name="insert-link-symbolic", tooltip_text="Add Torrent Link / Magnet")
        self.add_url_btn.connect("clicked", self._on_add_url_clicked)
        self.header.pack_start(self.add_url_btn)

        self.header.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # Pause / Resume / Delete buttons
        self.pause_btn = Gtk.Button(icon_name="media-playback-pause-symbolic", tooltip_text="Pause Selected")
        self.pause_btn.connect("clicked", self._on_pause_clicked)
        self.header.pack_start(self.pause_btn)

        self.resume_btn = Gtk.Button(icon_name="media-playback-start-symbolic", tooltip_text="Resume Selected")
        self.resume_btn.connect("clicked", self._on_resume_clicked)
        self.header.pack_start(self.resume_btn)

        self.delete_btn = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Delete Selected")
        self.delete_btn.connect("clicked", self._on_delete_clicked)
        self.header.pack_start(self.delete_btn)

        # Right side: Search, Toggle Details, Preferences
        # Search Entry
        self.search_entry = Gtk.SearchEntry(placeholder_text="Filter torrents...")
        self.search_entry.set_max_width_chars(18)
        self.search_entry.connect("search-changed", lambda e: self.torrent_table.set_search_query(e.get_text()))
        self.header.pack_end(self.search_entry)

        # Toggle Details button (bottom panel icon)
        self.toggle_details_btn = Gtk.Button(icon_name="view-bottom-pane-symbolic", tooltip_text="Toggle Details Panel")
        self.toggle_details_btn.connect("clicked", self._on_toggle_details)
        self.header.pack_end(self.toggle_details_btn)

        # Preferences button
        self.settings_btn = Gtk.Button(icon_name="emblem-system-symbolic", tooltip_text="Preferences")
        self.settings_btn.connect("clicked", self._on_preferences_clicked)
        self.header.pack_end(self.settings_btn)

    def _on_toggle_sidebar(self, btn):
        self.sidebar.set_visible(not self.sidebar.get_visible())

    def _on_toggle_details(self, btn):
        self.details_notebook.set_visible(not self.details_notebook.get_visible())

    def _on_sidebar_filter_changed(self, sidebar, filter_type, filter_val):
        self.torrent_table.set_sidebar_filter(filter_type, filter_val)

    def _on_selection_changed(self, *args):
        item = self.torrent_table.get_selected_torrent()
        self.details_notebook.update(item)

    def _on_torrent_activated(self, table, save_path):
        if save_path:
            uri = GLib.filename_to_uri(save_path, None)
            try:
                Gio.AppInfo.launch_default_for_uri(uri, None)
            except Exception as e:
                print(f"Failed to open folder: {e}")

    def _on_add_file_clicked(self, btn):
        dialog = Gtk.FileChooserNative(
            title="Open Torrent File",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
            accept_label="_Open",
            cancel_label="_Cancel",
        )
        filter_torrent = Gtk.FileFilter()
        filter_torrent.set_name("Torrent files (*.torrent)")
        filter_torrent.add_pattern("*.torrent")
        dialog.add_filter(filter_torrent)

        def on_resp(d, resp):
            if resp == Gtk.ResponseType.ACCEPT:
                f = d.get_file()
                if f:
                    add_dlg = AddTorrentDialog(self, self.client, torrent_file=f.get_path())
                    add_dlg.present()
            d.destroy()

        dialog.connect("response", on_resp)
        dialog.show()

    def _on_add_url_clicked(self, btn):
        add_dlg = AddTorrentDialog(self, self.client)
        add_dlg.present()

    def _on_pause_clicked(self, btn):
        items = self.torrent_table.get_selected_items()
        if items:
            self.client.pause_torrent([it.hash for it in items])
            self.refresh_torrents()
            GLib.timeout_add(300, self.refresh_torrents)

    def _on_resume_clicked(self, btn):
        items = self.torrent_table.get_selected_items()
        if items:
            self.client.resume_torrent([it.hash for it in items])
            self.refresh_torrents()
            GLib.timeout_add(300, self.refresh_torrents)

    def _on_delete_clicked(self, btn):
        items = self.torrent_table.get_selected_items()
        if items:
            self.torrent_table._on_delete(items)

    def _on_priority_clicked(self, action):
        items = self.torrent_table.get_selected_items()
        if not items:
            return
        hashes = [it.hash for it in items]
        if action == "top":
            self.client.top_priority(hashes)
        elif action == "up":
            self.client.increase_priority(hashes)
        elif action == "down":
            self.client.decrease_priority(hashes)
        elif action == "bottom":
            self.client.bottom_priority(hashes)
        self.refresh_torrents()

    def show_toast(self, message):
        toast = Adw.Toast.new(message)
        toast.set_timeout(3)
        self.toast_overlay.add_toast(toast)

    def _get_current_instance_safe(self):
        if hasattr(self.app, "settings") and hasattr(self.app.settings, "get_current_instance"):
            try:
                curr = self.app.settings.get_current_instance()
                if isinstance(curr, dict):
                    return curr
            except Exception:
                pass
        return {
            "id": "default",
            "name": "Local qBittorrent",
            "host_ip": "127.0.0.1",
            "port": "8080",
            "use_https": False,
            "username": "admin",
            "host": "http://127.0.0.1:8080"
        }

    def _get_instances_safe(self):
        if hasattr(self.app, "settings") and hasattr(self.app.settings, "get_instances"):
            try:
                insts = self.app.settings.get_instances()
                if isinstance(insts, list) and insts and isinstance(insts[0], dict):
                    return insts
            except Exception:
                pass
        return [self._get_current_instance_safe()]

    def _update_instance_ui(self):
        curr = self._get_current_instance_safe()
        self._update_instance_button(curr)
        self._rebuild_instance_popover()

    def _update_instance_button(self, inst):
        name = inst.get("name") or "qBittorrent"
        self.instance_label.set_text(name)
        host = inst.get("host") or f"{inst.get('host_ip', '127.0.0.1')}:{inst.get('port', '8080')}"
        self.instance_btn.set_tooltip_text(f"Instance: {name} ({host})\nClick to switch or add instance")

    def _rebuild_instance_popover(self):
        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        popover_box.set_margin_top(12)
        popover_box.set_margin_bottom(12)
        popover_box.set_margin_start(12)
        popover_box.set_margin_end(12)
        popover_box.set_size_request(320, -1)

        # Header Title
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_lbl = Gtk.Label(label="<b>qBittorrent Instances</b>", use_markup=True, xalign=0, hexpand=True)
        title_box.append(title_lbl)
        popover_box.append(title_box)

        instances = self._get_instances_safe()
        current_inst = self._get_current_instance_safe()
        curr_id = current_inst.get("id")

        list_box = Gtk.ListBox()
        list_box.add_css_class("boxed-list")
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)

        for inst in instances:
            if not isinstance(inst, dict):
                continue
            inst_id = inst.get("id")
            inst_name = inst.get("name") or f"{inst.get('host_ip', '127.0.0.1')}:{inst.get('port', '8080')}"
            inst_addr = inst.get("host") or f"{inst.get('host_ip', '127.0.0.1')}:{inst.get('port', '8080')}"
            is_active = (inst_id == curr_id)

            row = Adw.ActionRow()
            row.set_title(inst_name)
            row.set_subtitle(inst_addr)
            row.set_activatable(True)

            # Left server icon
            icon = Gtk.Image.new_from_icon_name("network-server-symbolic")
            if is_active:
                icon.add_css_class("accent")
            row.add_prefix(icon)

            # Active indicator
            if is_active:
                active_icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
                active_icon.set_tooltip_text("Active Instance")
                active_icon.add_css_class("accent")
                row.add_suffix(active_icon)

            # Edit button
            edit_btn = Gtk.Button(icon_name="document-edit-symbolic", tooltip_text="Edit instance settings")
            edit_btn.add_css_class("flat")
            edit_btn.set_valign(Gtk.Align.CENTER)
            edit_btn.connect("clicked", lambda b, it=inst: self._on_edit_instance_clicked(it))
            row.add_suffix(edit_btn)

            # Delete button (if > 1 instance)
            if len(instances) > 1:
                del_btn = Gtk.Button(icon_name="user-trash-symbolic", tooltip_text="Delete instance")
                del_btn.add_css_class("flat")
                del_btn.set_valign(Gtk.Align.CENTER)
                del_btn.connect("clicked", lambda b, it=inst: self._on_delete_instance_clicked(it))
                row.add_suffix(del_btn)

            row.connect("activated", lambda r, i_id=inst_id: self._on_instance_row_activated(i_id))
            list_box.append(row)

        popover_box.append(list_box)

        # Separator
        popover_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Add Instance Button
        add_btn = Gtk.Button()
        add_btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.CENTER)
        add_btn_box.append(Gtk.Image.new_from_icon_name("list-add-symbolic"))
        add_btn_box.append(Gtk.Label(label="Add Instance…"))
        add_btn.set_child(add_btn_box)
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", self._on_add_instance_clicked)
        popover_box.append(add_btn)

        self.instance_popover.set_child(popover_box)

    def _on_popover_visible(self, popover):
        if popover.get_visible():
            self._rebuild_instance_popover()

    def _on_instance_row_activated(self, instance_id):
        self.instance_popover.popdown()
        self.switch_to_instance(instance_id)

    def switch_to_instance(self, instance_id, force=False):
        current_inst = self._get_current_instance_safe()
        if not force and current_inst.get("id") == instance_id:
            return

        if hasattr(self.app, "settings") and hasattr(self.app.settings, "set_current_instance_id"):
            self.app.settings.set_current_instance_id(instance_id)

        target_inst = self._get_current_instance_safe()
        self._update_instance_button(target_inst)
        self._rebuild_instance_popover()

        # Clear existing items and reset details/status
        self.items_by_hash.clear()
        self.model.remove_all()
        self.details_notebook.update(None)
        self.details_notebook.update_speed(0, 0)
        self.status_bar.update_status({}, None)

        # Connect client with new parameters
        protocol = "https" if target_inst.get("use_https") else "http"
        full_host = target_inst.get("host") or f"{protocol}://{target_inst.get('host_ip', '127.0.0.1')}:{target_inst.get('port', '8080')}"
        username = target_inst.get("username", "admin")
        password = target_inst.get("password", "")

        connected = False
        if hasattr(self.client, "update_settings"):
            connected = self.client.update_settings(full_host, username, password)

        inst_name = target_inst.get("name", "instance")
        if connected:
            self.show_toast(f"Connected to {inst_name}")
        else:
            self.show_toast(f"Switched to {inst_name} (Connection failed)")

        self.refresh_torrents()

    def _on_add_instance_clicked(self, *args):
        self.instance_popover.popdown()
        settings = getattr(self.app, "settings", None)
        dlg = InstanceDialog(self, settings, instance=None, on_saved=self._on_instance_saved)
        dlg.present()

    def _on_edit_instance_clicked(self, inst):
        self.instance_popover.popdown()
        settings = getattr(self.app, "settings", None)
        dlg = InstanceDialog(self, settings, instance=inst, on_saved=self._on_instance_saved)
        dlg.present()

    def _on_instance_saved(self, saved_inst, is_active=False):
        if is_active:
            self.switch_to_instance(saved_inst["id"], force=True)
        else:
            curr = self._get_current_instance_safe()
            if curr.get("id") == saved_inst.get("id"):
                self.switch_to_instance(saved_inst["id"], force=True)
            else:
                self._update_instance_ui()
                self.show_toast(f"Saved instance '{saved_inst.get('name')}'")

    def _on_delete_instance_clicked(self, inst):
        self.instance_popover.popdown()
        dlg = Adw.MessageDialog(
            transient_for=self,
            heading="Delete Instance?",
            body=f"Are you sure you want to remove '{inst.get('name')}'?"
        )
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("delete", "Delete")
        dlg.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        def on_resp(d, resp):
            if resp == "delete":
                curr_inst = self._get_current_instance_safe()
                was_current = (curr_inst.get("id") == inst.get("id"))
                if hasattr(self.app, "settings") and hasattr(self.app.settings, "delete_instance"):
                    self.app.settings.delete_instance(inst.get("id"))
                if was_current:
                    new_curr = self._get_current_instance_safe()
                    self.switch_to_instance(new_curr.get("id"), force=True)
                else:
                    self._update_instance_ui()
                    self.show_toast(f"Removed instance '{inst.get('name')}'")

        dlg.connect("response", on_resp)
        dlg.present()

    def _on_preferences_clicked(self, btn):
        pref_win = PreferencesDialog(self, self.app.settings, self.client)
        pref_win.connect("close-request", lambda w: self._on_preferences_closed())
        pref_win.present()

    def _on_preferences_closed(self):
        curr = self._get_current_instance_safe()
        self._update_instance_button(curr)
        self._rebuild_instance_popover()
        self.refresh_torrents()

    def _on_connection_setup_clicked(self):
        welcome_win = WelcomeWindow(self.app, self.app.settings, self.client, is_reconnect=False)
        welcome_win.set_transient_for(self)
        welcome_win.connect("connected", lambda w: self.refresh_torrents())
        welcome_win.present()

    def format_speed(self, speed):
        """Maintained for backwards compatibility with test_app.py."""
        if speed < 1024:
            return f"{speed} B/s"
        elif speed < 1024 * 1024:
            return f"{speed/1024:.1f} KB/s"
        else:
            return f"{speed/(1024*1024):.1f} MB/s"

    def refresh_torrents(self):
        # 1. Fetch torrents and maindata
        torrents_data = self.client.get_torrents()
        if not hasattr(torrents_data, '__iter__') or isinstance(torrents_data, (str, bytes)):
            torrents_data = []
        
        # Build maps
        new_data_by_hash = {
            data['hash']: data for data in torrents_data
            if hasattr(data, 'get') and data.get('hash')
        }

        # Remove deleted
        to_remove = []
        for i in range(self.model.get_n_items()):
            item = self.model.get_item(i)
            if item.hash not in new_data_by_hash:
                to_remove.append(i)

        for i in sorted(to_remove, reverse=True):
            item = self.model.get_item(i)
            if item.hash in self.items_by_hash:
                del self.items_by_hash[item.hash]
            self.model.remove(i)

        # Update or insert
        for h, data in new_data_by_hash.items():
            if h in self.items_by_hash:
                self.items_by_hash[h].update(data)
            else:
                new_item = TorrentItem(data)
                self.items_by_hash[h] = new_item
                self.model.append(new_item)

        # 2. Update transfer info & status bar
        transfer_info = self.client.get_transfer_info()
        transfer_info = transfer_info if hasattr(transfer_info, 'get') else {}

        prefs = self.client.get_app_preferences()
        prefs = prefs if hasattr(prefs, 'get') else {}
        save_path = prefs.get('save_path', '')
        
        free_space = self.client.get_free_space(save_path) if save_path else None
        free_space = free_space if isinstance(free_space, (int, float)) else None

        self.status_bar.update_status(transfer_info, free_space, prefs=prefs)

        # 3. Update speed graph
        if transfer_info:
            dl_rate = transfer_info.get('dl_info_speed', 0)
            up_rate = transfer_info.get('up_info_speed', 0)
            if isinstance(dl_rate, (int, float)) and isinstance(up_rate, (int, float)):
                self.details_notebook.update_speed(dl_rate, up_rate)

        # 4. Update sidebar counts
        categories = self.client.get_categories()
        categories = categories if hasattr(categories, 'items') else {}
        tags = self.client.get_tags()
        tags = tags if hasattr(tags, '__iter__') and not isinstance(tags, (str, bytes)) else []
        trackers_map = {}
        for item in self.items_by_hash.values():
            tr = item.raw_data.get('tracker', '')
            if tr:
                trackers_map[tr] = trackers_map.get(tr, 0) + 1

        all_items = list(self.items_by_hash.values())
        self.sidebar.update_counts(all_items, categories, tags, trackers_map)

        # 5. Refresh filter model so items move if status changed
        self.torrent_table.custom_filter.changed(Gtk.FilterChange.DIFFERENT)

        # 6. Refresh details panel for current selection
        self._on_selection_changed()

        return True
