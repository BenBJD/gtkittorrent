import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GObject
from ..utils.formatters import format_bytes

class TrackerItem(GObject.Object):
    tier = GObject.Property(type=str, default="0")
    url = GObject.Property(type=str, default="")
    status = GObject.Property(type=str, default="")
    peers = GObject.Property(type=int, default=0)
    seeds = GObject.Property(type=int, default=0)
    leeches = GObject.Property(type=int, default=0)
    downloaded = GObject.Property(type=int, default=0)
    msg = GObject.Property(type=str, default="")

    def __init__(self, data=None):
        super().__init__()
        if data:
            self.update(data)

    def update(self, data):
        self.tier = str(data.get('tier', self.tier))
        self.url = str(data.get('url', self.url))
        self.status = str(data.get('status', self.status))
        self.peers = int(data.get('num_peers', self.peers))
        self.seeds = int(data.get('num_seeds', self.seeds))
        self.leeches = int(data.get('num_leeches', self.leeches))
        self.downloaded = int(data.get('num_downloaded', self.downloaded))
        self.msg = str(data.get('msg', self.msg))
