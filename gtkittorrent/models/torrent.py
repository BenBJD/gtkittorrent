import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GObject
from ..utils.formatters import (
    format_bytes,
    format_speed,
    format_eta,
    format_timestamp,
    format_duration,
    format_ratio,
    format_percent,
    get_state_display
)

class TorrentItem(GObject.Object):
    """GObject representing a qBittorrent torrent item with observable properties."""

    hash = GObject.Property(type=str, default="")
    name = GObject.Property(type=str, default="")
    size = GObject.Property(type=GObject.TYPE_INT64, default=0)
    progress = GObject.Property(type=float, default=0.0)
    state = GObject.Property(type=str, default="")
    priority = GObject.Property(type=int, default=0)
    dlspeed = GObject.Property(type=GObject.TYPE_INT64, default=0)
    upspeed = GObject.Property(type=GObject.TYPE_INT64, default=0)
    eta = GObject.Property(type=GObject.TYPE_INT64, default=0)
    ratio = GObject.Property(type=float, default=0.0)
    num_seeds = GObject.Property(type=int, default=0)
    num_complete = GObject.Property(type=int, default=0)
    num_leechs = GObject.Property(type=int, default=0)
    num_incomplete = GObject.Property(type=int, default=0)
    category = GObject.Property(type=str, default="")
    tags = GObject.Property(type=str, default="")
    added_on = GObject.Property(type=GObject.TYPE_INT64, default=0)
    completion_on = GObject.Property(type=GObject.TYPE_INT64, default=0)
    save_path = GObject.Property(type=str, default="")
    downloaded = GObject.Property(type=GObject.TYPE_INT64, default=0)
    uploaded = GObject.Property(type=GObject.TYPE_INT64, default=0)
    time_active = GObject.Property(type=GObject.TYPE_INT64, default=0)

    # Formatted strings for display
    priority_str = GObject.Property(type=str, default="*")
    size_str = GObject.Property(type=str, default="0 B")
    progress_str = GObject.Property(type=str, default="0.0%")
    state_str = GObject.Property(type=str, default="")
    state_icon = GObject.Property(type=str, default="dialog-information-symbolic")
    dlspeed_str = GObject.Property(type=str, default="0 B/s")
    upspeed_str = GObject.Property(type=str, default="0 B/s")
    eta_str = GObject.Property(type=str, default="∞")
    ratio_str = GObject.Property(type=str, default="0.00")
    seeds_str = GObject.Property(type=str, default="0 (0)")
    peers_str = GObject.Property(type=str, default="0 (0)")
    added_on_str = GObject.Property(type=str, default="—")
    completion_on_str = GObject.Property(type=str, default="—")

    def __init__(self, torrent_data=None):
        super().__init__()
        self.raw_data = {}
        if torrent_data:
            self.hash = torrent_data.get('hash', '')
            self.update(torrent_data)

    def update(self, torrent_data):
        self.raw_data.update(torrent_data)

        name = torrent_data.get('name', self.name)
        if name != self.name:
            self.name = name

        size = torrent_data.get('size', self.size)
        if size != self.size or not self.size_str:
            self.size = size
            self.size_str = format_bytes(size)

        progress = float(torrent_data.get('progress', self.progress))
        if abs(progress - self.progress) > 1e-4 or not self.progress_str:
            self.progress = progress
            self.progress_str = format_percent(progress)

        state = torrent_data.get('state', self.state)
        if state != self.state or not self.state_str:
            self.state = state
            disp, icon = get_state_display(state)
            self.state_str = disp
            self.state_icon = icon

        priority = torrent_data.get('priority', self.priority)
        if priority != self.priority or self.priority_str == "*":
            self.priority = priority
            self.priority_str = str(priority) if priority > 0 else "*"

        dlspeed = torrent_data.get('dlspeed', self.dlspeed)
        if dlspeed != self.dlspeed:
            self.dlspeed = dlspeed
            self.dlspeed_str = format_speed(dlspeed)

        upspeed = torrent_data.get('upspeed', self.upspeed)
        if upspeed != self.upspeed:
            self.upspeed = upspeed
            self.upspeed_str = format_speed(upspeed)

        eta = torrent_data.get('eta', self.eta)
        if eta != self.eta:
            self.eta = eta
            self.eta_str = format_eta(eta)

        ratio = float(torrent_data.get('ratio', self.ratio))
        if abs(ratio - self.ratio) > 1e-4:
            self.ratio = ratio
            self.ratio_str = format_ratio(ratio)

        num_seeds = torrent_data.get('num_seeds', self.num_seeds)
        num_complete = torrent_data.get('num_complete', self.num_complete)
        if num_seeds != self.num_seeds or num_complete != self.num_complete:
            self.num_seeds = num_seeds
            self.num_complete = num_complete
            self.seeds_str = f"{num_seeds} ({num_complete})"

        num_leechs = torrent_data.get('num_leechs', self.num_leechs)
        num_incomplete = torrent_data.get('num_incomplete', self.num_incomplete)
        if num_leechs != self.num_leechs or num_incomplete != self.num_incomplete:
            self.num_leechs = num_leechs
            self.num_incomplete = num_incomplete
            self.peers_str = f"{num_leechs} ({num_incomplete})"

        cat = torrent_data.get('category', self.category)
        if cat != self.category:
            self.category = cat or ""

        tags = torrent_data.get('tags', self.tags)
        if tags != self.tags:
            self.tags = tags or ""

        added = torrent_data.get('added_on', self.added_on)
        if added != self.added_on:
            self.added_on = added
            self.added_on_str = format_timestamp(added)

        completed = torrent_data.get('completion_on', self.completion_on)
        if completed != self.completion_on:
            self.completion_on = completed
            self.completion_on_str = format_timestamp(completed)

        save_path = torrent_data.get('save_path', self.save_path)
        if save_path != self.save_path:
            self.save_path = save_path or ""

        self.downloaded = torrent_data.get('downloaded', self.downloaded)
        self.uploaded = torrent_data.get('uploaded', self.uploaded)
        self.time_active = torrent_data.get('time_active', self.time_active)

    # Status group helper for sidebar filtering
    def matches_status_filter(self, filter_id):
        if not filter_id or filter_id == "all":
            return True
        st = self.state.lower()
        if filter_id == "downloading":
            return "downloading" in st or "metadl" in st or "allocating" in st
        elif filter_id == "seeding":
            return "uploading" in st or "seeding" in st
        elif filter_id == "completed":
            return self.progress >= 1.0 or "up" in st
        elif filter_id == "resumed" or filter_id == "active":
            return (self.dlspeed > 0 or self.upspeed > 0) and not ("paused" in st or "stopped" in st)
        elif filter_id == "paused" or filter_id == "inactive":
            return "paused" in st or "stopped" in st or (self.dlspeed == 0 and self.upspeed == 0)
        elif filter_id == "stalled":
            return "stalled" in st
        elif filter_id == "stalled_dl":
            return st == "stalleddl"
        elif filter_id == "stalled_up":
            return st == "stalledup"
        elif filter_id == "checking":
            return "checking" in st
        elif filter_id == "moving":
            return st == "moving"
        elif filter_id == "errored":
            return "error" in st or "missing" in st
        return True
