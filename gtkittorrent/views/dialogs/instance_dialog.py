import threading
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, GLib, Adw

from ...client.client import QBittorrentClient

class InstanceDialog(Adw.Window):
    """Dialog for adding or editing a qBittorrent instance."""

    def __init__(self, parent, settings, instance=None, on_saved=None):
        super().__init__(transient_for=parent, modal=True)
        self.settings = settings
        self.instance = instance
        self.on_saved = on_saved
        self.is_edit = instance is not None

        title = "Edit Instance" if self.is_edit else "Add qBittorrent Instance"
        self.set_title(title)
        self.set_default_size(480, 560)

        self._build_ui()

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # HeaderBar
        header = Adw.HeaderBar()
        main_box.append(header)

        # Cancel button
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)

        # Save / Add button
        action_label = "Save" if self.is_edit else "Add"
        self.save_btn = Gtk.Button(label=action_label, css_classes=["suggested-action"])
        self.save_btn.connect("clicked", self._on_save_clicked)
        header.pack_end(self.save_btn)

        # Scrolled content
        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        main_box.append(scrolled)

        clamp = Adw.Clamp(maximum_size=440, margin_top=16, margin_bottom=24, margin_start=16, margin_end=16)
        scrolled.set_child(clamp)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(content_box)

        # General Group
        inst_group = Adw.PreferencesGroup(title="Instance Information")
        content_box.append(inst_group)

        self.name_entry = Adw.EntryRow(title="Instance Name")
        default_name = self.instance.get("name", "") if self.is_edit else ""
        self.name_entry.set_text(default_name)
        inst_group.add(self.name_entry)

        # Connection Group
        conn_group = Adw.PreferencesGroup(title="Connection Details")
        content_box.append(conn_group)

        self.host_entry = Adw.EntryRow(title="IP / Domain")
        default_host = self.instance.get("host_ip", "127.0.0.1") if self.is_edit else "127.0.0.1"
        self.host_entry.set_text(default_host)
        conn_group.add(self.host_entry)

        self.port_entry = Adw.EntryRow(title="Port")
        default_port = str(self.instance.get("port", "8080")) if self.is_edit else "8080"
        self.port_entry.set_text(default_port)
        conn_group.add(self.port_entry)

        self.username_entry = Adw.EntryRow(title="Username")
        default_user = self.instance.get("username", "admin") if self.is_edit else "admin"
        self.username_entry.set_text(default_user)
        conn_group.add(self.username_entry)

        self.password_entry = Adw.PasswordEntryRow(title="Password")
        default_pass = self.instance.get("password", "") if self.is_edit else ""
        self.password_entry.set_text(default_pass)
        conn_group.add(self.password_entry)

        self.https_row = Adw.ActionRow(title="Use HTTPS")
        is_https = bool(self.instance.get("use_https", False)) if self.is_edit else False
        self.https_switch = Gtk.Switch(active=is_https, valign=Gtk.Align.CENTER)
        self.https_row.add_suffix(self.https_switch)
        conn_group.add(self.https_row)

        if not self.is_edit:
            self.switch_to_row = Adw.ActionRow(title="Switch to this instance now")
            self.switch_to_switch = Gtk.Switch(active=True, valign=Gtk.Align.CENTER)
            self.switch_to_row.add_suffix(self.switch_to_switch)
            conn_group.add(self.switch_to_row)

        # Connection Test Row
        test_group = Adw.PreferencesGroup(title="Verification")
        content_box.append(test_group)

        self.test_row = Adw.ActionRow(title="Connection Test")
        self.test_row.set_subtitle("Verify reachability before saving")
        self.test_spinner = Gtk.Spinner(valign=Gtk.Align.CENTER)
        self.test_row.add_suffix(self.test_spinner)

        self.test_btn = Gtk.Button(label="Test Connection", valign=Gtk.Align.CENTER)
        self.test_btn.connect("clicked", self._on_test_clicked)
        self.test_row.add_suffix(self.test_btn)
        test_group.add(self.test_row)

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
        test_group.add(self.feedback_box)

    def _get_form_values(self):
        name = self.name_entry.get_text().strip()
        host_ip = self.host_entry.get_text().strip() or "127.0.0.1"
        port = self.port_entry.get_text().strip() or "8080"
        username = self.username_entry.get_text().strip()
        password = self.password_entry.get_text().strip()
        use_https = self.https_switch.get_active()
        if not name:
            name = f"{host_ip}:{port}"
        protocol = "https" if use_https else "http"
        full_host = f"{protocol}://{host_ip}:{port}"
        return name, host_ip, port, username, password, use_https, full_host

    def _on_test_clicked(self, btn):
        _, _, _, username, password, _, full_host = self._get_form_values()

        self.test_btn.set_sensitive(False)
        self.test_spinner.start()
        self.feedback_box.set_visible(False)

        def worker():
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

    def _on_save_clicked(self, btn):
        name, host_ip, port, username, password, use_https, full_host = self._get_form_values()

        if not host_ip:
            self.feedback_box.set_visible(True)
            self.feedback_icon.set_from_icon_name("dialog-error-symbolic")
            self.feedback_lbl.set_markup("<span color='#e01b24'><b>Error:</b> Host / IP cannot be empty</span>")
            return

        try:
            p_int = int(port)
            if p_int < 1 or p_int > 65535:
                raise ValueError()
        except ValueError:
            self.feedback_box.set_visible(True)
            self.feedback_icon.set_from_icon_name("dialog-error-symbolic")
            self.feedback_lbl.set_markup("<span color='#e01b24'><b>Error:</b> Port must be a number between 1 and 65535</span>")
            return

        is_local = host_ip in ("127.0.0.1", "localhost", "::1")

        if self.is_edit:
            self.settings.update_instance(
                self.instance["id"],
                name=name,
                host_ip=host_ip,
                port=port,
                username=username,
                password=password,
                use_https=use_https,
                local=is_local
            )
            saved_inst = self.settings.get_instance(self.instance["id"])
            if self.on_saved:
                self.on_saved(saved_inst, is_active=False)
        else:
            make_active = self.switch_to_switch.get_active() if hasattr(self, 'switch_to_switch') else True
            saved_inst = self.settings.add_instance(
                name=name,
                host_ip=host_ip,
                port=port,
                username=username,
                password=password,
                use_https=use_https,
                local=is_local,
                make_active=make_active
            )
            if self.on_saved:
                self.on_saved(saved_inst, is_active=make_active)

        self.close()
