import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, GObject, Gio, Adw
from .dialogs.simple_dialogs import CategoryDialog, TagDialog

class Sidebar(Gtk.Box):
    """Left sidebar with Status, Categories, Tags, and Trackers filters."""

    __gsignals__ = {
        'filter-changed': (GObject.SignalFlags.RUN_FIRST, None, (str, str)),  # (filter_type, filter_value)
        'priority-clicked': (GObject.SignalFlags.RUN_FIRST, None, (str,)),    # (action: "top"|"up"|"down"|"bottom")
    }

    def __init__(self, client):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.client = client
        self.active_filter_type = "status"
        self.active_filter_value = "all"

        self.status_counts = {}
        self.category_counts = {}
        self.tag_counts = {}
        self.tracker_counts = {}

        self.set_size_request(200, -1)

        # 0. Priority Controls Bar at top of sidebar
        self.prio_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_top=6, margin_bottom=6, margin_start=8, margin_end=8)
        prio_lbl = Gtk.Label(label="<b>Priority</b>", use_markup=True, xalign=0, hexpand=True)
        self.prio_bar.append(prio_lbl)

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["linked"])
        self.top_prio_btn = Gtk.Button(icon_name="go-top-symbolic", tooltip_text="Top Priority")
        self.top_prio_btn.connect("clicked", lambda b: self.emit("priority-clicked", "top"))
        btn_box.append(self.top_prio_btn)

        self.up_prio_btn = Gtk.Button(icon_name="go-up-symbolic", tooltip_text="Increase Priority")
        self.up_prio_btn.connect("clicked", lambda b: self.emit("priority-clicked", "up"))
        btn_box.append(self.up_prio_btn)

        self.down_prio_btn = Gtk.Button(icon_name="go-down-symbolic", tooltip_text="Decrease Priority")
        self.down_prio_btn.connect("clicked", lambda b: self.emit("priority-clicked", "down"))
        btn_box.append(self.down_prio_btn)

        self.bottom_prio_btn = Gtk.Button(icon_name="go-bottom-symbolic", tooltip_text="Bottom Priority")
        self.bottom_prio_btn.connect("clicked", lambda b: self.emit("priority-clicked", "bottom"))
        btn_box.append(self.bottom_prio_btn)

        self.prio_bar.append(btn_box)
        self.append(self.prio_bar)

        self.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.append(scrolled)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=8, margin_bottom=8, margin_start=8, margin_end=8)
        scrolled.set_child(main_box)

        # 1. Status Section
        lbl_status = Gtk.Label(label="<b>STATUS</b>", use_markup=True, xalign=0, margin_start=4)
        main_box.append(lbl_status)
        self.status_list = Gtk.ListBox(css_classes=["navigation-sidebar"])
        self.status_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        main_box.append(self.status_list)

        # 2. Categories Section
        cat_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_start=4)
        cat_header_box.append(Gtk.Label(label="<b>CATEGORIES</b>", use_markup=True, xalign=0, hexpand=True))
        add_cat_btn = Gtk.Button(icon_name="list-add-symbolic", css_classes=["flat"])
        add_cat_btn.set_tooltip_text("Add Category")
        add_cat_btn.connect("clicked", self._on_add_category_clicked)
        cat_header_box.append(add_cat_btn)
        main_box.append(cat_header_box)

        self.category_list = Gtk.ListBox(css_classes=["navigation-sidebar"])
        self.category_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.category_list.connect("row-selected", self._on_category_row_selected)
        main_box.append(self.category_list)

        # 3. Tags Section
        tag_header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_start=4)
        tag_header_box.append(Gtk.Label(label="<b>TAGS</b>", use_markup=True, xalign=0, hexpand=True))
        add_tag_btn = Gtk.Button(icon_name="list-add-symbolic", css_classes=["flat"])
        add_tag_btn.set_tooltip_text("Add Tag")
        add_tag_btn.connect("clicked", self._on_add_tag_clicked)
        tag_header_box.append(add_tag_btn)
        main_box.append(tag_header_box)

        self.tag_list = Gtk.ListBox(css_classes=["navigation-sidebar"])
        self.tag_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.tag_list.connect("row-selected", self._on_tag_row_selected)
        main_box.append(self.tag_list)

        # 4. Trackers Section
        lbl_trackers = Gtk.Label(label="<b>TRACKERS</b>", use_markup=True, xalign=0, margin_start=4)
        main_box.append(lbl_trackers)
        self.tracker_list = Gtk.ListBox(css_classes=["navigation-sidebar"])
        self.tracker_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.tracker_list.connect("row-selected", self._on_tracker_row_selected)
        main_box.append(self.tracker_list)

        # Now connect status row selected and initialize rows
        self.status_list.connect("row-selected", self._on_status_row_selected)
        self._init_status_rows()

    def _create_sidebar_row(self, title, count=0, icon_name="folder-symbolic", item_id=""):
        row = Gtk.ListBoxRow()
        row.item_id = item_id
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, margin_top=4, margin_bottom=4, margin_start=6, margin_end=6)
        
        img = Gtk.Image.new_from_icon_name(icon_name)
        box.append(img)

        lbl = Gtk.Label(label=title, xalign=0, hexpand=True, ellipsize=3)
        box.append(lbl)

        count_badge = Gtk.Label(label=f"({count})", css_classes=["dim-label"])
        row.count_label = count_badge
        box.append(count_badge)

        row.set_child(box)
        return row

    def _init_status_rows(self):
        self.status_items = [
            ("All", "all", "network-workgroup-symbolic"),
            ("Downloading", "downloading", "folder-download-symbolic"),
            ("Seeding", "seeding", "network-transmit-receive-symbolic"),
            ("Completed", "completed", "emblem-ok-symbolic"),
            ("Resumed / Active", "active", "media-playback-start-symbolic"),
            ("Paused / Inactive", "inactive", "media-playback-pause-symbolic"),
            ("Stalled", "stalled", "network-idle-symbolic"),
            ("Stalled Downloading", "stalled_dl", "network-idle-symbolic"),
            ("Stalled Uploading", "stalled_up", "network-idle-symbolic"),
            ("Checking", "checking", "system-run-symbolic"),
            ("Moving", "moving", "document-save-as-symbolic"),
            ("Errored", "errored", "dialog-error-symbolic"),
        ]
        self.status_row_widgets = {}
        for title, s_id, icon in self.status_items:
            row = self._create_sidebar_row(title, count=0, icon_name=icon, item_id=s_id)
            self.status_list.append(row)
            self.status_row_widgets[s_id] = row
        
        first_row = self.status_list.get_row_at_index(0)
        if first_row:
            self.status_list.select_row(first_row)

    def update_counts(self, torrent_items, categories_dict, tags_list, trackers_dict):
        # 1. Update status counts
        counts = {s_id: 0 for _, s_id, _ in self.status_items}
        for item in torrent_items:
            for _, s_id, _ in self.status_items:
                if item.matches_status_filter(s_id):
                    counts[s_id] += 1

        for s_id, cnt in counts.items():
            if s_id in self.status_row_widgets:
                self.status_row_widgets[s_id].count_label.set_text(f"({cnt})")

        # 2. Update Categories
        # Clear existing
        while True:
            row = self.category_list.get_row_at_index(0)
            if not row:
                break
            self.category_list.remove(row)

        all_cat_row = self._create_sidebar_row("All", len(torrent_items), "folder-symbolic", "all")
        self.category_list.append(all_cat_row)

        uncat_count = sum(1 for item in torrent_items if not item.category)
        uncat_row = self._create_sidebar_row("Uncategorized", uncat_count, "folder-symbolic", "")
        self.category_list.append(uncat_row)

        for cat_name in sorted(categories_dict.keys()):
            cnt = sum(1 for item in torrent_items if item.category == cat_name)
            cat_row = self._create_sidebar_row(cat_name, cnt, "folder-symbolic", cat_name)
            self._add_category_context_menu(cat_row, cat_name, categories_dict.get(cat_name, {}).get('savePath', ''))
            self.category_list.append(cat_row)

        # 3. Update Tags
        while True:
            row = self.tag_list.get_row_at_index(0)
            if not row:
                break
            self.tag_list.remove(row)

        all_tag_row = self._create_sidebar_row("All", len(torrent_items), "tag-symbolic", "all")
        self.tag_list.append(all_tag_row)

        untagged_count = sum(1 for item in torrent_items if not item.tags)
        untagged_row = self._create_sidebar_row("Untagged", untagged_count, "tag-symbolic", "")
        self.tag_list.append(untagged_row)

        for tag in sorted(tags_list):
            cnt = sum(1 for item in torrent_items if tag in [t.strip() for t in item.tags.split(',')])
            tag_row = self._create_sidebar_row(tag, cnt, "tag-symbolic", tag)
            self._add_tag_context_menu(tag_row, tag)
            self.tag_list.append(tag_row)

        # 4. Update Trackers
        while True:
            row = self.tracker_list.get_row_at_index(0)
            if not row:
                break
            self.tracker_list.remove(row)

        all_tr_row = self._create_sidebar_row("All", len(torrent_items), "network-transmit-receive-symbolic", "all")
        self.tracker_list.append(all_tr_row)

        for host, cnt in sorted(trackers_dict.items()):
            tr_row = self._create_sidebar_row(host, cnt, "network-transmit-receive-symbolic", host)
            self.tracker_list.append(tr_row)

    def _add_category_context_menu(self, row, cat_name, save_path):
        click_gesture = Gtk.GestureClick(button=3)
        def on_right_click(gesture, n_press, x, y):
            menu = Gio.Menu()
            menu.append("Edit...", f"cat.edit::{cat_name}")
            menu.append("Delete", f"cat.delete::{cat_name}")
            popover = Gtk.PopoverMenu.new_from_model(menu)
            popover.set_parent(row)
            popover.popup()
        click_gesture.connect("pressed", on_right_click)
        row.add_controller(click_gesture)

    def _add_tag_context_menu(self, row, tag):
        click_gesture = Gtk.GestureClick(button=3)
        def on_right_click(gesture, n_press, x, y):
            menu = Gio.Menu()
            menu.append("Delete", f"tag.delete::{tag}")
            popover = Gtk.PopoverMenu.new_from_model(menu)
            popover.set_parent(row)
            popover.popup()
        click_gesture.connect("pressed", on_right_click)
        row.add_controller(click_gesture)

    def _on_add_category_clicked(self, btn):
        dialog = CategoryDialog(self.get_root(), is_edit=False)
        def on_resp(d, resp):
            if resp == "save":
                name, path = d.get_data()
                if name:
                    self.client.create_category(name=name, save_path=path)
            d.destroy()
        dialog.connect("response", on_resp)
        dialog.show()

    def _on_add_tag_clicked(self, btn):
        dialog = TagDialog(self.get_root())
        def on_resp(d, resp):
            if resp == "add":
                tags = d.get_tags()
                if tags:
                    self.client.create_tags(tags)
            d.destroy()
        dialog.connect("response", on_resp)
        dialog.show()

    def _on_status_row_selected(self, box, row):
        if row:
            self.category_list.unselect_all()
            self.tag_list.unselect_all()
            self.tracker_list.unselect_all()
            self.active_filter_type = "status"
            self.active_filter_value = row.item_id
            self.emit("filter-changed", "status", row.item_id)

    def _on_category_row_selected(self, box, row):
        if row:
            self.status_list.unselect_all()
            self.tag_list.unselect_all()
            self.tracker_list.unselect_all()
            self.active_filter_type = "category"
            self.active_filter_value = row.item_id
            self.emit("filter-changed", "category", row.item_id)

    def _on_tag_row_selected(self, box, row):
        if row:
            self.status_list.unselect_all()
            self.category_list.unselect_all()
            self.tracker_list.unselect_all()
            self.active_filter_type = "tag"
            self.active_filter_value = row.item_id
            self.emit("filter-changed", "tag", row.item_id)

    def _on_tracker_row_selected(self, box, row):
        if row:
            self.status_list.unselect_all()
            self.category_list.unselect_all()
            self.tag_list.unselect_all()
            self.active_filter_type = "tracker"
            self.active_filter_value = row.item_id
            self.emit("filter-changed", "tracker", row.item_id)
