import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Gdk, Gio, GLib, GObject, Adw
from ..models.torrent import TorrentItem
from .dialogs.simple_dialogs import LocationDialog, SpeedLimitDialog, CategoryDialog, TagDialog

class TorrentTable(Gtk.Box):
    """Main torrents table featuring sorting, filtering, multi-selection, and context actions."""

    __gsignals__ = {
        'selection-changed': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'torrent-activated': (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        'refresh-requested': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, client, settings=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.client = client
        self.settings = settings
        self.raw_store = Gio.ListStore(item_type=TorrentItem)

        self.default_widths = {
            "#": 40,
            "Name": 280,
            "Size": 75,
            "Done": 160,
            "Status": 95,
            "Seeds": 65,
            "Peers": 65,
            "Down Speed": 85,
            "Up Speed": 85,
            "ETA": 65,
            "Ratio": 60,
            "Category": 85,
            "Tags": 85,
            "Added On": 120,
        }
        self.saved_widths = {}
        if self.settings and hasattr(self.settings, "get_column_widths"):
            self.saved_widths = self.settings.get_column_widths()
        elif self.settings and hasattr(self.settings, "get"):
            self.saved_widths = self.settings.get("column_widths", {}) or {}
        if not isinstance(self.saved_widths, dict):
            self.saved_widths = {}
        self._save_widths_timer = None

        self.columns_by_title = {}
        self.default_order = [
            "#",
            "Name",
            "Size",
            "Done",
            "Status",
            "Seeds",
            "Peers",
            "Down Speed",
            "Up Speed",
            "ETA",
            "Ratio",
            "Category",
            "Tags",
            "Added On",
        ]
        self.saved_order = []
        if self.settings and hasattr(self.settings, "get_column_order"):
            self.saved_order = self.settings.get_column_order()
        elif self.settings and hasattr(self.settings, "get"):
            self.saved_order = self.settings.get("column_order", []) or []
        if not isinstance(self.saved_order, list) or not self.saved_order:
            self.saved_order = list(self.default_order)
        self._internal_reorder = True

        self.visible_columns = {}
        if self.settings and hasattr(self.settings, "get_visible_columns"):
            self.visible_columns = self.settings.get_visible_columns()
        elif self.settings and hasattr(self.settings, "get"):
            self.visible_columns = self.settings.get("visible_columns", {}) or {}
        if not isinstance(self.visible_columns, dict):
            self.visible_columns = {}

        # Setup ActionGroup and header menu for right-clicking columns
        self.action_group = Gio.SimpleActionGroup()
        self.insert_action_group("table", self.action_group)
        self._setup_header_actions()

        # Filtering state
        self.filter_type = "status"
        self.filter_val = "all"
        self.search_text = ""

        # Setup FilterListModel
        self.custom_filter = Gtk.CustomFilter.new(self._filter_func)
        self.filter_model = Gtk.FilterListModel(model=self.raw_store, filter=self.custom_filter)

        # Setup SortListModel
        self.sort_model = Gtk.SortListModel(model=self.filter_model)

        # Setup SelectionModel (MultiSelection)
        self.selection_model = Gtk.MultiSelection(model=self.sort_model)
        self.selection_model.connect("selection-changed", self._on_selection_changed)

        # Scrolled ColumnView
        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.append(scrolled)

        self.column_view = Gtk.ColumnView(model=self.selection_model)
        self.column_view.set_reorderable(True)
        self.column_view.connect("activate", self._on_row_activated)
        scrolled.set_child(self.column_view)

        # Attach right-click context menu gesture
        right_click = Gtk.GestureClick(button=3)
        right_click.connect("pressed", self._on_right_click)
        self.column_view.add_controller(right_click)

        self._setup_columns()

    def _get_initial_width(self, title):
        if self.saved_widths and title in self.saved_widths:
            try:
                w = int(self.saved_widths[title])
                if w > 20:
                    return w
            except Exception:
                pass
        return self.default_widths.get(title, 100)

    def _on_col_width_changed(self, col, title):
        w = col.get_fixed_width()
        if w > 20:
            self.saved_widths[title] = w
            if self.settings:
                if self._save_widths_timer:
                    GLib.source_remove(self._save_widths_timer)
                self._save_widths_timer = GLib.timeout_add(500, self._persist_column_widths)

    def _persist_column_widths(self):
        self._save_widths_timer = None
        if self.settings and hasattr(self.settings, "set_column_widths"):
            self.settings.set_column_widths(dict(self.saved_widths))
        elif self.settings and hasattr(self.settings, "set"):
            self.settings.set("column_widths", dict(self.saved_widths))
        return False

    def _setup_header_actions(self):
        self.header_menu = Gio.Menu()
        cols_section = Gio.Menu()
        for title in self.default_widths.keys():
            action_name = f"toggle_col_{title.replace(' ', '_').replace('#', 'prio').lower()}"
            is_vis = self.is_column_visible(title)
            act = Gio.SimpleAction.new_stateful(
                action_name,
                None,
                GLib.Variant.new_boolean(is_vis)
            )
            if title == "Name":
                act.set_enabled(False)
            else:
                act.connect("change-state", lambda a, v, t=title: self._on_header_action_toggled(a, v, t))
            self.action_group.add_action(act)
            cols_section.append(title, f"table.{action_name}")
        self.header_menu.append_section("Columns", cols_section)

        reset_section = Gio.Menu()
        reset_act = Gio.SimpleAction.new("reset_widths", None)
        reset_act.connect("activate", lambda a, p: self.reset_column_widths())
        self.action_group.add_action(reset_act)
        reset_section.append("Resize Columns to Fit", "table.reset_widths")

        reset_order_act = Gio.SimpleAction.new("reset_order", None)
        reset_order_act.connect("activate", lambda a, p: self.reset_column_order())
        self.action_group.add_action(reset_order_act)
        reset_section.append("Reset Column Order", "table.reset_order")
        self.header_menu.append_section(None, reset_section)

    def _on_header_action_toggled(self, action, value, title):
        action.set_state(value)
        self.set_column_visible(title, value.get_boolean())

    def is_column_visible(self, title):
        if title == "Name":
            return True
        if self.visible_columns and title in self.visible_columns:
            return bool(self.visible_columns[title])
        return True

    def set_column_visible(self, title, is_visible):
        if title == "Name":
            return
        col = self.columns_by_title.get(title)
        if col:
            col.set_visible(is_visible)
            self.visible_columns[title] = is_visible
            action_name = f"toggle_col_{title.replace(' ', '_').replace('#', 'prio').lower()}"
            act = self.action_group.lookup_action(action_name)
            if act:
                act.set_state(GLib.Variant.new_boolean(is_visible))
            if self.settings and hasattr(self.settings, "set_visible_columns"):
                self.settings.set_visible_columns(dict(self.visible_columns))
            elif self.settings and hasattr(self.settings, "set"):
                self.settings.set("visible_columns", dict(self.visible_columns))

    def reset_column_widths(self):
        for title, default_w in self.default_widths.items():
            col = self.columns_by_title.get(title)
            if col:
                col.set_fixed_width(default_w)
                self.saved_widths[title] = default_w
        if self.settings and hasattr(self.settings, "set_column_widths"):
            self.settings.set_column_widths(dict(self.default_widths))
        elif self.settings and hasattr(self.settings, "set"):
            self.settings.set("column_widths", dict(self.default_widths))
        root = self.get_root()
        if root and hasattr(root, "show_toast"):
            root.show_toast("Column widths reset to defaults")

    def reset_column_order(self):
        self._internal_reorder = True
        try:
            for i, title in enumerate(self.default_order):
                col = self.columns_by_title.get(title)
                if col:
                    # insert_column() moves an existing column in place
                    self.column_view.insert_column(i, col)
        finally:
            self._internal_reorder = False
            self._enable_header_reordering()
        self.saved_order = list(self.default_order)
        if self.settings and hasattr(self.settings, "set_column_order"):
            self.settings.set_column_order(list(self.default_order))
        elif self.settings and hasattr(self.settings, "set"):
            self.settings.set("column_order", list(self.default_order))
        root = self.get_root()
        if root and hasattr(root, "show_toast"):
            root.show_toast("Column order reset to defaults")

    def create_column_selector_popover(self):
        popover = Gtk.Popover()
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        main_box.set_margin_top(12)
        main_box.set_margin_bottom(12)
        main_box.set_margin_start(12)
        main_box.set_margin_end(12)
        main_box.set_size_request(240, -1)

        # Header Title
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title_lbl = Gtk.Label(label="<b>Visible Columns</b>", use_markup=True, xalign=0, hexpand=True)
        title_box.append(title_lbl)
        main_box.append(title_box)

        # Scrolled list of CheckButtons
        scrolled = Gtk.ScrolledWindow(max_content_height=320, propagate_natural_height=True)
        col_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scrolled.set_child(col_list_box)

        check_buttons = {}
        for title in self.default_widths.keys():
            col = self.columns_by_title.get(title)
            is_vis = col.get_visible() if col else True
            cb = Gtk.CheckButton(label=title, active=is_vis)
            if title == "Name":
                cb.set_sensitive(False)
            else:
                cb.connect("toggled", lambda b, t=title: self.set_column_visible(t, b.get_active()))
            check_buttons[title] = cb
            col_list_box.append(cb)

        main_box.append(scrolled)
        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Reset / Resize Button
        resize_btn = Gtk.Button()
        resize_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.CENTER)
        resize_box.append(Gtk.Image.new_from_icon_name("zoom-fit-best-symbolic"))
        resize_box.append(Gtk.Label(label="Resize Columns to Fit"))
        resize_btn.set_child(resize_box)
        resize_btn.set_tooltip_text("Reset all columns to optimal default widths")
        resize_btn.add_css_class("flat")
        resize_btn.connect("clicked", lambda b: self._on_reset_btn_clicked(popover))
        main_box.append(resize_btn)

        # Reset Column Order Button
        order_btn = Gtk.Button()
        order_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, halign=Gtk.Align.CENTER)
        order_box.append(Gtk.Image.new_from_icon_name("view-sort-ascending-symbolic"))
        order_box.append(Gtk.Label(label="Reset Column Order"))
        order_btn.set_child(order_box)
        order_btn.set_tooltip_text("Reset column order to defaults")
        order_btn.add_css_class("flat")
        order_btn.connect("clicked", lambda b: self._on_reset_order_btn_clicked(popover))
        main_box.append(order_btn)

        def on_show(p, pspec):
            if p.get_visible():
                for t, cb in check_buttons.items():
                    c = self.columns_by_title.get(t)
                    if c and t != "Name":
                        cb.set_active(c.get_visible())

        popover.connect("notify::visible", on_show)
        popover.set_child(main_box)
        return popover

    def _on_reset_btn_clicked(self, popover):
        self.reset_column_widths()
        popover.popdown()

    def _on_reset_order_btn_clicked(self, popover):
        self.reset_column_order()
        popover.popdown()

    def _setup_columns(self):
        # 1. Queue Priority (#)
        self._create_label_column("#", "priority_str", xalign=1, sorter_prop="priority", numeric=True)

        # 2. Name with Status Icon
        f_name = Gtk.SignalListItemFactory()
        def setup_name(f, i):
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_start=4, margin_end=4)
            img = Gtk.Image()
            lbl = Gtk.Label(xalign=0, ellipsize=3)
            box.append(img)
            box.append(lbl)
            box.img = img
            box.lbl = lbl
            i.set_child(box)

        def bind_name(f, i):
            item = i.get_item()
            box = i.get_child()
            if item and box:
                b1 = item.bind_property("state_icon", box.img, "icon-name", GObject.BindingFlags.SYNC_CREATE)
                b2 = item.bind_property("name", box.lbl, "label", GObject.BindingFlags.SYNC_CREATE)
                i.name_bindings = (b1, b2)

        def unbind_name(f, i):
            if hasattr(i, "name_bindings") and i.name_bindings:
                for b in i.name_bindings:
                    b.unbind()
                i.name_bindings = None

        f_name.connect("setup", setup_name)
        f_name.connect("bind", bind_name)
        f_name.connect("unbind", unbind_name)

        expr_name = Gtk.PropertyExpression.new(TorrentItem, None, "name")
        col_name = Gtk.ColumnViewColumn(title="Name", factory=f_name, sorter=Gtk.StringSorter.new(expr_name))
        col_name.set_fixed_width(self._get_initial_width("Name"))
        col_name.set_expand(True)
        col_name.set_resizable(True)
        col_name.set_visible(self.is_column_visible("Name"))
        col_name.set_header_menu(self.header_menu)
        col_name.connect("notify::fixed-width", lambda c, pspec: self._on_col_width_changed(c, "Name"))
        self.columns_by_title["Name"] = col_name

        # 3. Size
        self._create_label_column("Size", "size_str", xalign=1, sorter_prop="size", numeric=True)

        # 4. Progress Bar
        f_prog = Gtk.SignalListItemFactory()
        f_prog.connect("setup", lambda f, i: i.set_child(Gtk.ProgressBar(show_text=True, margin_start=4, margin_end=4)))
        def bind_prog(f, i):
            item = i.get_item()
            pbar = i.get_child()
            if item and pbar:
                b1 = item.bind_property("progress", pbar, "fraction", GObject.BindingFlags.SYNC_CREATE)
                b2 = item.bind_property("progress_str", pbar, "text", GObject.BindingFlags.SYNC_CREATE)
                i.prog_bindings = (b1, b2)

        def unbind_prog(f, i):
            if hasattr(i, "prog_bindings") and i.prog_bindings:
                for b in i.prog_bindings:
                    b.unbind()
                i.prog_bindings = None

        f_prog.connect("bind", bind_prog)
        f_prog.connect("unbind", unbind_prog)

        expr_prog = Gtk.PropertyExpression.new(TorrentItem, None, "progress")
        col_prog = Gtk.ColumnViewColumn(title="Done", factory=f_prog, sorter=Gtk.NumericSorter.new(expr_prog))
        col_prog.set_fixed_width(self._get_initial_width("Done"))
        col_prog.set_resizable(True)
        col_prog.set_visible(self.is_column_visible("Done"))
        col_prog.set_header_menu(self.header_menu)
        col_prog.connect("notify::fixed-width", lambda c, pspec: self._on_col_width_changed(c, "Done"))
        self.columns_by_title["Done"] = col_prog

        # 5. Status
        self._create_label_column("Status", "state_str", xalign=0, sorter_prop="state_str", numeric=False)

        # 6. Seeds
        self._create_label_column("Seeds", "seeds_str", xalign=1, sorter_prop="num_seeds", numeric=True)

        # 7. Peers
        self._create_label_column("Peers", "peers_str", xalign=1, sorter_prop="num_leechs", numeric=True)

        # 8. Down Speed
        self._create_label_column("Down Speed", "dlspeed_str", xalign=1, sorter_prop="dlspeed", numeric=True)

        # 9. Up Speed
        self._create_label_column("Up Speed", "upspeed_str", xalign=1, sorter_prop="upspeed", numeric=True)

        # 10. ETA
        self._create_label_column("ETA", "eta_str", xalign=1, sorter_prop="eta", numeric=True)

        # 11. Ratio
        self._create_label_column("Ratio", "ratio_str", xalign=1, sorter_prop="ratio", numeric=True)

        # 12. Category
        self._create_label_column("Category", "category", xalign=0, sorter_prop="category", numeric=False)

        # 13. Tags
        self._create_label_column("Tags", "tags", xalign=0, sorter_prop="tags", numeric=False)

        # 14. Added On
        self._create_label_column("Added On", "added_on_str", xalign=0, sorter_prop="added_on", numeric=True)

        # Append columns in the configured/saved order
        ordered_titles = [t for t in self.saved_order if t in self.columns_by_title]
        for t in self.default_order:
            if t not in ordered_titles and t in self.columns_by_title:
                ordered_titles.append(t)

        for t in ordered_titles:
            col = self.columns_by_title[t]
            # GTK (re)creates a column's header widget when it is attached to the view;
            # "notify::column-view" fires after that, so re-apply the reorder workaround.
            col.connect("notify::column-view", lambda c, pspec: self._enable_header_reordering())
            self.column_view.append_column(col)

        # Connect sorters to SortListModel
        self.sort_model.set_sorter(self.column_view.get_sorter())

        # Work around GTK bug that prevents header drag-reordering
        self._enable_header_reordering()

        # Listen for column reordering (drag and drop)
        self.column_view.get_columns().connect("items-changed", self._on_columns_changed)
        self._internal_reorder = False

    def _enable_header_reordering(self):
        """Work around a GTK 4 bug that makes column drag-reordering impossible.

        Each column header (GtkColumnViewTitle) has a click gesture whose "pressed"
        handler immediately claims the event sequence. Claiming a sequence denies it
        for every other gesture in the propagation chain, including the ColumnView's
        own header drag gesture, which only claims after the drag threshold is
        crossed. As a result, column reordering never starts.

        Blocking that "pressed" handler leaves the drag gesture alive. Click-to-sort
        and the header right-click menu still work because they are handled in the
        title gesture's "released" handler. This is idempotent and is re-run whenever
        the column list changes, since GTK may recreate header widgets.
        """
        header_row = self.column_view.get_first_child()
        if header_row is None:
            return
        signal_id = GObject.signal_lookup("pressed", Gtk.GestureClick)
        match = GObject.SignalMatchType.ID | GObject.SignalMatchType.UNBLOCKED
        title = header_row.get_first_child()
        while title is not None:
            controllers = title.observe_controllers()
            for i in range(controllers.get_n_items()):
                ctrl = controllers.get_item(i)
                if isinstance(ctrl, Gtk.GestureClick):
                    while True:
                        handler_id = GObject.signal_handler_find(ctrl, match, signal_id, 0, None, None, None)
                        if not handler_id:
                            break
                        GObject.signal_handler_block(ctrl, handler_id)
            title = title.get_next_sibling()

    def _on_columns_changed(self, model, position, removed, added):
        # Header widgets may have been (re)created; keep reordering functional
        self._enable_header_reordering()
        if self._internal_reorder:
            return
        n = model.get_n_items()
        if n == len(self.columns_by_title):
            new_order = [model.get_item(i).get_title() for i in range(n)]
            self.saved_order = new_order
            if self.settings and hasattr(self.settings, "set_column_order"):
                self.settings.set_column_order(new_order)
            elif self.settings and hasattr(self.settings, "set"):
                self.settings.set("column_order", new_order)

    def _create_label_column(self, title, prop_name, width=None, xalign=0, sorter_prop=None, numeric=False):
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", lambda f, i: i.set_child(Gtk.Label(xalign=xalign, margin_start=4, margin_end=4)))
        
        def bind(f, i):
            item = i.get_item()
            lbl = i.get_child()
            if item and lbl:
                i.binding = item.bind_property(prop_name, lbl, "label", GObject.BindingFlags.SYNC_CREATE)

        def unbind(f, i):
            if hasattr(i, "binding") and i.binding:
                i.binding.unbind()
                i.binding = None

        factory.connect("bind", bind)
        factory.connect("unbind", unbind)

        expr = Gtk.PropertyExpression.new(TorrentItem, None, sorter_prop or prop_name)
        sorter = Gtk.NumericSorter.new(expr) if numeric else Gtk.StringSorter.new(expr)
        
        initial_width = width if width is not None else self._get_initial_width(title)
        col = Gtk.ColumnViewColumn(title=title, factory=factory, sorter=sorter)
        col.set_fixed_width(initial_width)
        col.set_resizable(True)
        col.set_visible(self.is_column_visible(title))
        col.set_header_menu(self.header_menu)
        col.connect("notify::fixed-width", lambda c, pspec, t=title: self._on_col_width_changed(c, t))
        self.columns_by_title[title] = col
        return col

    def _filter_func(self, item):
        if not item:
            return False

        # Search text match
        if self.search_text:
            query = self.search_text.lower()
            if query not in item.name.lower() and query not in item.hash.lower():
                return False

        # Sidebar filter match
        if self.filter_type == "status":
            return item.matches_status_filter(self.filter_val)
        elif self.filter_type == "category":
            if not self.filter_val or self.filter_val == "all":
                return True
            return item.category == self.filter_val
        elif self.filter_type == "tag":
            if not self.filter_val or self.filter_val == "all":
                return True
            item_tags = [t.strip() for t in item.tags.split(',') if t.strip()]
            return self.filter_val in item_tags
        elif self.filter_type == "tracker":
            if not self.filter_val or self.filter_val == "all":
                return True
            return True

        return True

    def set_sidebar_filter(self, filter_type, filter_val):
        self.filter_type = filter_type
        self.filter_val = filter_val
        self.custom_filter.changed(Gtk.FilterChange.DIFFERENT)

    def set_search_query(self, query):
        self.search_text = query.strip()
        self.custom_filter.changed(Gtk.FilterChange.DIFFERENT)

    def get_selected_items(self):
        selection = self.selection_model.get_selection()
        items = []
        n = self.sort_model.get_n_items()
        for i in range(n):
            if selection.contains(i):
                item = self.sort_model.get_item(i)
                if item:
                    items.append(item)
        return items

    def get_selected_torrent(self):
        items = self.get_selected_items()
        return items[0] if items else None

    def _on_selection_changed(self, selection_model, position, n_items):
        self.emit("selection-changed")

    def _on_row_activated(self, column_view, position):
        item = self.sort_model.get_item(position)
        if item and item.save_path:
            self.emit("torrent-activated", item.save_path)

    def _on_right_click(self, gesture, n_press, x, y):
        # Ignore right-clicks on the column header row; the header has its own menu
        header_row = self.column_view.get_first_child()
        if header_row is not None and y <= header_row.get_height():
            return

        items = self.get_selected_items()
        if not items:
            return

        popover = Gtk.Popover()
        popover.set_parent(self.column_view)
        
        # Point to click position
        rect = Gdk.Rectangle()
        rect.x = int(x)
        rect.y = int(y)
        rect.width = 1
        rect.height = 1
        popover.set_pointing_to(rect)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        popover.set_child(box)

        hashes = [it.hash for it in items]

        def add_menu_btn(label, icon, callback):
            btn = Gtk.Button(label=label, css_classes=["flat"])
            b_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            b_box.append(Gtk.Image.new_from_icon_name(icon))
            b_box.append(Gtk.Label(label=label, xalign=0))
            btn.set_child(b_box)
            btn.connect("clicked", lambda b: [popover.popdown(), callback()])
            box.append(btn)

        def _action(func):
            func()
            self.emit("refresh-requested")

        add_menu_btn("Resume", "media-playback-start-symbolic", lambda: _action(lambda: self.client.resume_torrent(hashes)))
        add_menu_btn("Pause", "media-playback-pause-symbolic", lambda: _action(lambda: self.client.pause_torrent(hashes)))
        add_menu_btn("Force Start", "media-playback-start-symbolic", lambda: _action(lambda: self.client.set_force_start(hashes, True)))
        
        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Priority submenu buttons
        add_menu_btn("Top Priority", "go-top-symbolic", lambda: _action(lambda: self.client.top_priority(hashes)))
        add_menu_btn("Increase Priority", "go-up-symbolic", lambda: _action(lambda: self.client.increase_priority(hashes)))
        add_menu_btn("Decrease Priority", "go-down-symbolic", lambda: _action(lambda: self.client.decrease_priority(hashes)))
        add_menu_btn("Bottom Priority", "go-bottom-symbolic", lambda: _action(lambda: self.client.bottom_priority(hashes)))

        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        add_menu_btn("Force Recheck", "system-run-symbolic", lambda: _action(lambda: self.client.recheck_torrent(hashes)))
        add_menu_btn("Force Reannounce", "view-refresh-symbolic", lambda: _action(lambda: self.client.reannounce_torrent(hashes)))
        add_menu_btn("Set Location...", "folder-symbolic", lambda: self._on_set_location(items[0]))
        add_menu_btn("Set Speed Limits...", "network-transmit-receive-symbolic", lambda: self._on_set_limits(items[0]))
        
        if len(items) == 1:
            add_menu_btn("Rename...", "document-edit-symbolic", lambda: self._on_rename(items[0]))

        box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        add_menu_btn("Remove...", "user-trash-symbolic", lambda: self._on_delete(items))

        popover.popup()

    def _on_set_location(self, item):
        dialog = LocationDialog(self.get_root(), item.save_path)
        def on_resp(d, resp):
            if resp == "save":
                loc = d.get_location()
                if loc:
                    items = self.get_selected_items()
                    self.client.set_location([it.hash for it in items], loc)
            d.destroy()
        dialog.connect("response", on_resp)
        dialog.show()

    def _on_set_limits(self, item):
        dialog = SpeedLimitDialog(self.get_root(), item.dlspeed, item.upspeed)
        def on_resp(d, resp):
            if resp == "save":
                dl, up = d.get_limits()
                items = self.get_selected_items()
                hashes = [it.hash for it in items]
                self.client.set_download_limit(hashes, dl)
                self.client.set_upload_limit(hashes, up)
            d.destroy()
        dialog.connect("response", on_resp)
        dialog.show()

    def _on_rename(self, item):
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading="Rename Torrent",
            body="Enter new name:"
        )
        entry = Gtk.Entry()
        entry.set_text(item.name)
        entry.set_margin_top(12)
        entry.set_margin_bottom(12)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        dialog.set_extra_child(entry)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Rename")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)

        def on_resp(d, resp):
            if resp == "save":
                new_name = entry.get_text().strip()
                if new_name and new_name != item.name:
                    self.client.rename_torrent(item.hash, new_name)
                    item.name = new_name
            d.destroy()

        dialog.connect("response", on_resp)
        dialog.show()

    def _on_delete(self, items):
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading=f"Delete {len(items)} Torrent(s)?",
            body="Are you sure you want to remove the selected torrent(s)?"
        )
        chk_files = Gtk.CheckButton(label="Also delete the files on the hard disk")
        chk_files.set_margin_top(8)
        chk_files.set_margin_bottom(8)
        chk_files.set_margin_start(12)
        chk_files.set_margin_end(12)
        dialog.set_extra_child(chk_files)

        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")

        def on_resp(d, resp):
            if resp == "delete":
                del_files = chk_files.get_active()
                hashes = [it.hash for it in items]
                self.client.delete_torrent(hashes, delete_files=del_files)
            d.destroy()

        dialog.connect("response", on_resp)
        dialog.show()
