import threading
import time
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, GLib, Adw, Gio, Gdk

class PreferencesDialog(Adw.PreferencesWindow):
    """Preferences dialog matching some of qBittorrent's options."""

    def __init__(self, parent, settings, client):
        super().__init__(transient_for=parent, modal=True)
        self.set_title("Preferences")
        self.set_default_size(680, 620)
        self.settings = settings
        self.client = client
        self.qb_prefs = self.client.get_app_preferences() if self.client else {}

        self._setup_behaviour_page()
        self._setup_downloads_page()
        self._setup_connection_page()
        self._setup_speed_page()
        self._setup_bittorrent_page()

        self.connect("close-request", self._on_close)

    def _setup_behaviour_page(self):
        page = Adw.PreferencesPage(title="Behaviour", icon_name="preferences-system-symbolic")
        self.add(page)

        self._setup_theme_group(page)

        group = Adw.PreferencesGroup(title="qBittorrent Web UI Server")
        page.add(group)

        self.name_entry = Adw.EntryRow(title="Instance Name")
        curr_inst = self.settings.get_current_instance() if hasattr(self.settings, "get_current_instance") else {}
        if not isinstance(curr_inst, dict):
            curr_inst = {}
        inst_name = curr_inst.get("name") or (self.settings.get("name") if self.settings else "Local qBittorrent") or "Local qBittorrent"
        self.name_entry.set_text(inst_name)
        group.add(self.name_entry)

        self.host_entry = Adw.EntryRow(title="IP / Domain")
        self.host_entry.set_text(curr_inst.get("host_ip") or (self.settings.get("host_ip") if self.settings else "127.0.0.1") or "127.0.0.1")
        group.add(self.host_entry)

        self.port_entry = Adw.EntryRow(title="Port")
        self.port_entry.set_text(str(curr_inst.get("port") or (self.settings.get("port") if self.settings else "8080") or "8080"))
        group.add(self.port_entry)

        self.username_entry = Adw.EntryRow(title="Username")
        self.username_entry.set_text(curr_inst.get("username") or (self.settings.get("username") if self.settings else "admin") or "admin")
        group.add(self.username_entry)

        self.password_entry = Adw.PasswordEntryRow(title="Password")
        default_pw = curr_inst.get("password") if "password" in curr_inst else (self.settings.get("password") if self.settings else "")
        self.password_entry.set_text(default_pw or "")
        group.add(self.password_entry)

        self.https_row = Adw.ActionRow(title="Use HTTPS")
        is_https = curr_inst.get("use_https") if "use_https" in curr_inst else (self.settings.get("use_https") if self.settings else False)
        self.https_switch = Gtk.Switch(active=bool(is_https), valign=Gtk.Align.CENTER)
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

        # Local Background Engine Group
        from ...client.daemon import LocalDaemonManager
        self.daemon_mgr = LocalDaemonManager.get_instance()
        bin_info = self.daemon_mgr.get_binary_info()

        self.engine_group = Adw.PreferencesGroup(title="Local Background Engine")
        page.add(self.engine_group)

        self.engine_binary_row = Adw.ActionRow(title="Engine Binary")
        if bin_info["preferred"] == "qbittorrent-nox":
            self.engine_binary_row.set_subtitle("qbittorrent-nox (Headless daemon)")
            self.engine_binary_row.add_suffix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        elif bin_info["preferred"] == "qbittorrent":
            self.engine_binary_row.set_subtitle("qbittorrent (Desktop app)")
            self.engine_binary_row.add_suffix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
        else:
            self.engine_binary_row.set_subtitle("Not found. Please install qbittorrent-nox or qbittorrent.")
            self.engine_binary_row.add_suffix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
        self.engine_group.add(self.engine_binary_row)

        if bin_info.get("recommend_nox"):
            tip_row = Adw.ActionRow(
                title="Recommended: qbittorrent-nox",
                subtitle="Install qbittorrent-nox for a pure headless daemon without desktop windows."
            )
            tip_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            self.engine_group.add(tip_row)

        # Service Control Row (Start / Stop / Restart buttons)
        self.engine_control_row = Adw.ActionRow(
            title="Service Control",
            subtitle="Checking engine status…"
        )
        self.engine_group.add(self.engine_control_row)

        self.engine_status_spinner = Gtk.Spinner(valign=Gtk.Align.CENTER)
        self.engine_control_row.add_suffix(self.engine_status_spinner)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, valign=Gtk.Align.CENTER)
        self.engine_control_row.add_suffix(btn_box)

        self.engine_start_btn = Gtk.Button(valign=Gtk.Align.CENTER, tooltip_text="Start local background engine")
        start_child = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        start_child.append(Gtk.Image.new_from_icon_name("media-playback-start-symbolic"))
        start_child.append(Gtk.Label(label="Start"))
        self.engine_start_btn.set_child(start_child)
        self.engine_start_btn.connect("clicked", self._on_engine_start_clicked)
        btn_box.append(self.engine_start_btn)

        self.engine_stop_btn = Gtk.Button(valign=Gtk.Align.CENTER, tooltip_text="Stop local background engine")
        stop_child = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        stop_child.append(Gtk.Image.new_from_icon_name("media-playback-stop-symbolic"))
        stop_child.append(Gtk.Label(label="Stop"))
        self.engine_stop_btn.set_child(stop_child)
        self.engine_stop_btn.connect("clicked", self._on_engine_stop_clicked)
        btn_box.append(self.engine_stop_btn)

        self.engine_restart_btn = Gtk.Button(valign=Gtk.Align.CENTER, tooltip_text="Restart local background engine")
        restart_child = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        restart_child.append(Gtk.Image.new_from_icon_name("view-refresh-symbolic"))
        restart_child.append(Gtk.Label(label="Restart"))
        self.engine_restart_btn.set_child(restart_child)
        self.engine_restart_btn.connect("clicked", self._on_engine_restart_clicked)
        btn_box.append(self.engine_restart_btn)

        self.engine_autostart_row = Adw.ActionRow(
            title="Start Engine on Launch",
            subtitle="Automatically launch local qBittorrent when opening GTKittorrent"
        )
        self.engine_autostart_switch = Gtk.Switch(
            active=bool(self.settings.get("engine_autostart", True) if self.settings else True),
            valign=Gtk.Align.CENTER
        )
        self.engine_autostart_row.add_suffix(self.engine_autostart_switch)
        self.engine_group.add(self.engine_autostart_row)

        self.engine_stop_on_exit_row = Adw.ActionRow(
            title="Stop Engine on Exit",
            subtitle="When disabled, torrents continue downloading and seeding in the background"
        )
        self.engine_stop_on_exit_switch = Gtk.Switch(
            active=bool(self.settings.get("engine_stop_on_exit", False) if self.settings else False),
            valign=Gtk.Align.CENTER
        )
        self.engine_stop_on_exit_row.add_suffix(self.engine_stop_on_exit_switch)
        self.engine_group.add(self.engine_stop_on_exit_row)

        # Apply visibility (hidden if not a local instance) and Flatpak restrictions
        is_local = self._is_local_instance()
        is_flatpak = self._is_flatpak()

        if not is_local:
            self.engine_group.set_visible(False)
        else:
            self.engine_group.set_visible(True)
            if is_flatpak:
                self.engine_group.set_description("Local background engine management is not available in Flatpak.")
                self.engine_binary_row.set_subtitle("Not available in Flatpak")
                self.engine_binary_row.set_sensitive(False)
                self.engine_control_row.set_subtitle("Not available in Flatpak")
                self.engine_control_row.set_sensitive(False)
                self.engine_start_btn.set_sensitive(False)
                self.engine_stop_btn.set_sensitive(False)
                self.engine_restart_btn.set_sensitive(False)
                self.engine_autostart_row.set_subtitle("Not available in Flatpak")
                self.engine_autostart_row.set_sensitive(False)
                self.engine_autostart_switch.set_sensitive(False)
                self.engine_stop_on_exit_row.set_subtitle("Not available in Flatpak")
                self.engine_stop_on_exit_row.set_sensitive(False)
                self.engine_stop_on_exit_switch.set_sensitive(False)
            else:
                self._check_engine_status()

    @staticmethod
    def _clamp(value, lo, hi):
        try:
            return max(lo, min(hi, int(value)))
        except (TypeError, ValueError):
            return lo

    def _switch_row(self, group, title, active, subtitle=None):
        row = Adw.ActionRow(title=title)
        if subtitle:
            row.set_subtitle(subtitle)
        switch = Gtk.Switch(active=bool(active), valign=Gtk.Align.CENTER)
        row.add_suffix(switch)
        row.set_activatable_widget(switch)
        group.add(row)
        return row, switch

    def _spin_row(self, group, title, value, lower, upper, step=1, subtitle=None):
        row = Adw.SpinRow(
            title=title,
            adjustment=Gtk.Adjustment(lower=lower, upper=upper, step_increment=step, page_increment=step * 10)
        )
        if subtitle:
            row.set_subtitle(subtitle)
        row.set_value(value)
        group.add(row)
        return row

    def _is_qbt5(self):
        """qBittorrent 5.x renamed several preference keys."""
        return "add_stopped_enabled" in self.qb_prefs or "category_changed_tmm_enabled" in self.qb_prefs

    _THEME_CSS = b"""
    checkbutton.theme-selector {
        padding: 0;
        min-height: 44px;
        min-width: 44px;
        padding: 1px;
        background-clip: content-box;
        border-radius: 9999px;
        box-shadow: inset 0 0 0 1px @borders;
    }
    checkbutton.theme-selector:checked {
        box-shadow: inset 0 0 0 2px @accent_bg_color;
    }
    checkbutton.theme-selector radio {
        -gtk-icon-source: none;
        border: none;
        background: none;
        box-shadow: none;
        min-width: 12px;
        min-height: 12px;
        transform: translate(27px, 14px);
        padding: 2px;
    }
    checkbutton.theme-selector radio:checked {
        -gtk-icon-source: -gtk-icontheme("object-select-symbolic");
        background-color: @accent_bg_color;
        color: @accent_fg_color;
    }
    checkbutton.theme-selector.follow {
        background-image: linear-gradient(to bottom right, #ffffff 49.99%, #202020 50.01%);
    }
    checkbutton.theme-selector.light {
        background-color: #ffffff;
    }
    checkbutton.theme-selector.dark {
        background-color: #202020;
    }
    """

    def _setup_theme_group(self, page):
        display = Gdk.Display.get_default()
        if display:
            provider = Gtk.CssProvider()
            provider.load_from_data(self._THEME_CSS)
            Gtk.StyleContext.add_provider_for_display(
                display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )

        group = Adw.PreferencesGroup(title="Appearance")
        page.add(group)

        row = Adw.ActionRow(title="Style", subtitle="Choose between system, light and dark appearance")
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, valign=Gtk.Align.CENTER)
        row.add_suffix(box)

        current = self.settings.get("theme", "system") if self.settings else "system"
        self.theme_buttons = {}
        group_btn = None
        for key, css, tip in (
            ("system", "follow", "Follow System Style"),
            ("light", "light", "Light Style"),
            ("dark", "dark", "Dark Style"),
        ):
            btn = Gtk.CheckButton(tooltip_text=tip, css_classes=["theme-selector", css])
            if group_btn is None:
                group_btn = btn
            else:
                btn.set_group(group_btn)
            btn.set_active(key == current)
            btn.connect("toggled", self._on_theme_toggled, key)
            box.append(btn)
            self.theme_buttons[key] = btn
        group.add(row)

    def _on_theme_toggled(self, btn, key):
        if not btn.get_active():
            return
        if self.settings:
            self.settings.set("theme", key)
        from ...settings import apply_theme
        apply_theme(key)

    def _setup_connection_page(self):
        page = Adw.PreferencesPage(title="Connection", icon_name="network-workgroup-symbolic")
        self.add(page)

        conn_group = Adw.PreferencesGroup(title="Listening Port &amp; Limits")
        page.add(conn_group)

        self.protocol_row = Adw.ComboRow(
            title="Peer Connection Protocol",
            model=Gtk.StringList.new(["TCP and μTP", "TCP", "μTP"])
        )
        self.protocol_row.set_selected(self._clamp(self.qb_prefs.get("bittorrent_protocol", 0), 0, 2))
        conn_group.add(self.protocol_row)

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

        limits_group = Adw.PreferencesGroup(
            title="Connection Limits",
            description="Use 0 for unlimited."
        )
        page.add(limits_group)

        def spin(title, key, default, upper=65535):
            row = Adw.SpinRow(
                title=title,
                adjustment=Gtk.Adjustment(lower=0, upper=upper, step_increment=1, page_increment=10)
            )
            val = self.qb_prefs.get(key, default)
            row.set_value(val if isinstance(val, (int, float)) and val > 0 else 0)
            limits_group.add(row)
            return row

        self.max_connec_row = spin("Global Maximum Connections", "max_connec", 500)
        self.max_connec_per_torrent_row = spin("Maximum Connections per Torrent", "max_connec_per_torrent", 100)
        self.max_uploads_row = spin("Global Maximum Upload Slots", "max_uploads", 20)
        self.max_uploads_per_torrent_row = spin("Maximum Upload Slots per Torrent", "max_uploads_per_torrent", 4)

    def _setup_downloads_page(self):
        page = Adw.PreferencesPage(title="Downloads", icon_name="folder-download-symbolic")
        self.add(page)

        group = Adw.PreferencesGroup(title="Default Save Path")
        page.add(group)

        self.save_path_entry = Adw.EntryRow(title="Save files to location")
        self.save_path_entry.set_text(self.qb_prefs.get("save_path", ""))
        self.save_path_browse_btn = Gtk.Button(
            icon_name="folder-open-symbolic",
            valign=Gtk.Align.CENTER,
            tooltip_text="Browse for save directory...",
            css_classes=["flat"]
        )
        self.save_path_browse_btn.connect(
            "clicked",
            lambda b: self._on_browse_directory(self.save_path_entry, "Select Save Directory")
        )
        self.save_path_entry.add_suffix(self.save_path_browse_btn)
        group.add(self.save_path_entry)

        self.temp_path_enabled_row = Adw.ActionRow(title="Keep incomplete torrents in separate location")
        self.temp_path_switch = Gtk.Switch(
            active=bool(self.qb_prefs.get("temp_path_enabled", False)),
            valign=Gtk.Align.CENTER
        )
        self.temp_path_enabled_row.add_suffix(self.temp_path_switch)
        self.temp_path_enabled_row.set_activatable_widget(self.temp_path_switch)
        group.add(self.temp_path_enabled_row)

        self.temp_path_entry = Adw.EntryRow(title="Incomplete files location")
        self.temp_path_entry.set_text(self.qb_prefs.get("temp_path", ""))
        self.temp_path_browse_btn = Gtk.Button(
            icon_name="folder-open-symbolic",
            valign=Gtk.Align.CENTER,
            tooltip_text="Browse for incomplete files directory...",
            css_classes=["flat"]
        )
        self.temp_path_browse_btn.connect(
            "clicked",
            lambda b: self._on_browse_directory(self.temp_path_entry, "Select Incomplete Files Directory")
        )
        self.temp_path_entry.add_suffix(self.temp_path_browse_btn)
        group.add(self.temp_path_entry)

        # Grey out incomplete files location if separate incomplete location is not checked
        self.temp_path_switch.connect("notify::active", self._on_temp_path_toggled)
        self._on_temp_path_toggled(self.temp_path_switch)

        add_group = Adw.PreferencesGroup(title="When Adding a Torrent")
        page.add(add_group)

        self.content_layout_row = Adw.ComboRow(
            title="Torrent Content Layout",
            model=Gtk.StringList.new(["Original", "Create subfolder", "Don't create subfolder"])
        )
        self.CONTENT_LAYOUTS = ["Original", "Subfolder", "NoSubfolder"]
        layout = self.qb_prefs.get("torrent_content_layout", "Original")
        self.content_layout_row.set_selected(
            self.CONTENT_LAYOUTS.index(layout) if layout in self.CONTENT_LAYOUTS else 0
        )
        add_group.add(self.content_layout_row)

        _, self.add_top_switch = self._switch_row(
            add_group, "Add to top of queue", self.qb_prefs.get("add_to_top_of_queue", False))
        stopped = self.qb_prefs.get("add_stopped_enabled", self.qb_prefs.get("start_paused_enabled", False))
        _, self.add_stopped_switch = self._switch_row(
            add_group, "Do not start the download automatically", stopped)

        tmm_group = Adw.PreferencesGroup(title="Saving Management")
        page.add(tmm_group)

        self.tmm_mode_row = Adw.ComboRow(
            title="Default Torrent Management Mode",
            model=Gtk.StringList.new(["Manual", "Automatic"])
        )
        self.tmm_mode_row.set_selected(1 if self.qb_prefs.get("auto_tmm_enabled", False) else 0)
        tmm_group.add(self.tmm_mode_row)

        self.CATEGORY_CHANGED_OPTIONS = ["Switch affected torrents to Manual Mode", "Relocate affected torrents"]
        self.category_changed_row = Adw.ComboRow(
            title="When Torrent Category Changed",
            model=Gtk.StringList.new(self.CATEGORY_CHANGED_OPTIONS)
        )
        relocate = self.qb_prefs.get("category_changed_tmm_enabled", self.qb_prefs.get("torrent_changed_tmm_enabled", True))
        self.category_changed_row.set_selected(1 if relocate else 0)
        tmm_group.add(self.category_changed_row)

        excl_group = Adw.PreferencesGroup(
            title="Excluded File Names",
            description="Files matching these patterns are not downloaded. One glob per line, e.g. *.exe or sample?.mkv"
        )
        page.add(excl_group)

        _, self.excluded_switch = self._switch_row(
            excl_group, "Enable excluded file names", self.qb_prefs.get("excluded_file_names_enabled", False))
        self.excluded_view = Gtk.TextView(
            wrap_mode=Gtk.WrapMode.NONE, monospace=True, top_margin=8, bottom_margin=8,
            left_margin=8, right_margin=8
        )
        self.excluded_view.get_buffer().set_text(self.qb_prefs.get("excluded_file_names", "") or "")
        scroller = Gtk.ScrolledWindow(min_content_height=110, css_classes=["card"])
        scroller.set_child(self.excluded_view)
        excl_group.add(scroller)
        self.excluded_switch.connect("notify::active", lambda sw, *a: scroller.set_sensitive(sw.get_active()))
        scroller.set_sensitive(self.excluded_switch.get_active())

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

        sched_group = Adw.PreferencesGroup(title="Scheduler")
        page.add(sched_group)

        _, self.scheduler_switch = self._switch_row(
            sched_group, "Schedule the use of alternative rate limits",
            self.qb_prefs.get("scheduler_enabled", False))

        self.sched_from_row = self._time_row(
            sched_group, "From",
            self.qb_prefs.get("schedule_from_hour", 0), self.qb_prefs.get("schedule_from_min", 0))
        self.sched_to_row = self._time_row(
            sched_group, "To",
            self.qb_prefs.get("schedule_to_hour", 0), self.qb_prefs.get("schedule_to_min", 0))

        self.sched_days_row = Adw.ComboRow(
            title="When",
            model=Gtk.StringList.new([
                "Every day", "Weekdays", "Weekends", "Monday", "Tuesday",
                "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"
            ])
        )
        self.sched_days_row.set_selected(self._clamp(self.qb_prefs.get("scheduler_days", 0), 0, 9))
        sched_group.add(self.sched_days_row)

        def update_sched(*_):
            on = self.scheduler_switch.get_active()
            for r in (self.sched_from_row, self.sched_to_row, self.sched_days_row):
                r.set_sensitive(on)
        self.scheduler_switch.connect("notify::active", update_sched)
        update_sched()

    def _time_row(self, group, title, hour, minute):
        """Row with hour and minute spin buttons. Returns the row with .hour/.minute spins attached."""
        row = Adw.ActionRow(title=title)
        hour_spin = Gtk.SpinButton(
            adjustment=Gtk.Adjustment(lower=0, upper=23, step_increment=1, page_increment=6),
            valign=Gtk.Align.CENTER, orientation=Gtk.Orientation.HORIZONTAL, width_chars=2
        )
        min_spin = Gtk.SpinButton(
            adjustment=Gtk.Adjustment(lower=0, upper=59, step_increment=1, page_increment=10),
            valign=Gtk.Align.CENTER, width_chars=2
        )
        hour_spin.set_value(self._clamp(hour, 0, 23))
        min_spin.set_value(self._clamp(minute, 0, 59))
        for sp_ in (hour_spin, min_spin):
            sp_.set_numeric(True)
            sp_.connect("output", lambda w: (w.set_text(f"{int(w.get_value()):02d}"), True)[1])
        row.add_suffix(hour_spin)
        row.add_suffix(Gtk.Label(label=":"))
        row.add_suffix(min_spin)
        row.hour_spin = hour_spin
        row.min_spin = min_spin
        group.add(row)
        return row

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

        self.encryption_row = Adw.ComboRow(
            title="Encryption Mode",
            model=Gtk.StringList.new(["Allow encryption", "Require encryption", "Disable encryption"])
        )
        self.encryption_row.set_selected(self._clamp(self.qb_prefs.get("encryption", 0), 0, 2))
        privacy_group.add(self.encryption_row)

        _, self.anonymous_switch = self._switch_row(
            privacy_group, "Enable anonymous mode",
            self.qb_prefs.get("anonymous_mode", False),
            "Hides client identification from peers and trackers")

        limits_group = Adw.PreferencesGroup(title="Seeding Limits")
        page.add(limits_group)

        _, self.ratio_switch = self._switch_row(
            limits_group, "Share ratio limit", self.qb_prefs.get("max_ratio_enabled", False))
        ratio = self.qb_prefs.get("max_ratio", 1.0)
        self.ratio_row = Adw.SpinRow(
            title="When ratio reaches",
            adjustment=Gtk.Adjustment(lower=0, upper=9999, step_increment=0.05, page_increment=1),
            digits=2
        )
        self.ratio_row.set_value(ratio if isinstance(ratio, (int, float)) and ratio >= 0 else 1.0)
        limits_group.add(self.ratio_row)

        _, self.seed_time_switch = self._switch_row(
            limits_group, "Seeding time limit", self.qb_prefs.get("max_seeding_time_enabled", False))
        self.seed_time_row = self._spin_row(
            limits_group, "When seeding time reaches (minutes)",
            max(0, self.qb_prefs.get("max_seeding_time", 1440) or 0), 0, 525600, 10)

        _, self.inactive_time_switch = self._switch_row(
            limits_group, "Inactive seeding time limit",
            self.qb_prefs.get("max_inactive_seeding_time_enabled", False))
        self.inactive_time_row = self._spin_row(
            limits_group, "When inactive seeding time reaches (minutes)",
            max(0, self.qb_prefs.get("max_inactive_seeding_time", 1440) or 0), 0, 525600, 10)

        for sw, row in (
            (self.ratio_switch, self.ratio_row),
            (self.seed_time_switch, self.seed_time_row),
            (self.inactive_time_switch, self.inactive_time_row),
        ):
            sw.connect("notify::active", lambda s, *a, r=row: r.set_sensitive(s.get_active()))
            row.set_sensitive(sw.get_active())

        self.share_mode_row = Adw.ComboRow(
            title="Limit applies when",
            model=Gtk.StringList.new(["Any of the above is reached", "All of the above are reached"])
        )
        mode = self.qb_prefs.get("share_limits_mode", 0)
        self.share_mode_row.set_selected(1 if mode in (1, "MatchAll") else 0)
        self.share_mode_row.set_visible(not self.qb_prefs or "share_limits_mode" in self.qb_prefs)
        limits_group.add(self.share_mode_row)

        # max_ratio_act values differ between qBittorrent 4.x and 5.x
        if self._is_qbt5():
            self.SHARE_ACTIONS = [("Stop torrent", 0), ("Remove torrent", 1),
                                  ("Remove torrent and its files", 3), ("Enable super seeding", 2)]
        else:
            self.SHARE_ACTIONS = [("Pause torrent", 0), ("Remove torrent", 1),
                                  ("Remove torrent and its files", 3), ("Enable super seeding", 2)]
        self.share_action_row = Adw.ComboRow(
            title="Then",
            model=Gtk.StringList.new([n for n, _ in self.SHARE_ACTIONS])
        )
        cur_act = self.qb_prefs.get("max_ratio_act", 0)
        for i, (_, v) in enumerate(self.SHARE_ACTIONS):
            if v == cur_act:
                self.share_action_row.set_selected(i)
        limits_group.add(self.share_action_row)

        trackers_group = Adw.PreferencesGroup(
            title="Trackers",
        )
        page.add(trackers_group)
        _, self.add_trackers_switch = self._switch_row(
            trackers_group, "Automatically append these trackers to new downloads",
            self.qb_prefs.get("add_trackers_enabled", False))
        self.add_trackers_view = Gtk.TextView(
            wrap_mode=Gtk.WrapMode.NONE, monospace=True, top_margin=8, bottom_margin=8,
            left_margin=8, right_margin=8
        )
        self.add_trackers_view.get_buffer().set_text(self.qb_prefs.get("add_trackers", "") or "")
        trk_scroller = Gtk.ScrolledWindow(min_content_height=110, css_classes=["card"])
        trk_scroller.set_child(self.add_trackers_view)
        trackers_group.add(trk_scroller)
        trackers_group.set_description("One tracker URL per line.")
        self.add_trackers_switch.connect("notify::active", lambda sw, *a: trk_scroller.set_sensitive(sw.get_active()))
        trk_scroller.set_sensitive(self.add_trackers_switch.get_active())

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

    def _on_temp_path_toggled(self, switch, *args):
        self.temp_path_entry.set_sensitive(switch.get_active())

    def _on_browse_directory(self, entry_widget, title="Select Directory"):
        dialog = Gtk.FileChooserNative(
            title=title,
            transient_for=self,
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            accept_label="_Select",
            cancel_label="_Cancel"
        )
        current_path = entry_widget.get_text().strip()
        if current_path:
            try:
                f = Gio.File.new_for_path(current_path)
                dialog.set_current_folder(f)
            except Exception:
                pass

        def on_resp(d, resp):
            if resp == Gtk.ResponseType.ACCEPT:
                selected_file = d.get_file()
                if selected_file:
                    path = selected_file.get_path()
                    if path:
                        entry_widget.set_text(path)
            d.destroy()

        dialog.connect("response", on_resp)
        dialog.show()

    def _get_local_port(self):
        try:
            return int(self.port_entry.get_text().strip())
        except (ValueError, AttributeError, TypeError):
            try:
                return int(self.settings.get("port") or 8080)
            except (ValueError, TypeError):
                return 8080

    def _is_local_instance(self):
        if not self.settings:
            return False
        if hasattr(self.settings, "is_current_local"):
            val = self.settings.is_current_local()
            if isinstance(val, bool):
                return val
        curr = self.settings.get_current_instance() if hasattr(self.settings, "get_current_instance") else None
        if isinstance(curr, dict):
            return bool(curr.get("local", False))
        return self.settings.get("host_ip") in ("127.0.0.1", "localhost", "::1")

    def _is_flatpak(self):
        if self.settings and hasattr(self.settings, "is_flatpak"):
            val = self.settings.is_flatpak()
            if isinstance(val, bool):
                return val
        import os
        return os.path.exists("/.flatpak-info") or bool(os.environ.get("FLATPAK_ID"))

    def _check_engine_status(self):
        port = self._get_local_port()
        self.engine_status_spinner.start()

        def worker():
            is_running = self.daemon_mgr.is_engine_running("127.0.0.1", port)
            GLib.idle_add(self._update_engine_status_ui, is_running, port)

        threading.Thread(target=worker, daemon=True).start()

    def _update_engine_status_ui(self, is_running, port):
        self.engine_status_spinner.stop()
        if self._is_flatpak():
            self.engine_start_btn.set_sensitive(False)
            self.engine_stop_btn.set_sensitive(False)
            self.engine_restart_btn.set_sensitive(False)
            self.engine_control_row.set_subtitle("Not available in Flatpak")
            return

        self.engine_start_btn.set_sensitive(not is_running)
        self.engine_stop_btn.set_sensitive(is_running)
        self.engine_restart_btn.set_sensitive(True)
        if is_running:
            self.engine_control_row.set_subtitle(f"Running (127.0.0.1:{port})")
        else:
            self.engine_control_row.set_subtitle("Stopped")

    def _on_engine_start_clicked(self, btn):
        port = self._get_local_port()
        self.engine_start_btn.set_sensitive(False)
        self.engine_stop_btn.set_sensitive(False)
        self.engine_restart_btn.set_sensitive(False)
        self.engine_control_row.set_subtitle("Starting engine…")
        self.engine_status_spinner.start()

        def on_done(success, msg):
            self._update_engine_status_ui(success, port)
            if success and self.client:
                self.client.connect()

        self.daemon_mgr.start_daemon_async(port=port, callback=on_done)

    def _on_engine_stop_clicked(self, btn):
        port = self._get_local_port()
        self.engine_start_btn.set_sensitive(False)
        self.engine_stop_btn.set_sensitive(False)
        self.engine_restart_btn.set_sensitive(False)
        self.engine_control_row.set_subtitle("Stopping engine…")
        self.engine_status_spinner.start()

        def stop_worker():
            self.daemon_mgr.stop_daemon(self.client)
            time.sleep(1.0)
            is_running = self.daemon_mgr.is_engine_running("127.0.0.1", port)
            GLib.idle_add(self._update_engine_status_ui, is_running, port)

        threading.Thread(target=stop_worker, daemon=True).start()

    def _on_engine_restart_clicked(self, btn):
        port = self._get_local_port()
        self.engine_start_btn.set_sensitive(False)
        self.engine_stop_btn.set_sensitive(False)
        self.engine_restart_btn.set_sensitive(False)
        self.engine_control_row.set_subtitle("Restarting engine…")
        self.engine_status_spinner.start()

        def on_done(success, msg):
            self._update_engine_status_ui(success, port)
            if success and self.client:
                self.client.connect()

        self.daemon_mgr.restart_daemon_async(port=port, client=self.client, callback=on_done)

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

        name = self.name_entry.get_text().strip() if hasattr(self, "name_entry") else "Local qBittorrent"
        if not name:
            name = "Local qBittorrent"

        if hasattr(self.settings, "get_current_instance") and hasattr(self.settings, "update_instance"):
            curr_inst = self.settings.get_current_instance()
            if curr_inst and "id" in curr_inst:
                is_local = host_ip in ("127.0.0.1", "localhost", "::1")
                self.settings.update_instance(
                    curr_inst["id"],
                    name=name,
                    host_ip=host_ip,
                    port=port,
                    username=username,
                    password=password,
                    use_https=use_https,
                    local=is_local
                )
        else:
            self.settings.set("name", name)
            self.settings.set("host_ip", host_ip)
            self.settings.set("port", port)
            self.settings.set("username", username)
            self.settings.set("password", password)
            self.settings.set("use_https", use_https)

        protocol = "https" if use_https else "http"
        full_host = f"{protocol}://{host_ip}:{port}"
        self.settings.set("host", full_host)

        if hasattr(self, "engine_autostart_switch"):
            self.settings.set("engine_autostart", self.engine_autostart_switch.get_active())
        if hasattr(self, "engine_stop_on_exit_switch"):
            self.settings.set("engine_stop_on_exit", self.engine_stop_on_exit_switch.get_active())

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
            def text_of(view):
                buf = view.get_buffer()
                return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False).strip()

            q5 = self._is_qbt5()
            new_qb_prefs.update({
                "bittorrent_protocol": self.protocol_row.get_selected(),
                "max_connec_per_torrent": int(self.max_connec_per_torrent_row.get_value()) or -1,
                "max_uploads": int(self.max_uploads_row.get_value()) or -1,
                "max_uploads_per_torrent": int(self.max_uploads_per_torrent_row.get_value()) or -1,
                "torrent_content_layout": self.CONTENT_LAYOUTS[self.content_layout_row.get_selected()],
                "add_to_top_of_queue": self.add_top_switch.get_active(),
                "auto_tmm_enabled": self.tmm_mode_row.get_selected() == 1,
                "excluded_file_names_enabled": self.excluded_switch.get_active(),
                "excluded_file_names": text_of(self.excluded_view),
                "scheduler_enabled": self.scheduler_switch.get_active(),
                "schedule_from_hour": int(self.sched_from_row.hour_spin.get_value()),
                "schedule_from_min": int(self.sched_from_row.min_spin.get_value()),
                "schedule_to_hour": int(self.sched_to_row.hour_spin.get_value()),
                "schedule_to_min": int(self.sched_to_row.min_spin.get_value()),
                "scheduler_days": self.sched_days_row.get_selected(),
                "encryption": self.encryption_row.get_selected(),
                "anonymous_mode": self.anonymous_switch.get_active(),
                "max_ratio_enabled": self.ratio_switch.get_active(),
                "max_ratio": self.ratio_row.get_value(),
                "max_seeding_time_enabled": self.seed_time_switch.get_active(),
                "max_seeding_time": int(self.seed_time_row.get_value()),
                "max_inactive_seeding_time_enabled": self.inactive_time_switch.get_active(),
                "max_inactive_seeding_time": int(self.inactive_time_row.get_value()),
                "max_ratio_act": self.SHARE_ACTIONS[self.share_action_row.get_selected()][1],
                "add_trackers_enabled": self.add_trackers_switch.get_active(),
                "add_trackers": text_of(self.add_trackers_view),
            })
            relocate = self.category_changed_row.get_selected() == 1
            stopped = self.add_stopped_switch.get_active()
            if q5 or not self.qb_prefs:
                new_qb_prefs["add_stopped_enabled"] = stopped
                new_qb_prefs["category_changed_tmm_enabled"] = relocate
            if not q5:
                new_qb_prefs["start_paused_enabled"] = stopped
                new_qb_prefs["torrent_changed_tmm_enabled"] = relocate
            if self.share_mode_row.get_visible():
                new_qb_prefs["share_limits_mode"] = self.share_mode_row.get_selected()
            self.client.set_app_preferences(new_qb_prefs)
