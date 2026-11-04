import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GObject
from ..utils.formatters import format_bytes, format_percent

class FileItem(GObject.Object):
    index = GObject.Property(type=int, default=0)
    name = GObject.Property(type=str, default="")
    size = GObject.Property(type=GObject.TYPE_INT64, default=0)
    size_str = GObject.Property(type=str, default="0 B")
    progress = GObject.Property(type=float, default=0.0)
    progress_str = GObject.Property(type=str, default="0.0%")
    priority = GObject.Property(type=int, default=1)  # 0=Do not download, 1=Normal, 6=High, 7=Maximal
    priority_str = GObject.Property(type=str, default="Normal")
    remaining_str = GObject.Property(type=str, default="0 B")

    PRIORITY_NAMES = {
        0: "Do not download",
        1: "Normal",
        6: "High",
        7: "Maximum"
    }

    def __init__(self, data=None):
        super().__init__()
        if data:
            self.update(data)

    def update(self, data):
        self.index = int(data.get('index', self.index))
        self.name = str(data.get('name', self.name))
        sz = int(data.get('size', self.size))
        self.size = sz
        self.size_str = format_bytes(sz)
        
        prog = float(data.get('progress', self.progress))
        self.progress = prog
        self.progress_str = format_percent(prog)

        prio = int(data.get('priority', self.priority))
        self.priority = prio
        self.priority_str = self.PRIORITY_NAMES.get(prio, str(prio))

        rem_bytes = max(0, int(sz * (1.0 - prog)))
        self.remaining_str = format_bytes(rem_bytes)
