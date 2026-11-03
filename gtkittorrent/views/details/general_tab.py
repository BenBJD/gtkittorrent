import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk
from ...utils.formatters import (
    format_bytes,
    format_speed,
    format_eta,
    format_timestamp,
    format_duration,
    format_ratio
)

class GeneralTab(Gtk.ScrolledWindow):
    """General tab showing organized Transfer and Information sections."""

    def __init__(self, client):
        super().__init__(hexpand=True, vexpand=True)
        self.client = client
        self.torrent_hash = None

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, margin_top=12, margin_bottom=12, margin_start=16, margin_end=16)
        self.set_child(main_box)

        # Transfer Group
        lbl_transfer = Gtk.Label(label="<b>Transfer</b>", use_markup=True, xalign=0)
        main_box.append(lbl_transfer)

        grid_transfer = Gtk.Grid(column_spacing=24, row_spacing=6)
        main_box.append(grid_transfer)

        self.lbl_elapsed = self._add_grid_row(grid_transfer, 0, "Time Elapsed:")
        self.lbl_eta = self._add_grid_row(grid_transfer, 1, "ETA:")
        self.lbl_downloaded = self._add_grid_row(grid_transfer, 2, "Downloaded:")
        self.lbl_uploaded = self._add_grid_row(grid_transfer, 3, "Uploaded:")
        self.lbl_seeds = self._add_grid_row(grid_transfer, 4, "Seeds:")
        self.lbl_peers = self._add_grid_row(grid_transfer, 5, "Peers:")
        self.lbl_dlspeed = self._add_grid_row(grid_transfer, 6, "Download Speed:")
        self.lbl_upspeed = self._add_grid_row(grid_transfer, 7, "Upload Speed:")
        self.lbl_ratio = self._add_grid_row(grid_transfer, 8, "Share Ratio:")
        self.lbl_reannounce = self._add_grid_row(grid_transfer, 9, "Reannounce In:")

        # Separator
        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        # Information Group
        lbl_info = Gtk.Label(label="<b>Information</b>", use_markup=True, xalign=0)
        main_box.append(lbl_info)

        grid_info = Gtk.Grid(column_spacing=24, row_spacing=6)
        main_box.append(grid_info)

        self.lbl_size = self._add_grid_row(grid_info, 0, "Total Size:")
        self.lbl_pieces = self._add_grid_row(grid_info, 1, "Pieces:")
        self.lbl_save_path = self._add_grid_row(grid_info, 2, "Save Path:")
        self.lbl_hash = self._add_grid_row(grid_info, 3, "Hash:")
        self.lbl_added_on = self._add_grid_row(grid_info, 4, "Added On:")
        self.lbl_completion_on = self._add_grid_row(grid_info, 5, "Completed On:")
        self.lbl_created_by = self._add_grid_row(grid_info, 6, "Created By:")
        self.lbl_comment = self._add_grid_row(grid_info, 7, "Comment:")

    def _add_grid_row(self, grid, row, label_text):
        lbl_name = Gtk.Label(label=f"<span color='gray'>{label_text}</span>", use_markup=True, xalign=0)
        lbl_val = Gtk.Label(label="—", xalign=0, selectable=True)
        lbl_val.set_wrap(True)
        col = (row % 2) * 2
        r = row // 2
        grid.attach(lbl_name, col, r, 1, 1)
        grid.attach(lbl_val, col + 1, r, 1, 1)
        return lbl_val

    def update(self, torrent_item):
        if not torrent_item:
            self.torrent_hash = None
            self._clear()
            return

        self.torrent_hash = torrent_item.hash
        props = self.client.get_torrent_properties(self.torrent_hash) if self.client else {}

        # Transfer fields
        elapsed = props.get('time_elapsed', torrent_item.time_active)
        self.lbl_elapsed.set_text(format_duration(elapsed))
        self.lbl_eta.set_text(format_eta(props.get('eta', torrent_item.eta)))
        
        dl_bytes = props.get('total_downloaded', torrent_item.downloaded)
        self.lbl_downloaded.set_text(format_bytes(dl_bytes))

        up_bytes = props.get('total_uploaded', torrent_item.uploaded)
        self.lbl_uploaded.set_text(format_bytes(up_bytes))

        self.lbl_seeds.set_text(f"{props.get('seeds', torrent_item.num_seeds)} ({props.get('seeds_total', torrent_item.num_complete)})")
        self.lbl_peers.set_text(f"{props.get('peers', torrent_item.num_leechs)} ({props.get('peers_total', torrent_item.num_incomplete)})")

        self.lbl_dlspeed.set_text(format_speed(props.get('dl_speed', torrent_item.dlspeed)))
        self.lbl_upspeed.set_text(format_speed(props.get('up_speed', torrent_item.upspeed)))
        self.lbl_ratio.set_text(format_ratio(props.get('share_ratio', torrent_item.ratio)))

        reannounce = props.get('reannounce', 0)
        self.lbl_reannounce.set_text(format_duration(reannounce) if reannounce > 0 else "—")

        # Information fields
        self.lbl_size.set_text(format_bytes(props.get('total_size', torrent_item.size)))
        pieces_num = props.get('pieces_num', 0)
        piece_size = props.get('piece_size', 0)
        if pieces_num > 0:
            self.lbl_pieces.set_text(f"{pieces_num} x {format_bytes(piece_size)}")
        else:
            self.lbl_pieces.set_text("—")

        self.lbl_save_path.set_text(props.get('save_path', torrent_item.save_path) or "—")
        self.lbl_hash.set_text(self.torrent_hash or "—")
        self.lbl_added_on.set_text(format_timestamp(props.get('addition_date', torrent_item.added_on)))
        self.lbl_completion_on.set_text(format_timestamp(props.get('completion_date', torrent_item.completion_on)))
        self.lbl_created_by.set_text(props.get('created_by', '') or "—")
        self.lbl_comment.set_text(props.get('comment', '') or "—")

    def _clear(self):
        for lbl in (self.lbl_elapsed, self.lbl_eta, self.lbl_downloaded, self.lbl_uploaded,
                    self.lbl_seeds, self.lbl_peers, self.lbl_dlspeed, self.lbl_upspeed,
                    self.lbl_ratio, self.lbl_reannounce, self.lbl_size, self.lbl_pieces,
                    self.lbl_save_path, self.lbl_hash, self.lbl_added_on, self.lbl_completion_on,
                    self.lbl_created_by, self.lbl_comment):
            lbl.set_text("—")
