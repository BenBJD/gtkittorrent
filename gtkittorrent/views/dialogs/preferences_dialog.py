import threading
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, GLib, Adw

class PreferencesDialog(Adw.PreferencesWindow):
    """Comprehensive preferences dialog matching qBittorrent's options."""

    def __init__(self, parent, settings, client):
        super().__init__(transient_for=parent, modal=True)
        self.set_title("Preferences")
        self.set_default_size(680, 620)
        self.settings = settings
        self.client = client
        self.qb_prefs = self.client.get_app_preferences() if self.client else {}

        self._setup_connection_page()
        self._setup_downloads_page()
        self._setup_speed_page()
        self._setup_bittorrent_page()

        self.connect("close-request", self._on_close)

    def _setup_connection_page(self):
        page = Adw.PreferencesPage(title="Connection", icon_name="network-workgroup-symbolic")
        self.add(page)

        group = Adw.PreferencesGroup(title="qBittorrent Web UI Server")
        page.add(group)

        self.name_entry = Adw.EntryRow(title="Instance Name")
        current_name = "Local qBittorrent"
        if hasattr(self.settings, "get_current_instance"):
            curr_inst = self.settings.get_current_instance()
            if isinstance(curr_inst, dict) and curr_inst.get("name"):
                current_name = curr_inst["name"]
        self.name_entry.set_text(self.settings.get("name") or current_name)
        group.add(self.name_entry)

        self.host_entry = Adw.EntryRow(title="IP / Domain")
        self.host_entry.set_text(self.settings.get("host_ip") or "127.0.0.1")
        group.add(self.host_entry)

        self.port_entry = Adw.EntryRow(title="Port")
        self.port_entry.set_text(str(self.settings.get("port") or "8080"))
        group.add(self.port_entry)

        self.username_entry = Adw.EntryRow(title="Username")
        self.username_entry.set_text(self.settings.get("username") or "admin")
        group.add(self.username_entry)

        self.password_entry = Adw.PasswordEntryRow(title="Password")
        self.password_entry.set_text(self.settings.get("password") or "")
        group.add(self.password_entry)

        self.https_row = Adw.ActionRow(title="Use HTTPS")
        self.https_switch = Gtk.Switch(active=bool(self.settings.get("use_https")), valign=Gtk.Align.CENTER)
        self.https_row.add_suffix(self.https_switch)
        group.add(self.https_row)

        # Test Connection Row
        self.test_conn_row = Adw.ActionRow(title="Connection Test")
        self.test_conn_row.set_subtitle("Verify credentials and server reachability")

        self.test_spinner = Gtk.Spinner(valign=Gtk.Align.CENTER)
        self.test_conn_row.add_suffix(self.test_spinner)

        self.test_btn = Gtk.Button(label="Test Connection", valign=Gtk.Align.CENTER)
        self.test_btn.connect("clicked", self._on_test_connection_clicked)
        self.test_conn_row.add_suffix(self.test_btn)
        group.add(self.test_conn_row)

        # Feedback box
        self.test_feedback_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            margin_start=12,
            margin_end=12,
            margin_top=4,
            margin_bottom=8
        )
        self.test_feedback_icon = Gtk.Image()
        self.test_feedback_lbl = Gtk.Label(xalign=0, wrap=True, hexpand=True, use_markup=True)
        self.test_feedback_box.append(self.test_feedback_icon)
        self.test_feedback_box.append(self.test_feedback_lbl)
        self.test_feedback_box.set_visible(False)
        group.add(self.test_feedback_box)

        conn_group = Adw.PreferencesGroup(title="Listening Port &amp; Limits")
        page.add(conn_group)

        self.listen_port_row = Adw.SpinRow(
            title="Peer Listening Port",
            adjustment=Gtk.Adjustment(lower=1, upper=65535, step_increment=1, page_increment=10)
        )
        self.listen_port_row.set_value(self.qb_prefs.get("listen_port", 6881))
        conn_group.add(self.listen_port_row)

        self.upnp_row = Adw.ActionRow(title="Use UPnP / NAT-PMP port forwarding")
        self.upnp_switch = Gtk.Switch(active=bool(self.qb_prefs.get("upnp", True)), valign=Gtk.Align.CENTER)
        self.upnp_row.add_suffix(self.upnp_switch)
        conn_group.add(self.upnp_row)

        self.max_connec_row = Adw.SpinRow(
            title="Global Maximum Connections",
            adjustment=Gtk.Adjustment(lower=0, upper=5000, step_increment=10, page_increment=50)
        )
        self.max_connec_row.set_value(self.qb_prefs.get("max_connec", 500))
        conn_group.add(self.max_connec_row)

    def _setup_downloads_page(self):
        page = Adw.PreferencesPage(title="Downloads", icon_name="folder-download-symbolic")
        self.add(page)

        group = Adw.PreferencesGroup(title="Default Save Path")
        page.add(group)

        self.save_path_entry = Adw.EntryRow(title="Save files to location")
        self.save_path_entry.set_text(self.qb_prefs.get("save_path", ""))
        group.add(self.save_path_entry)

        self.temp_path_enabled_row = Adw.ActionRow(title="Keep incomplete torrents in separate location")
        self.temp_path_switch = Gtk.Switch(active=bool(self.qb_prefs.get("temp_path_enabled", False)), valign=Gtk.Align.CENTER)
        self.temp_path_enabled_row.add_suffix(self.temp_path_switch)
        group.add(self.temp_path_enabled_row)

        self.temp_path_entry = Adw.EntryRow(title="Incomplete files location")
        self.temp_path_entry.set_text(self.qb_prefs.get("temp_path", ""))
        group.add(self.temp_path_entry)

        disk_group = Adw.PreferencesGroup(title="File Management")
        page.add(disk_group)

        self.append_extension_row = Adw.ActionRow(title="Append .!qB extension to incomplete files")
        self.append_extension_switch = Gtk.Switch(active=bool(self.qb_prefs.get("incomplete_files_ext", False)), valign=Gtk.Align.CENTER)
        self.append_extension_row.add_suffix(self.append_extension_switch)
        disk_group.add(self.append_extension_row)

        self.preallocate_row = Adw.ActionRow(title="Pre-allocate disk space for all files")
        self.preallocate_switch = Gtk.Switch(active=bool(self.qb_prefs.get("preallocate_all", False)), valign=Gtk.Align.CENTER)
        self.preallocate_row.add_suffix(self.preallocate_switch)
        disk_group.add(self.preallocate_row)

    def _setup_speed_page(self):
        page = Adw.PreferencesPage(title="Speed", icon_name="network-transmit-receive-symbolic")
        self.add(page)

        group = Adw.PreferencesGroup(title="Global Rate Limits (0 = Unlimited)")
        page.add(group)

        self.dl_limit_row = Adw.SpinRow(
            title="Download Limit (KiB/s)",
            adjustment=Gtk.Adjustment(lower=0, upper=1000000, step_increment=10, page_increment=100)
        )
        dl = self.qb_prefs.get("dl_limit", 0)
        self.dl_limit_row.set_value(dl / 1024 if dl > 0 else 0)
        group.add(self.dl_limit_row)

        self.up_limit_row = Adw.SpinRow(
            title="Upload Limit (KiB/s)",
            adjustment=Gtk.Adjustment(lower=0, upper=1000000, step_increment=10, page_increment=100)
        )
        up = self.qb_prefs.get("up_limit", 0)
        self.up_limit_row.set_value(up / 1024 if up > 0 else 0)
        group.add(self.up_limit_row)

        alt_group = Adw.PreferencesGroup(title="Alternative Rate Limits (Turtle Mode)")
        page.add(alt_group)

        self.alt_dl_limit_row = Adw.SpinRow(
            title="Alternative Download Limit (KiB/s)",
            adjustment=Gtk.Adjustment(lower=0, upper=1000000, step_increment=10, page_increment=100)
        )
        alt_dl = self.qb_prefs.get("alt_dl_limit", 0)
        self.alt_dl_limit_row.set_value(alt_dl / 1024 if alt_dl > 0 else 0)
        alt_group.add(self.alt_dl_limit_row)

        self.alt_up_limit_row = Adw.SpinRow(
            title="Alternative Upload Limit (KiB/s)",
            adjustment=Gtk.Adjustment(lower=0, upper=1000000, step_increment=10, page_increment=100)
        )
        alt_up = self.qb_prefs.get("alt_up_limit", 0)
        self.alt_up_limit_row.set_value(alt_up / 1024 if alt_up > 0 else 0)
        alt_group.add(self.alt_up_limit_row)

    def _setup_bittorrent_page(self):
        page = Adw.PreferencesPage(title="BitTorrent", icon_name="system-run-symbolic")
        self.add(page)

        privacy_group = Adw.PreferencesGroup(title="Privacy &amp; Protocol")
        page.add(privacy_group)

        self.dht_row = Adw.ActionRow(title="Enable DHT (Distributed Hash Table)")
        self.dht_switch = Gtk.Switch(active=bool(self.qb_prefs.get("dht", True)), valign=Gtk.Align.CENTER)
        self.dht_row.add_suffix(self.dht_switch)
        privacy_group.add(self.dht_row)

        self.pex_row = Adw.ActionRow(title="Enable PeX (Peer Exchange)")
        self.pex_switch = Gtk.Switch(active=bool(self.qb_prefs.get("pex", True)), valign=Gtk.Align.CENTER)
        self.pex_row.add_suffix(self.pex_switch)
        privacy_group.add(self.pex_row)

        self.lsd_row = Adw.ActionRow(title="Enable LSD (Local Peer Discovery)")
        self.lsd_switch = Gtk.Switch(active=bool(self.qb_prefs.get("lsd", True)), valign=Gtk.Align.CENTER)
        self.lsd_row.add_suffix(self.lsd_switch)
        privacy_group.add(self.lsd_row)

        queue_group = Adw.PreferencesGroup(title="Torrent Queueing")
        page.add(queue_group)

        self.queueing_row = Adw.ActionRow(title="Enable Torrent Queueing")
        self.queueing_switch = Gtk.Switch(active=bool(self.qb_prefs.get("queueing_enabled", True)), valign=Gtk.Align.CENTER)
        self.queueing_row.add_suffix(self.queueing_switch)
        queue_group.add(self.queueing_row)

        self.max_active_dl_row = Adw.SpinRow(
            title="Maximum active downloads",
            adjustment=Gtk.Adjustment(lower=-1, upper=1000, step_increment=1, page_increment=5)
        )
        self.max_active_dl_row.set_value(self.qb_prefs.get("max_active_downloads", 3))
        queue_group.add(self.max_active_dl_row)

        self.max_active_up_row = Adw.SpinRow(
            title="Maximum active uploads",
            adjustment=Gtk.Adjustment(lower=-1, upper=1000, step_increment=1, page_increment=5)
        )
        self.max_active_up_row.set_value(self.qb_prefs.get("max_active_uploads", 3))
        queue_group.add(self.max_active_up_row)

        self.max_active_torrents_row = Adw.SpinRow(
            title="Maximum active torrents",
            adjustment=Gtk.Adjustment(lower=-1, upper=1000, step_increment=1, page_increment=5)
        )
        self.max_active_torrents_row.set_value(self.qb_prefs.get("max_active_torrents", 5))
        queue_group.add(self.max_active_torrents_row)

    def _on_test_connection_clicked(self, btn):
        host_ip = self.host_entry.get_text().strip()
        port = self.port_entry.get_text().strip()
        username = self.username_entry.get_text().strip()
        password = self.password_entry.get_text().strip()
        use_https = self.https_switch.get_active()

        protocol = "https" if use_https else "http"
        full_host = f"{protocol}://{host_ip}:{port}"

        self.test_btn.set_sensitive(False)
        self.test_spinner.start()
        self.test_feedback_box.set_visible(False)

        def worker():
            from ...client.client import QBittorrentClient
            success, message, _ = QBittorrentClient.test_connection_params(full_host, username, password)
            GLib.idle_add(self._on_test_connection_result, success, message)

        threading.Thread(target=worker, daemon=True).start()

    def _on_test_connection_result(self, success, message):
        self.test_spinner.stop()
        self.test_btn.set_sensitive(True)
        self.test_feedback_box.set_visible(True)

        if success:
            self.test_feedback_icon.set_from_icon_name("emblem-ok-symbolic")
            self.test_feedback_lbl.set_markup(f"<span color='#2ec27e'><b>Success:</b> {message}</span>")
        else:
            self.test_feedback_icon.set_from_icon_name("dialog-error-symbolic")
            self.test_feedback_lbl.set_markup(f"<span color='#e01b24'><b>Failed:</b> {message}</span>")

    def _on_close(self, *args):
        host_ip = self.host_entry.get_text().strip()
        port = self.port_entry.get_text().strip()
        username = self.username_entry.get_text().strip()
        password = self.password_entry.get_text().strip()
        use_https = self.https_switch.get_active()

        if hasattr(self, "name_entry"):
            name = self.name_entry.get_text().strip() or "Local qBittorrent"
            self.settings.set("name", name)

        self.settings.set("host_ip", host_ip)
        self.settings.set("port", port)
        self.settings.set("username", username)
        self.settings.set("password", password)
        self.settings.set("use_https", use_https)

        protocol = "https" if use_https else "http"
        full_host = f"{protocol}://{host_ip}:{port}"
        self.settings.set("host", full_host)

        if self.client:
            self.client.update_settings(full_host, username, password)

            new_qb_prefs = {
                "listen_port": int(self.listen_port_row.get_value()),
                "upnp": self.upnp_switch.get_active(),
                "max_connec": int(self.max_connec_row.get_value()),
                "save_path": self.save_path_entry.get_text().strip(),
                "temp_path_enabled": self.temp_path_switch.get_active(),
                "temp_path": self.temp_path_entry.get_text().strip(),
                "incomplete_files_ext": self.append_extension_switch.get_active(),
                "preallocate_all": self.preallocate_switch.get_active(),
                "dl_limit": int(self.dl_limit_row.get_value() * 1024),
                "up_limit": int(self.up_limit_row.get_value() * 1024),
                "alt_dl_limit": int(self.alt_dl_limit_row.get_value() * 1024),
                "alt_up_limit": int(self.alt_up_limit_row.get_value() * 1024),
                "dht": self.dht_switch.get_active(),
                "pex": self.pex_switch.get_active(),
                "lsd": self.lsd_switch.get_active(),
                "queueing_enabled": self.queueing_switch.get_active(),
                "max_active_downloads": int(self.max_active_dl_row.get_value()),
                "max_active_uploads": int(self.max_active_up_row.get_value()),
                "max_active_torrents": int(self.max_active_torrents_row.get_value()),
            }
            self.client.set_app_preferences(new_qb_prefs)
