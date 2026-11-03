import threading
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, GLib, Adw, GObject

class WelcomeWindow(Adw.Window):
    """Modern Libadwaita welcome screen for setting up the qBittorrent connection."""

    __gsignals__ = {
        'connected': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, app, settings, client, is_reconnect=False):
        super().__init__(application=app, title="Welcome to GTKittorrent")
        self.app = app
        self.settings = settings
        self.client = client
        self.is_reconnect = is_reconnect

        self.set_default_size(540, 680)
        self.set_modal(True)

        self._build_ui()

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # HeaderBar
        header = Adw.HeaderBar()
        main_box.append(header)

        # Scrolled Window
        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        main_box.append(scrolled)

        clamp = Adw.Clamp(maximum_size=500, margin_top=24, margin_bottom=24, margin_start=16, margin_end=16)
        scrolled.set_child(clamp)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        clamp.set_child(content_box)

        # Status Page Header
        status_page = Adw.StatusPage(
            icon_name="network-workgroup-symbolic",
            title="Welcome to GTKittorrent",
            description="Configure your connection to qBittorrent Web UI" if not self.is_reconnect
                        else "Could not connect to qBittorrent. Please verify your settings."
        )
        content_box.append(status_page)

        # Connection Form Group
        group = Adw.PreferencesGroup(title="Connection Details")
        content_box.append(group)

        self.name_entry = Adw.EntryRow(title="Instance Name")
        default_inst_name = "Local qBittorrent"
        if hasattr(self.settings, "get_current_instance"):
            curr_inst = self.settings.get_current_instance()
            if isinstance(curr_inst, dict) and curr_inst.get("name"):
                default_inst_name = curr_inst["name"]
        self.name_entry.set_text(self.settings.get("name") or default_inst_name)
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
        self.password_entry.set_text(self.settings.get("password") or "adminpassword")
        group.add(self.password_entry)

        self.https_row = Adw.ActionRow(title="Use HTTPS")
        self.https_switch = Gtk.Switch(active=bool(self.settings.get("use_https")), valign=Gtk.Align.CENTER)
        self.https_row.add_suffix(self.https_switch)
        group.add(self.https_row)

        # Test Connection Row
        self.test_row = Adw.ActionRow(title="Connection Test")
        self.test_spinner = Gtk.Spinner(valign=Gtk.Align.CENTER)
        self.test_row.add_suffix(self.test_spinner)

        self.test_btn = Gtk.Button(label="Test Connection", valign=Gtk.Align.CENTER)
        self.test_btn.connect("clicked", self._on_test_clicked)
        self.test_row.add_suffix(self.test_btn)
        group.add(self.test_row)

        # Feedback box
        self.feedback_box = Gtk.Box(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=8,
            margin_start=12,
            margin_end=12,
            margin_top=4,
            margin_bottom=8
        )
        self.feedback_icon = Gtk.Image()
        self.feedback_lbl = Gtk.Label(xalign=0, wrap=True, hexpand=True, use_markup=True)
        self.feedback_box.append(self.feedback_icon)
        self.feedback_box.append(self.feedback_lbl)
        self.feedback_box.set_visible(False)
        group.add(self.feedback_box)

        # Quick Tip Box
        tip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, margin_start=8, margin_end=8)
        tip_icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
        tip_lbl = Gtk.Label(
            label="<small>Ensure Web UI is enabled in qBittorrent: <b>Tools → Preferences → Web UI</b>.</small>",
            use_markup=True,
            wrap=True,
            xalign=0
        )
        tip_box.append(tip_icon)
        tip_box.append(tip_lbl)
        content_box.append(tip_box)

        # Action Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=12)
        content_box.append(btn_box)

        self.connect_btn = Gtk.Button(
            label="Connect & Continue",
            css_classes=["suggested-action", "pill"],
            valign=Gtk.Align.CENTER
        )
        self.connect_btn.connect("clicked", self._on_connect_clicked)
        btn_box.append(self.connect_btn)

        self.connect_anyway_btn = Gtk.Button(
            label="Save & Open Offline",
            css_classes=["flat"],
            valign=Gtk.Align.CENTER
        )
        self.connect_anyway_btn.connect("clicked", self._on_connect_anyway_clicked)
        btn_box.append(self.connect_anyway_btn)

    def _get_form_values(self):
        host_ip = self.host_entry.get_text().strip() or "127.0.0.1"
        port = self.port_entry.get_text().strip() or "8080"
        username = self.username_entry.get_text().strip()
        password = self.password_entry.get_text().strip()
        use_https = self.https_switch.get_active()
        protocol = "https" if use_https else "http"
        full_host = f"{protocol}://{host_ip}:{port}"
        return host_ip, port, username, password, use_https, full_host

    def _on_test_clicked(self, btn):
        _, _, username, password, _, full_host = self._get_form_values()

        self.test_btn.set_sensitive(False)
        self.test_spinner.start()
        self.feedback_box.set_visible(False)

        def worker():
            from ..client.client import QBittorrentClient
            success, message, _ = QBittorrentClient.test_connection_params(full_host, username, password)
            GLib.idle_add(self._on_test_result, success, message)

        threading.Thread(target=worker, daemon=True).start()

    def _on_test_result(self, success, message):
        self.test_spinner.stop()
        self.test_btn.set_sensitive(True)
        self.feedback_box.set_visible(True)

        if success:
            self.feedback_icon.set_from_icon_name("emblem-ok-symbolic")
            self.feedback_lbl.set_markup(f"<span color='#2ec27e'><b>Connected:</b> {message}</span>")
        else:
            self.feedback_icon.set_from_icon_name("dialog-error-symbolic")
            self.feedback_lbl.set_markup(f"<span color='#e01b24'><b>Failed:</b> {message}</span>")

    def _save_and_apply(self):
        host_ip, port, username, password, use_https, full_host = self._get_form_values()
        name = self.name_entry.get_text().strip() or "Local qBittorrent"

        self.settings.set("name", name)
        self.settings.set("host_ip", host_ip)
        self.settings.set("port", port)
        self.settings.set("username", username)
        self.settings.set("password", password)
        self.settings.set("use_https", use_https)
        self.settings.set("host", full_host)
        self.settings.set("configured", True)

        if self.client:
            self.client.update_settings(full_host, username, password)

    def _on_connect_clicked(self, btn):
        host_ip, port, username, password, use_https, full_host = self._get_form_values()

        self.connect_btn.set_sensitive(False)
        self.test_spinner.start()
        self.feedback_box.set_visible(False)

        def worker():
            from ..client.client import QBittorrentClient
            success, message, _ = QBittorrentClient.test_connection_params(full_host, username, password)
            GLib.idle_add(self._on_connect_result, success, message)

        threading.Thread(target=worker, daemon=True).start()

    def _on_connect_result(self, success, message):
        self.test_spinner.stop()
        self.connect_btn.set_sensitive(True)

        if success:
            self._save_and_apply()
            self.emit("connected")
            self.close()
        else:
            self.feedback_box.set_visible(True)
            self.feedback_icon.set_from_icon_name("dialog-error-symbolic")
            self.feedback_lbl.set_markup(f"<span color='#e01b24'><b>Failed:</b> {message}</span>")

    def _on_connect_anyway_clicked(self, btn):
        self._save_and_apply()
        self.emit("connected")
        self.close()
