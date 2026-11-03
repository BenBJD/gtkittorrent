import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, GObject, Gio
from ...utils.formatters import format_timestamp

class LogItem(GObject.Object):
    id = GObject.Property(type=int, default=0)
    timestamp_str = GObject.Property(type=str, default="")
    message = GObject.Property(type=str, default="")
    type_str = GObject.Property(type=str, default="Normal")

    def __init__(self, data=None):
        super().__init__()
        if data:
            self.id = data.get('id', 0)
            self.timestamp_str = format_timestamp(data.get('timestamp', 0) // 1000)
            self.message = str(data.get('message', ''))
            t = data.get('type', 1)
            t_map = {1: "Normal", 2: "Info", 4: "Warning", 8: "Critical"}
            self.type_str = t_map.get(t, "Normal")


class LogTab(Gtk.Box):
    """qBittorrent Execution Log tab with message filtering."""

    def __init__(self, client):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.client = client
        self.last_log_id = -1
        self.model = Gio.ListStore(item_type=LogItem)

        # Toolbar with filter check buttons
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12, margin_top=6, margin_bottom=6, margin_start=12, margin_end=12)
        self.append(toolbar)

        self.chk_normal = Gtk.CheckButton(label="Normal", active=True)
        self.chk_normal.connect("toggled", lambda x: self.refresh_logs(force=True))
        toolbar.append(self.chk_normal)

        self.chk_info = Gtk.CheckButton(label="Info", active=True)
        self.chk_info.connect("toggled", lambda x: self.refresh_logs(force=True))
        toolbar.append(self.chk_info)

        self.chk_warning = Gtk.CheckButton(label="Warning", active=True)
        self.chk_warning.connect("toggled", lambda x: self.refresh_logs(force=True))
        toolbar.append(self.chk_warning)

        self.chk_critical = Gtk.CheckButton(label="Critical", active=True)
        self.chk_critical.connect("toggled", lambda x: self.refresh_logs(force=True))
        toolbar.append(self.chk_critical)

        clear_btn = Gtk.Button(label="Clear", valign=Gtk.Align.CENTER)
        clear_btn.connect("clicked", lambda x: self.model.remove_all())
        toolbar.append(clear_btn)

        # Scrolled ColumnView
        scrolled = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        self.append(scrolled)

        self.selection_model = Gtk.SingleSelection(model=self.model)
        self.column_view = Gtk.ColumnView(model=self.selection_model)
        scrolled.set_child(self.column_view)

        self._setup_columns()

    def _setup_columns(self):
        # Time
        f_time = Gtk.SignalListItemFactory()
        f_time.connect("setup", lambda f, i: i.set_child(Gtk.Label(xalign=0, margin_start=4, margin_end=4)))
        f_time.connect("bind", lambda f, i: i.get_child().set_text(i.get_item().timestamp_str if i.get_item() else ""))
        col_time = Gtk.ColumnViewColumn(title="Time", factory=f_time)
        col_time.set_fixed_width(160)
        self.column_view.append_column(col_time)

        # Type
        f_type = Gtk.SignalListItemFactory()
        f_type.connect("setup", lambda f, i: i.set_child(Gtk.Label(xalign=0, margin_start=4, margin_end=4)))
        f_type.connect("bind", lambda f, i: i.get_child().set_text(i.get_item().type_str if i.get_item() else ""))
        col_type = Gtk.ColumnViewColumn(title="Type", factory=f_type)
        col_type.set_fixed_width(90)
        self.column_view.append_column(col_type)

        # Message
        f_msg = Gtk.SignalListItemFactory()
        f_msg.connect("setup", lambda f, i: i.set_child(Gtk.Label(xalign=0, margin_start=4, margin_end=4, selectable=True)))
        def bind_msg(f, i):
            item = i.get_item()
            lbl = i.get_child()
            if item and lbl:
                lbl.set_text(item.message)
        f_msg.connect("bind", bind_msg)
        col_msg = Gtk.ColumnViewColumn(title="Message", factory=f_msg)
        col_msg.set_expand(True)
        self.column_view.append_column(col_msg)

    def refresh_logs(self, force=False):
        if not self.client:
            return
        last_id = -1 if force else self.last_log_id
        if force:
            self.model.remove_all()

        logs = self.client.get_logs(
            normal=self.chk_normal.get_active(),
            info=self.chk_info.get_active(),
            warning=self.chk_warning.get_active(),
            critical=self.chk_critical.get_active(),
            last_known_id=last_id
        )
        for log in logs:
            self.model.append(LogItem(log))
            if log.get('id', 0) > self.last_log_id:
                self.last_log_id = log.get('id', 0)
