import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
from ..utils.formatters import format_bytes, format_speed

class StatusBar(Gtk.Box):
    """Bottom status bar displaying global transfer rates, alt speeds toggle, and DHT stats."""

    def __init__(self, client):
        super().__init__(
            orientation=Gtk.Orientation.HORIZONTAL,
            spacing=16,
            margin_top=4,
            margin_bottom=4,
            margin_start=12,
            margin_end=12
        )
        self.client = client
        self.cached_prefs = {}

        # Connection status & DHT
        self.conn_img = Gtk.Image.new_from_icon_name("network-wired-symbolic")
        self.append(self.conn_img)

        self.lbl_dht = Gtk.Label(label="DHT: 0 nodes", css_classes=["dim-label"])
        self.append(self.lbl_dht)

        # Separator
        self.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        # Free space
        self.lbl_free_space = Gtk.Label(label="Free: —", css_classes=["dim-label"], hexpand=True, xalign=0)
        self.append(self.lbl_free_space)

        # Alternative Speed Limits (Speedometer / Turtle Mode) Button
        self.alt_speed_btn = Gtk.ToggleButton(icon_name="power-profile-performance-symbolic")
        self.alt_speed_btn.add_css_class("flat")
        self.alt_speed_btn.connect("toggled", self._on_alt_speed_toggled)
        self.append(self.alt_speed_btn)

        # Setup right-click & long-press gesture to open speed limit editor popover
        btn_rc = Gtk.GestureClick(button=3)
        btn_rc.connect("pressed", lambda g, n, x, y: self._open_speed_popover())
        self.alt_speed_btn.add_controller(btn_rc)

        btn_lp = Gtk.GestureLongPress()
        btn_lp.connect("pressed", lambda g, x, y: self._open_speed_popover())
        self.alt_speed_btn.add_controller(btn_lp)

        # Rates
        self.lbl_dl = Gtk.Label(label="DL: 0 B/s")
        self.append(self.lbl_dl)

        self.lbl_up = Gtk.Label(label="UL: 0 B/s")
        self.append(self.lbl_up)

        # Also open speed limits popover on right-clicking rates
        for lbl in (self.lbl_dl, self.lbl_up):
            rc = Gtk.GestureClick(button=3)
            rc.connect("pressed", lambda g, n, x, y: self._open_speed_popover())
            lbl.add_controller(rc)

        # Total Session
        self.lbl_session = Gtk.Label(label="[0 B / 0 B]", css_classes=["dim-label"])
        self.append(self.lbl_session)

        # Create popover for editing alternative speed limits
        self._create_speed_popover()
        self._set_alt_speed_visual_state(False)

    def _create_speed_popover(self):
        self.speed_popover = Gtk.Popover()
        self.speed_popover.set_parent(self.alt_speed_btn)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(14)
        box.set_margin_end(14)
        box.set_size_request(270, -1)

        # Header Title
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_lbl = Gtk.Label(label="<b>Alternative Speed Limits</b>", use_markup=True, xalign=0, hexpand=True)
        title_box.append(title_lbl)
        box.append(title_box)

        # Enable Switch Row
        enable_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        enable_lbl = Gtk.Label(label="Alternative limits active", xalign=0, hexpand=True)
        self.popover_enable_switch = Gtk.Switch(valign=Gtk.Align.CENTER)
        enable_box.append(enable_lbl)
        enable_box.append(self.popover_enable_switch)
        box.append(enable_box)

        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Download Limit
        dl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        dl_lbl = Gtk.Label(label="Download (KiB/s):", xalign=0, hexpand=True)
        self.popover_dl_adj = Gtk.Adjustment(value=0, lower=0, upper=1000000, step_increment=10, page_increment=100)
        self.popover_dl_spin = Gtk.SpinButton(adjustment=self.popover_dl_adj, numeric=True)
        self.popover_dl_spin.set_width_chars(8)
        dl_box.append(dl_lbl)
        dl_box.append(self.popover_dl_spin)
        box.append(dl_box)

        # Upload Limit
        up_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        up_lbl = Gtk.Label(label="Upload (KiB/s):", xalign=0, hexpand=True)
        self.popover_up_adj = Gtk.Adjustment(value=0, lower=0, upper=1000000, step_increment=10, page_increment=100)
        self.popover_up_spin = Gtk.SpinButton(adjustment=self.popover_up_adj, numeric=True)
        self.popover_up_spin.set_width_chars(8)
        up_box.append(up_lbl)
        up_box.append(self.popover_up_spin)
        box.append(up_box)

        hint_lbl = Gtk.Label(label="<i>0 = Unlimited</i>", use_markup=True, xalign=0, css_classes=["dim-label"])
        box.append(hint_lbl)

        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Action Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        pref_btn = Gtk.Button(label="Preferences...")
        pref_btn.add_css_class("flat")
        pref_btn.connect("clicked", self._on_popover_preferences_clicked)
        btn_box.append(pref_btn)

        spacer = Gtk.Box(hexpand=True)
        btn_box.append(spacer)

        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_popover_save_clicked)
        btn_box.append(save_btn)

        box.append(btn_box)
        self.speed_popover.set_child(box)

    def _open_speed_popover(self):
        if self.client and hasattr(self.client, "is_connected") and self.client.is_connected():
            prefs = self.client.get_app_preferences()
            if prefs:
                self.cached_prefs.update(prefs)

        alt_active = self.alt_speed_btn.get_active()
        self.popover_enable_switch.set_active(alt_active)

        alt_dl = self.cached_prefs.get("alt_dl_limit", 0)
        alt_up = self.cached_prefs.get("alt_up_limit", 0)
        self.popover_dl_adj.set_value(alt_dl // 1024 if alt_dl > 0 else 0)
        self.popover_up_adj.set_value(alt_up // 1024 if alt_up > 0 else 0)

        if self.get_root():
            self.speed_popover.popup()

    def _on_popover_preferences_clicked(self, btn):
        self.speed_popover.popdown()
        root = self.get_root()
        if root and hasattr(root, "_on_preferences_clicked"):
            root._on_preferences_clicked(None)

    def _on_popover_save_clicked(self, btn):
        dl_kib = int(self.popover_dl_adj.get_value())
        up_kib = int(self.popover_up_adj.get_value())
        new_active = self.popover_enable_switch.get_active()

        if self.client:
            self.client.set_app_preferences({
                "alt_dl_limit": dl_kib * 1024,
                "alt_up_limit": up_kib * 1024
            })
            if hasattr(self.client, "set_speed_limits_mode"):
                self.client.set_speed_limits_mode(new_active)
            elif self.alt_speed_btn.get_active() != new_active:
                self.client.toggle_speed_limits_mode()

            self.alt_speed_btn.handler_block_by_func(self._on_alt_speed_toggled)
            self.alt_speed_btn.set_active(new_active)
            self.alt_speed_btn.handler_unblock_by_func(self._on_alt_speed_toggled)

        self.cached_prefs["alt_dl_limit"] = dl_kib * 1024
        self.cached_prefs["alt_up_limit"] = up_kib * 1024
        self._set_alt_speed_visual_state(new_active)
        self.speed_popover.popdown()

        root = self.get_root()
        if root and hasattr(root, "show_toast"):
            dl_str = f"{dl_kib} KiB/s" if dl_kib > 0 else "Unlimited"
            up_str = f"{up_kib} KiB/s" if up_kib > 0 else "Unlimited"
            root.show_toast(f"Alternative speed limits saved ({dl_str} DL / {up_str} UL)")

    def _set_alt_speed_visual_state(self, active):
        dl = self.cached_prefs.get("alt_dl_limit", 0)
        up = self.cached_prefs.get("alt_up_limit", 0)
        dl_str = f"{dl // 1024} KiB/s" if dl > 0 else "Unlimited"
        up_str = f"{up // 1024} KiB/s" if up > 0 else "Unlimited"

        if active:
            if "suggested-action" not in self.alt_speed_btn.get_css_classes():
                self.alt_speed_btn.add_css_class("suggested-action")
            self.alt_speed_btn.set_tooltip_text(
                f"Alternative Speed Limits: Active\nDownload: {dl_str} | Upload: {up_str}\nClick to disable • Right-click to edit"
            )
        else:
            if "suggested-action" in self.alt_speed_btn.get_css_classes():
                self.alt_speed_btn.remove_css_class("suggested-action")
            self.alt_speed_btn.set_tooltip_text(
                f"Alternative Speed Limits: Inactive\nDownload: {dl_str} | Upload: {up_str}\nClick to enable • Right-click to edit"
            )

    def update_status(self, transfer_info, free_space=None, prefs=None):
        if prefs:
            self.cached_prefs.update(prefs)

        if not transfer_info:
            self.conn_img.set_from_icon_name("network-offline-symbolic")
            self.lbl_dht.set_text("Offline")
            self.lbl_dl.set_text("DL: 0 B/s")
            self.lbl_up.set_text("UL: 0 B/s")
            return

        # Connection status
        conn_status = transfer_info.get('connection_status', 'connected')
        if conn_status == 'connected':
            self.conn_img.set_from_icon_name("network-wired-symbolic")
        elif conn_status == 'firewalled':
            self.conn_img.set_from_icon_name("security-medium-symbolic")
        else:
            self.conn_img.set_from_icon_name("network-offline-symbolic")

        dht_nodes = transfer_info.get('dht_nodes', 0)
        self.lbl_dht.set_text(f"DHT: {dht_nodes} nodes")

        if free_space is not None:
            self.lbl_free_space.set_text(f"Free: {format_bytes(free_space)}")

        # Speeds
        dl_rate = transfer_info.get('dl_info_speed', 0)
        up_rate = transfer_info.get('up_info_speed', 0)
        self.lbl_dl.set_text(f"DL: {format_speed(dl_rate)}")
        self.lbl_up.set_text(f"UL: {format_speed(up_rate)}")

        dl_data = transfer_info.get('dl_info_data', 0)
        up_data = transfer_info.get('up_info_data', 0)
        self.lbl_session.set_text(f"[{format_bytes(dl_data)} / {format_bytes(up_data)}]")

        # Alt speed state
        if self.client and hasattr(self.client, "is_connected") and self.client.is_connected():
            alt_active = bool(self.client.get_speed_limits_mode())
        else:
            alt_active = self.alt_speed_btn.get_active()

        if self.alt_speed_btn.get_active() != alt_active:
            self.alt_speed_btn.handler_block_by_func(self._on_alt_speed_toggled)
            self.alt_speed_btn.set_active(alt_active)
            self.alt_speed_btn.handler_unblock_by_func(self._on_alt_speed_toggled)

        self._set_alt_speed_visual_state(alt_active)

    def _on_alt_speed_toggled(self, btn):
        active = btn.get_active()
        self._set_alt_speed_visual_state(active)
        if self.client:
            if hasattr(self.client, "set_speed_limits_mode"):
                self.client.set_speed_limits_mode(active)
            else:
                self.client.toggle_speed_limits_mode()

        root = self.get_root()
        if root and hasattr(root, "show_toast"):
            if active:
                dl = self.cached_prefs.get("alt_dl_limit", 0)
                up = self.cached_prefs.get("alt_up_limit", 0)
                dl_str = f"{dl // 1024} KiB/s" if dl > 0 else "Unlimited"
                up_str = f"{up // 1024} KiB/s" if up > 0 else "Unlimited"
                root.show_toast(f"Alternative speed limits enabled ({dl_str} DL / {up_str} UL)")
            else:
                root.show_toast("Alternative speed limits disabled")
