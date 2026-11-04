import threading
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, GLib, Adw, GObject

from ..client.daemon import LocalDaemonManager
from ..utils.qbt_config import read_qbt_config, configure_qbt_webui

class WelcomeWindow(Adw.Window):
    """Modern Libadwaita onboarding assistant for setting up local or remote qBittorrent instances."""

    __gsignals__ = {
        'connected': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, app, settings, client, is_reconnect=False):
        super().__init__(application=app, title="Welcome to GTKittorrent")
        self.app = app
        self.settings = settings
        self.client = client
        self.is_reconnect = is_reconnect
        self.daemon_mgr = LocalDaemonManager.get_instance()
        self.configured_count = 0
        self.local_configured = False
        self.summary_rows = []

        self.set_default_size(580, 740)
        self.set_modal(True)

        self._build_ui()
        self._check_initial_state()

    def _build_ui(self):
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(main_box)

        # HeaderBar
        self.header = Adw.HeaderBar()
        self.header.set_centering_policy(Adw.CenteringPolicy.LOOSE)
        self.title_widget = Adw.WindowTitle(title="Welcome to GTKittorrent")
        self.header.set_title_widget(self.title_widget)
        main_box.append(self.header)

        # Back Button in Header
        self.back_btn = Gtk.Button(icon_name="go-previous-symbolic", tooltip_text="Back")
        self.back_btn.connect("clicked", lambda b: self._go_to_page(0))
        self.back_btn.set_visible(False)
        self.header.pack_start(self.back_btn)

        # Done / Close Button in Header (shown when already configured or opened from app)
        is_already_completed = bool(self.settings.get("welcome_completed", False)) if self.settings else False
        if is_already_completed:
            self.done_header_btn = Gtk.Button(label="Done")
            self.done_header_btn.connect("clicked", lambda b: self.close())
            self.header.pack_end(self.done_header_btn)

        # Main Carousel
        self.carousel = Adw.Carousel()
        self.carousel.set_vexpand(True)
        self.carousel.set_hexpand(True)
        self.carousel.set_allow_mouse_drag(False)
        self.carousel.set_allow_scroll_wheel(False)
        main_box.append(self.carousel)

        # Build 3 Pages
        self.page_mode = self._build_mode_selection_page()
        self.page_local = self._build_local_page()
        self.page_remote = self._build_remote_page()

        self.carousel.append(self.page_mode)
        self.carousel.append(self.page_local)
        self.carousel.append(self.page_remote)

        # Indicator Dots at bottom
        self.dots = Adw.CarouselIndicatorDots(carousel=self.carousel, margin_bottom=12)
        main_box.append(self.dots)

    def _go_to_page(self, page_index):
        target = [self.page_mode, self.page_local, self.page_remote][page_index]
        self.carousel.scroll_to(target, True)
        self.back_btn.set_visible(page_index > 0)
        if page_index == 0:
            self.title_widget.set_title("Welcome to GTKittorrent")
            self.title_widget.set_subtitle("")
            self._update_instances_summary()
        elif page_index == 1:
            self.title_widget.set_title("Local Setup")
            self.title_widget.set_subtitle("This Computer")
            self._refresh_local_engine_status()
        elif page_index == 2:
            self.title_widget.set_title("Remote Setup")
            self.title_widget.set_subtitle("Network Server / NAS")

    def _check_initial_state(self):
        self.local_configured = False
        if self.settings and hasattr(self.settings, "get_instances"):
            for inst in self.settings.get_instances():
                if inst.get("local", False):
                    self.local_configured = True
                    break

        # Read existing qBittorrent config for smart defaults on local port
        qbt_info = read_qbt_config()
        if qbt_info["exists"] and not (self.settings and self.settings.get("configured", False)):
            detected_port = str(qbt_info.get("webui_port", 8080))
            self.local_port_entry.set_text(detected_port)
            if qbt_info.get("webui_username"):
                self.local_username_entry.set_text(qbt_info["webui_username"])

        curr_ip = (self.settings.get("host_ip") if self.settings else "127.0.0.1") or "127.0.0.1"
        is_local = curr_ip in ("127.0.0.1", "localhost", "::1")

        if self.is_reconnect:
            if is_local:
                self._go_to_page(1)
            else:
                self._go_to_page(2)
        else:
            self._go_to_page(0)

    # ---------------- Page 0: Mode Selection ----------------
    def _build_mode_selection_page(self):
        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        clamp = Adw.Clamp(maximum_size=520, margin_top=20, margin_bottom=24, margin_start=16, margin_end=16)
        scrolled.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        clamp.set_child(box)

        status_page = Adw.StatusPage(
            icon_name="network-workgroup-symbolic",
            title="Welcome to GTKittorrent",
            description="A modern Libadwaita desktop client for qBittorrent.\nChoose an instance to set up:"
        )
        box.append(status_page)

        # Configured Instances Group (visible when instances are configured)
        self.configured_instances_group = Adw.PreferencesGroup(title="Configured Instances")
        self.configured_instances_group.set_visible(False)
        box.append(self.configured_instances_group)

        # Choice Group
        group = Adw.PreferencesGroup(title="Add or Configure Instance")
        box.append(group)

        # Local Card
        self.local_row = Adw.ActionRow(
            title="This Computer (Local)",
            subtitle="Manage torrents directly on this machine. Runs quietly in the background.",
            activatable=True
        )
        self.local_row.add_prefix(Gtk.Image.new_from_icon_name("computer-symbolic"))
        self.local_row_suffix_img = Gtk.Image.new_from_icon_name("go-next-symbolic")
        self.local_row.add_suffix(self.local_row_suffix_img)
        self.local_row.connect("activated", lambda r: self._go_to_page(1))
        group.add(self.local_row)

        # Remote Card
        self.remote_row = Adw.ActionRow(
            title="Remote Server / NAS",
            subtitle="Connect over your network to an existing qBittorrent Web UI.",
            activatable=True
        )
        self.remote_row.add_prefix(Gtk.Image.new_from_icon_name("network-server-symbolic"))
        self.remote_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        self.remote_row.connect("activated", lambda r: self._go_to_page(2))
        group.add(self.remote_row)

        # Finish Setup Button on Mode Page
        self.mode_finish_btn = Gtk.Button(
            label="Open GTKittorrent",
            css_classes=["suggested-action", "pill"],
            valign=Gtk.Align.CENTER
        )
        self.mode_finish_btn.connect("clicked", lambda b: self._finish_and_open())
        self.mode_finish_btn.set_visible(False)
        box.append(self.mode_finish_btn)

        return scrolled

    def _update_instances_summary(self):
        # Update local card state if local instance is configured
        if self.local_configured:
            self.local_row.set_sensitive(False)
            self.local_row.set_activatable(False)
            self.local_row_suffix_img.set_from_icon_name("emblem-ok-symbolic")
            port = self.local_port_entry.get_text().strip() or "8080"
            self.local_row.set_subtitle(f"Configured on this computer (127.0.0.1:{port})")
        else:
            self.local_row.set_sensitive(True)
            self.local_row.set_activatable(True)
            self.local_row_suffix_img.set_from_icon_name("go-next-symbolic")
            self.local_row.set_subtitle("Manage torrents directly on this machine. Runs quietly in the background.")

        if not self.settings or not hasattr(self.settings, "get_instances"):
            return

        instances = self.settings.get_instances()
        is_completed = bool(self.settings.get("welcome_completed", False)) if self.settings else False
        if len(instances) > 0 and (self.configured_count > 0 or is_completed):
            for r in self.summary_rows:
                self.configured_instances_group.remove(r)
            self.summary_rows.clear()

            for inst in instances:
                is_local_inst = inst.get("local", False)
                icon = "computer-symbolic" if is_local_inst else "network-server-symbolic"
                row = Adw.ActionRow(
                    title=inst.get("name", "qBittorrent"),
                    subtitle=inst.get("host", f"{inst.get('host_ip')}:{inst.get('port')}")
                )
                row.add_prefix(Gtk.Image.new_from_icon_name(icon))
                row.add_suffix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
                self.summary_rows.append(row)
                self.configured_instances_group.add(row)

            self.configured_instances_group.set_visible(True)
            self.mode_finish_btn.set_visible(True)
            if is_completed:
                self.mode_finish_btn.set_label("Done")

    # ---------------- Page 1: Local Setup ----------------
    def _build_local_page(self):
        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        clamp = Adw.Clamp(maximum_size=520, margin_top=16, margin_bottom=24, margin_start=16, margin_end=16)
        scrolled.set_child(clamp)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(box)

        status_page = Adw.StatusPage(
            icon_name="computer-symbolic",
            title="Local Engine Setup",
            description="GTKittorrent can start and manage qBittorrent quietly in the background."
        )
        box.append(status_page)

        # Engine Inspection Group
        eng_group = Adw.PreferencesGroup(title="Background Engine")
        box.append(eng_group)

        # Binary Detected Row
        bin_info = self.daemon_mgr.get_binary_info()
        self.bin_row = Adw.ActionRow(title="Detected Engine")
        if bin_info["preferred"] == "qbittorrent-nox":
            self.bin_row.set_subtitle("qbittorrent-nox (Headless daemon)")
            self.bin_row.add_suffix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        elif bin_info["preferred"] == "qbittorrent":
            self.bin_row.set_subtitle("qbittorrent (Desktop app)")
            self.bin_row.add_suffix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
        else:
            self.bin_row.set_subtitle("Not found. Please install qbittorrent-nox or qbittorrent.")
            self.bin_row.add_suffix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
        eng_group.add(self.bin_row)

        # Recommendation for nox if only GUI is installed
        if bin_info["recommend_nox"]:
            tip_row = Adw.ActionRow(
                title="Recommended: qbittorrent-nox",
                subtitle="Install qbittorrent-nox for a 100% headless daemon without desktop windows."
            )
            tip_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            eng_group.add(tip_row)

        # Engine Status Row
        self.local_status_row = Adw.ActionRow(title="Service Status")
        self.local_status_spinner = Gtk.Spinner(valign=Gtk.Align.CENTER)
        self.local_status_lbl = Gtk.Label(label="Checking...", valign=Gtk.Align.CENTER, use_markup=True)
        self.local_status_row.add_suffix(self.local_status_spinner)
        self.local_status_row.add_suffix(self.local_status_lbl)
        eng_group.add(self.local_status_row)

        # Engine Control Button Row
        self.local_ctrl_row = Adw.ActionRow(title="Engine Control")
        self.local_start_btn = Gtk.Button(label="Start Background Engine", css_classes=["suggested-action"], valign=Gtk.Align.CENTER)
        self.local_start_btn.connect("clicked", self._on_start_local_engine_clicked)
        self.local_ctrl_row.add_suffix(self.local_start_btn)
        eng_group.add(self.local_ctrl_row)

        # Local Config / Advanced Expander
        self.local_expander = Adw.ExpanderRow(title="Local Connection Details")
        self.local_expander.set_subtitle("Default: 127.0.0.1:8080 (Auth bypassed for localhost)")
        eng_group.add(self.local_expander)

        default_port = str((self.settings.get("port") if self.settings else "8080") or "8080")
        self.local_port_entry = Adw.EntryRow(title="Port")
        self.local_port_entry.set_text(default_port)
        self.local_expander.add_row(self.local_port_entry)

        default_user = (self.settings.get("username") if self.settings else "admin") or "admin"
        self.local_username_entry = Adw.EntryRow(title="Username")
        self.local_username_entry.set_text(default_user)
        self.local_expander.add_row(self.local_username_entry)

        default_pass = (self.settings.get("password") if self.settings else "") or ""
        self.local_password_entry = Adw.PasswordEntryRow(title="Password")
        self.local_password_entry.set_text(default_pass)
        self.local_expander.add_row(self.local_password_entry)

        # Engine running confirmation banner
        self.local_success_banner = Adw.Banner(title="Local engine is active and ready.")
        self.local_success_banner.set_revealed(False)
        box.append(self.local_success_banner)

        # Local Action Buttons
        self.local_btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=8)
        box.append(self.local_btn_box)

        # 1. Save and Finish Setup
        self.local_connect_btn = Gtk.Button(
            label="Save and Finish Setup",
            css_classes=["suggested-action", "pill"],
            valign=Gtk.Align.CENTER
        )
        self.local_connect_btn.connect("clicked", lambda b: self._on_local_save_and_finish())
        self.local_btn_box.append(self.local_connect_btn)

        # 2. Save and Add Another Instance (navigates back to page 0)
        self.local_add_another_btn = Gtk.Button(
            label="Save and Add Another Instance",
            css_classes=["pill"],
            valign=Gtk.Align.CENTER
        )
        self.local_add_another_btn.connect("clicked", lambda b: self._on_local_save_and_add_another())
        self.local_btn_box.append(self.local_add_another_btn)

        return scrolled

    # ---------------- Page 2: Remote Setup ----------------
    def _build_remote_page(self):
        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        clamp = Adw.Clamp(maximum_size=520, margin_top=16, margin_bottom=24, margin_start=16, margin_end=16)
        scrolled.set_child(clamp)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(content_box)

        status_page = Adw.StatusPage(
            icon_name="network-server-symbolic",
            title="Remote Web UI Connection",
            description="Connect to qBittorrent running on a server, NAS, or seedbox."
        )
        content_box.append(status_page)

        group = Adw.PreferencesGroup(title="Connection Details")
        content_box.append(group)

        self.name_entry = Adw.EntryRow(title="Instance Name")
        self.name_entry.set_text("Server")
        if hasattr(self.name_entry, "set_placeholder_text"):
            self.name_entry.set_placeholder_text("Server")
        group.add(self.name_entry)

        self.host_entry = Adw.EntryRow(title="IP / Domain")
        self.host_entry.set_text((self.settings.get("host_ip") if self.settings else "127.0.0.1") or "127.0.0.1")
        group.add(self.host_entry)

        self.port_entry = Adw.EntryRow(title="Port")
        self.port_entry.set_text(str((self.settings.get("port") if self.settings else "8080") or "8080"))
        group.add(self.port_entry)

        self.username_entry = Adw.EntryRow(title="Username")
        self.username_entry.set_text((self.settings.get("username") if self.settings else "admin") or "admin")
        group.add(self.username_entry)

        self.password_entry = Adw.PasswordEntryRow(title="Password")
        self.password_entry.set_text((self.settings.get("password") if self.settings else "adminpassword") or "adminpassword")
        group.add(self.password_entry)

        self.https_row = Adw.ActionRow(title="Use HTTPS")
        self.https_switch = Gtk.Switch(active=bool(self.settings.get("use_https") if self.settings else False), valign=Gtk.Align.CENTER)
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

        # Action Buttons
        self.remote_btn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=8)
        content_box.append(self.remote_btn_box)

        # 1. Save and Finish Setup
        self.connect_btn = Gtk.Button(
            label="Save and Finish Setup",
            css_classes=["suggested-action", "pill"],
            valign=Gtk.Align.CENTER
        )
        self.connect_btn.connect("clicked", lambda b: self._on_remote_save_clicked(finish_after=True))
        self.remote_btn_box.append(self.connect_btn)

        # 2. Save and Add Another Instance
        self.remote_add_another_btn = Gtk.Button(
            label="Save and Add Another Instance",
            css_classes=["pill"],
            valign=Gtk.Align.CENTER
        )
        self.remote_add_another_btn.connect("clicked", lambda b: self._on_remote_save_clicked(finish_after=False))
        self.remote_btn_box.append(self.remote_add_another_btn)

        return scrolled

    # ---------------- Local Engine Logic ----------------
    def _refresh_local_engine_status(self):
        port = int(self.local_port_entry.get_text().strip() or "8080")
        self.local_status_spinner.start()

        def _check():
            is_running = self.daemon_mgr.is_engine_running("127.0.0.1", port)
            GLib.idle_add(self._on_local_engine_status_result, is_running, port)

        threading.Thread(target=_check, daemon=True).start()

    def _on_local_engine_status_result(self, is_running, port):
        self.local_status_spinner.stop()
        if is_running:
            self.local_status_lbl.set_markup(f"<span color='#2ec27e'><b>Running</b> (127.0.0.1:{port})</span>")
            self.local_start_btn.set_label("Restart Engine")
            self.local_start_btn.set_sensitive(True)
            self.local_success_banner.set_title(f"Local engine is running on port {port}.")
            self.local_success_banner.set_revealed(True)
        else:
            self.local_status_lbl.set_markup("<span color='#e01b24'><b>Stopped</b></span>")
            self.local_start_btn.set_label("Start Background Engine")
            self.local_start_btn.set_sensitive(True)
            self.local_success_banner.set_revealed(False)

    def _on_start_local_engine_clicked(self, btn):
        port = int(self.local_port_entry.get_text().strip() or "8080")
        self.local_start_btn.set_sensitive(False)
        self.local_status_spinner.start()
        self.local_status_lbl.set_markup("<i>Starting engine...</i>")
        self.local_success_banner.set_revealed(False)

        def _on_done(success, message):
            self.local_status_spinner.stop()
            self.local_start_btn.set_sensitive(True)
            if success:
                self.local_status_lbl.set_markup(f"<span color='#2ec27e'><b>Running</b> (127.0.0.1:{port})</span>")
                self.local_start_btn.set_label("Restart Engine")
                self.local_success_banner.set_title(f"Local engine started successfully on port {port}!")
                self.local_success_banner.set_revealed(True)
                self.local_configured = True
                self.configured_count += 1
                self._save_local_instance()
            else:
                self.local_status_lbl.set_markup(f"<span color='#e01b24'><b>Failed:</b> {message}</span>")

        self.daemon_mgr.start_daemon_async(port=port, callback=_on_done)

    def _save_local_instance(self):
        port = self.local_port_entry.get_text().strip() or "8080"
        user = self.local_username_entry.get_text().strip() or "admin"
        pw = self.local_password_entry.get_text().strip()
        full_host = f"http://127.0.0.1:{port}"

        if self.settings:
            local_inst = self.settings.get_local_instance() if hasattr(self.settings, "get_local_instance") else None
            if local_inst:
                self.settings.update_instance(
                    local_inst["id"],
                    name="Local qBittorrent",
                    host_ip="127.0.0.1",
                    port=port,
                    username=user,
                    password=pw,
                    use_https=False,
                    local=True
                )
            elif hasattr(self.settings, "add_instance"):
                self.settings.add_instance(
                    "Local qBittorrent",
                    "127.0.0.1",
                    port,
                    user,
                    pw,
                    use_https=False,
                    local=True,
                    make_active=True
                )
            self.settings.set("name", "Local qBittorrent")
            self.settings.set("host_ip", "127.0.0.1")
            self.settings.set("port", port)
            self.settings.set("username", user)
            self.settings.set("password", pw)
            self.settings.set("use_https", False)
            self.settings.set("host", full_host)

        if self.client:
            self.client.update_settings(full_host, user, pw)

        self.local_configured = True

    def _on_local_save_and_finish(self):
        self._save_local_instance()
        self.configured_count += 1
        self._finish_and_open()

    def _on_local_save_and_add_another(self):
        self._save_local_instance()
        self.configured_count += 1
        self._go_to_page(0)

    # ---------------- Remote Engine Logic ----------------
    def _on_remote_save_clicked(self, finish_after=True):
        host_ip, port, username, password, use_https, full_host = self._get_form_values()
        name = self.name_entry.get_text().strip() or "Server"

        self.connect_btn.set_sensitive(False)
        self.remote_add_another_btn.set_sensitive(False)
        self.test_spinner.start()
        self.feedback_box.set_visible(False)

        def worker():
            from ..client.client import QBittorrentClient
            success, message, _ = QBittorrentClient.test_connection_params(full_host, username, password)
            GLib.idle_add(self._on_remote_save_result, success, message, name, host_ip, port, username, password, use_https, full_host, finish_after)

        threading.Thread(target=worker, daemon=True).start()

    def _on_remote_save_result(self, success, message, name, host_ip, port, username, password, use_https, full_host, finish_after):
        self.test_spinner.stop()
        self.connect_btn.set_sensitive(True)
        self.remote_add_another_btn.set_sensitive(True)

        if success:
            if self.settings and hasattr(self.settings, "add_instance"):
                self.settings.add_instance(name, host_ip, port, username, password, use_https=use_https, local=False, make_active=True)
            self.configured_count += 1

            if finish_after:
                self._finish_and_open()
            else:
                # Reset remote fields to clean "Server" default
                self.name_entry.set_text("Server")
                self.host_entry.set_text("")
                self.port_entry.set_text("8080")
                self.username_entry.set_text("admin")
                self.password_entry.set_text("")
                self.https_switch.set_active(False)
                self.feedback_box.set_visible(False)
                # Go back to page 0
                self._go_to_page(0)
        else:
            self.feedback_box.set_visible(True)
            self.feedback_icon.set_from_icon_name("dialog-error-symbolic")
            self.feedback_lbl.set_markup(f"<span color='#e01b24'><b>Failed to connect:</b> {message}</span>")

    # ---------------- Finish and Launch Flow ----------------
    def _finish_and_open(self):
        if self.settings:
            self.settings.set("welcome_completed", True)
            self.settings.set("configured", True)

        if self.client:
            self.client.connect()

        self.emit("connected")
        self.close()

    # ---------------- Common Form & Backward Compatibility Methods ----------------
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
        name = self.name_entry.get_text().strip() or ("Local qBittorrent" if host_ip in ("127.0.0.1", "localhost") else "Server")

        if self.settings:
            self.settings.set("name", name)
            self.settings.set("host_ip", host_ip)
            self.settings.set("port", port)
            self.settings.set("username", username)
            self.settings.set("password", password)
            self.settings.set("use_https", use_https)
            self.settings.set("host", full_host)
            self.settings.set("configured", True)
            self.settings.set("welcome_completed", True)

        if self.client:
            self.client.update_settings(full_host, username, password)

    def _on_connect_clicked(self, btn):
        self._on_remote_save_clicked(finish_after=True)

    def _on_connect_anyway_clicked(self, btn=None):
        self._save_and_apply()
        self.emit("connected")
        self.close()
