import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GObject
from ..utils.formatters import format_bytes, format_speed, format_percent

class PeerItem(GObject.Object):
    ip = GObject.Property(type=str, default="")
    port = GObject.Property(type=int, default=0)
    client = GObject.Property(type=str, default="")
    progress = GObject.Property(type=float, default=0.0)
    progress_str = GObject.Property(type=str, default="0.0%")
    dlspeed = GObject.Property(type=GObject.TYPE_INT64, default=0)
    dlspeed_str = GObject.Property(type=str, default="0 B/s")
    upspeed = GObject.Property(type=GObject.TYPE_INT64, default=0)
    upspeed_str = GObject.Property(type=str, default="0 B/s")
    downloaded_str = GObject.Property(type=str, default="0 B")
    uploaded_str = GObject.Property(type=str, default="0 B")
    flags = GObject.Property(type=str, default="")
    relevance = GObject.Property(type=float, default=0.0)
    country = GObject.Property(type=str, default="")

    def __init__(self, data=None):
        super().__init__()
        if data:
            self.update(data)

    def update(self, data):
        self.ip = str(data.get('ip', self.ip))
        self.port = int(data.get('port', self.port))
        self.client = str(data.get('client', self.client))
        prog = float(data.get('progress', self.progress))
        self.progress = prog
        self.progress_str = format_percent(prog)
        
        dl = data.get('dl_speed', data.get('dlspeed', self.dlspeed))
        self.dlspeed = dl
        self.dlspeed_str = format_speed(dl)

        up = data.get('up_speed', data.get('upspeed', self.upspeed))
        self.upspeed = up
        self.upspeed_str = format_speed(up)

        self.downloaded_str = format_bytes(data.get('downloaded', 0))
        self.uploaded_str = format_bytes(data.get('uploaded', 0))
        self.flags = str(data.get('flags', self.flags))
        self.relevance = float(data.get('relevance', self.relevance))
        self.country = str(data.get('country', self.country))
