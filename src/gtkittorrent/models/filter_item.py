import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GObject

class FilterItem(GObject.Object):
    id = GObject.Property(type=str, default="")
    name = GObject.Property(type=str, default="")
    count = GObject.Property(type=int, default=0)
    icon_name = GObject.Property(type=str, default="folder-symbolic")
    filter_type = GObject.Property(type=str, default="status")  # 'status', 'category', 'tag', 'tracker'

    def __init__(self, filter_id="", name="", count=0, icon_name="folder-symbolic", filter_type="status"):
        super().__init__()
        self.id = filter_id
        self.name = name
        self.count = count
        self.icon_name = icon_name
        self.filter_type = filter_type
