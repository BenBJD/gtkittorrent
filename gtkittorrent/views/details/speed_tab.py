import collections
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
from ...utils.formatters import format_speed

class SpeedTab(Gtk.Box):
    """Real-time speed graph drawn with Cairo."""

    def __init__(self, client):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.client = client
        self.max_points = 60
        self.dl_history = collections.deque([0] * self.max_points, maxlen=self.max_points)
        self.up_history = collections.deque([0] * self.max_points, maxlen=self.max_points)

        # Legend and rate readouts
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16, margin_top=8, margin_bottom=4, margin_start=12, margin_end=12)
        self.append(header)

        self.dl_lbl = Gtk.Label(label="<span color='#3584e4'>● DL: 0 B/s</span>", use_markup=True)
        header.append(self.dl_lbl)

        self.up_lbl = Gtk.Label(label="<span color='#e01b24'>● UL: 0 B/s</span>", use_markup=True)
        header.append(self.up_lbl)

        # Drawing Area
        self.drawing_area = Gtk.DrawingArea(vexpand=True, hexpand=True)
        self.drawing_area.set_draw_func(self._on_draw)
        self.append(self.drawing_area)

    def add_data_point(self, dl_rate, up_rate):
        self.dl_history.append(dl_rate)
        self.up_history.append(up_rate)
        self.dl_lbl.set_markup(f"<span color='#3584e4'>● DL: {format_speed(dl_rate)}</span>")
        self.up_lbl.set_markup(f"<span color='#e01b24'>● UL: {format_speed(up_rate)}</span>")
        self.drawing_area.queue_draw()

    def _on_draw(self, area, cr, width, height):
        # Background
        cr.set_source_rgba(0.12, 0.12, 0.12, 0.2)
        cr.rectangle(0, 0, width, height)
        cr.fill()

        # Grid lines
        cr.set_source_rgba(0.5, 0.5, 0.5, 0.15)
        cr.set_line_width(1.0)
        for y in range(4):
            y_pos = height * (y + 1) / 5
            cr.move_to(0, y_pos)
            cr.line_to(width, y_pos)
            cr.stroke()

        max_val = max(max(self.dl_history), max(self.up_history), 1024)
        n = len(self.dl_history)
        if n < 2:
            return

        step_x = width / (n - 1)

        # Draw Download line (Blue: #3584e4)
        cr.set_source_rgba(0.21, 0.52, 0.89, 0.9)
        cr.set_line_width(2.0)
        for i, val in enumerate(self.dl_history):
            x = i * step_x
            y = height - (val / max_val * (height - 20)) - 10
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.stroke()

        # Draw Upload line (Red/Orange: #e01b24)
        cr.set_source_rgba(0.88, 0.11, 0.14, 0.9)
        cr.set_line_width(2.0)
        for i, val in enumerate(self.up_history):
            x = i * step_x
            y = height - (val / max_val * (height - 20)) - 10
            if i == 0:
                cr.move_to(x, y)
            else:
                cr.line_to(x, y)
        cr.stroke()
