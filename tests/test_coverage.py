import io
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk

from gtkittorrent.models.file_item import FileItem
from gtkittorrent.models.filter_item import FilterItem
from gtkittorrent.models.peer import PeerItem
from gtkittorrent.models.tracker import TrackerItem
from gtkittorrent.models.torrent import TorrentItem
from gtkittorrent.views.details.general_tab import GeneralTab
from gtkittorrent.views.details.peers_tab import PeersTab
from gtkittorrent.views.details.log_tab import LogTab, LogItem
from gtkittorrent.views.dialogs.simple_dialogs import (
    CategoryDialog,
    TagDialog,
    LocationDialog,
    SpeedLimitDialog,
)
from gtkittorrent.views.dialogs.preferences_dialog import PreferencesDialog
from gtkittorrent.client.client import QBittorrentClient


class TestModels(unittest.TestCase):
    def test_file_item(self):
        item = FileItem({
            "index": 2,
            "name": "folder/ubuntu.iso",
            "size": 1000,
            "progress": 0.25,
            "priority": 6,
        })
        self.assertEqual(item.index, 2)
        self.assertEqual(item.name, "folder/ubuntu.iso")
        self.assertEqual(item.size, 1000)
        self.assertEqual(item.priority, 6)
        self.assertEqual(item.priority_str, "High")
        self.assertEqual(item.progress_str, "25.0%")
        self.assertEqual(item.remaining_str, "750 B")

        item.update({"priority": 0, "progress": 1.0})
        self.assertEqual(item.priority_str, "Do not download")
        self.assertEqual(item.remaining_str, "0 B")

    def test_filter_item(self):
        fi = FilterItem("downloading", "Downloading", 5, "folder-download-symbolic", "status")
        self.assertEqual(fi.id, "downloading")
        self.assertEqual(fi.name, "Downloading")
        self.assertEqual(fi.count, 5)
        self.assertEqual(fi.icon_name, "folder-download-symbolic")
        self.assertEqual(fi.filter_type, "status")

    def test_peer_item(self):
        peer = PeerItem({
            "ip": "1.2.3.4",
            "port": 51413,
            "client": "qBittorrent/5.0",
            "progress": 0.5,
            "dl_speed": 2048,
            "up_speed": 1024,
            "downloaded": 4096,
            "uploaded": 2048,
            "flags": "D E",
            "relevance": 0.8,
            "country": "GB",
        })
        self.assertEqual(peer.ip, "1.2.3.4")
        self.assertEqual(peer.port, 51413)
        self.assertEqual(peer.client, "qBittorrent/5.0")
        self.assertEqual(peer.progress_str, "50.0%")
        self.assertEqual(peer.dlspeed_str, "2.0 KiB/s")
        self.assertEqual(peer.upspeed_str, "1.0 KiB/s")
        self.assertEqual(peer.downloaded_str, "4.0 KiB")
        self.assertEqual(peer.uploaded_str, "2.0 KiB")
        self.assertEqual(peer.flags, "D E")
        self.assertEqual(peer.country, "GB")

    def test_tracker_item(self):
        trk = TrackerItem({
            "tier": 1,
            "url": "udp://tracker.example.com:80/announce",
            "status": 2,
            "num_peers": 10,
            "num_seeds": 5,
            "num_leeches": 3,
            "num_downloaded": 42,
            "msg": "Working",
        })
        self.assertEqual(trk.tier, "1")
        self.assertEqual(trk.url, "udp://tracker.example.com:80/announce")
        self.assertEqual(trk.peers, 10)
        self.assertEqual(trk.seeds, 5)
        self.assertEqual(trk.leeches, 3)
        self.assertEqual(trk.downloaded, 42)
        self.assertEqual(trk.msg, "Working")


class TestDetailsTabsExtra(unittest.TestCase):
    def test_general_tab_update_and_clear(self):
        mock_client = MagicMock()
        mock_client.get_torrent_properties.return_value = {
            "time_elapsed": 120,
            "eta": 60,
            "total_downloaded": 1024,
            "total_uploaded": 512,
            "seeds": 3,
            "seeds_total": 10,
            "peers": 2,
            "peers_total": 8,
            "dl_speed": 2048,
            "up_speed": 1024,
            "share_ratio": 0.5,
            "reannounce": 300,
            "total_size": 4096,
            "pieces_num": 4,
            "piece_size": 1024,
            "save_path": "/downloads/ubuntu",
            "addition_date": 1700000000,
            "completion_date": 1700000100,
            "created_by": "mktorrent",
            "comment": "Test comment",
        }
        tab = GeneralTab(mock_client)
        torrent = TorrentItem({"hash": "abc123", "name": "Ubuntu"})
        tab.update(torrent)

        self.assertEqual(tab.lbl_hash.get_text(), "abc123")
        self.assertEqual(tab.lbl_save_path.get_text(), "/downloads/ubuntu")
        self.assertEqual(tab.lbl_created_by.get_text(), "mktorrent")
        self.assertEqual(tab.lbl_comment.get_text(), "Test comment")
        self.assertIn("4 x", tab.lbl_pieces.get_text())

        tab.update(None)
        self.assertEqual(tab.lbl_hash.get_text(), "—")
        self.assertEqual(tab.lbl_comment.get_text(), "—")

    def test_peers_tab_sync_update_and_remove(self):
        mock_client = MagicMock()
        mock_client.sync_torrent_peers.side_effect = [
            {
                "rid": 1,
                "peers": {
                    "1.1.1.1:80": {"ip": "1.1.1.1", "port": 80, "dl_speed": 100},
                    "2.2.2.2:80": {"ip": "2.2.2.2", "port": 80, "dl_speed": 200},
                },
                "peers_removed": [],
            },
            {
                "rid": 2,
                "peers": {"1.1.1.1:80": {"dl_speed": 500}},
                "peers_removed": ["2.2.2.2:80"],
            },
        ]
        tab = PeersTab(mock_client)
        torrent = TorrentItem({"hash": "h1"})
        tab.update(torrent)
        self.assertEqual(tab.model.get_n_items(), 2)
        self.assertEqual(tab.peer_rid, 1)

        tab.update(torrent)
        self.assertEqual(tab.model.get_n_items(), 1)
        self.assertEqual(tab.model.get_item(0).dlspeed, 500)

        tab.update(None)
        self.assertEqual(tab.model.get_n_items(), 0)

    def test_log_tab_filtering_and_refresh(self):
        li = LogItem({"id": 10, "timestamp": 1700000000000, "message": "Warn msg", "type": 4})
        self.assertEqual(li.type_str, "Warning")
        self.assertEqual(li.message, "Warn msg")

        mock_client = MagicMock()
        mock_client.get_logs.return_value = [
            {"id": 1, "timestamp": 1700000000000, "message": "Started", "type": 1},
            {"id": 2, "timestamp": 1700000005000, "message": "Crit", "type": 8},
        ]
        tab = LogTab(mock_client)
        tab.refresh_logs()
        self.assertEqual(tab.model.get_n_items(), 2)
        self.assertEqual(tab.last_log_id, 2)
        self.assertEqual(tab.model.get_item(1).type_str, "Critical")


class TestSimpleDialogs(unittest.TestCase):
    def test_category_dialog(self):
        dlg = CategoryDialog(None, "Movies", "/dl/movies", is_edit=False)
        self.assertEqual(dlg.get_data(), ("Movies", "/dl/movies"))
        self.assertTrue(dlg.name_entry.get_sensitive())
        dlg.destroy()

        edit_dlg = CategoryDialog(None, "Movies", "/dl/movies", is_edit=True)
        self.assertFalse(edit_dlg.name_entry.get_sensitive())
        edit_dlg.destroy()

    def test_tag_dialog(self):
        dlg = TagDialog(None)
        self.assertEqual(dlg.get_tags(), [])
        dlg.entry.set_text("linux, iso , , fast")
        self.assertEqual(dlg.get_tags(), ["linux", "iso", "fast"])
        dlg.destroy()

    def test_location_dialog(self):
        dlg = LocationDialog(None, "/old/path")
        self.assertEqual(dlg.get_location(), "/old/path")
        with patch("gtkittorrent.views.dialogs.simple_dialogs.Gtk.FileChooserNative") as mock_fc_cls:
            mock_fc = MagicMock()
            mock_fc_cls.return_value = mock_fc

            def fake_connect(sig, cb):
                if sig == "response":
                    f = MagicMock()
                    f.get_path.return_value = "/new/path"
                    mock_fc.get_file.return_value = f
                    cb(mock_fc, Gtk.ResponseType.ACCEPT)

            mock_fc.connect.side_effect = fake_connect
            dlg._on_browse(None)
            self.assertEqual(dlg.get_location(), "/new/path")
        dlg.destroy()

    def test_speed_limit_dialog(self):
        dlg = SpeedLimitDialog(None, current_dl=2048, current_up=0)
        self.assertEqual(dlg.get_limits(), (2048, 0))
        dlg.dl_spin.set_value(10)
        dlg.up_spin.set_value(5)
        self.assertEqual(dlg.get_limits(), (10240, 5120))
        dlg.destroy()


class TestPreferencesDialogFullSave(unittest.TestCase):
    def test_preferences_dialog_qbt5_and_qbt4_save(self):
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda k, d=None: "127.0.0.1" if "ip" in k else "8080"
        mock_client = MagicMock()
        mock_client.get_app_preferences.return_value = {
            "listen_port": 6881,
            "upnp": True,
            "max_connec": 200,
            "max_connec_per_torrent": 50,
            "max_uploads": 20,
            "max_uploads_per_torrent": 5,
            "bittorrent_protocol": 1,
            "save_path": "/dl",
            "temp_path_enabled": False,
            "temp_path": "/tmp",
            "torrent_content_layout": "Subfolder",
            "add_to_top_of_queue": True,
            "add_stopped_enabled": True,
            "auto_tmm_enabled": True,
            "category_changed_tmm_enabled": True,
            "dl_limit": 10240,
            "up_limit": 5120,
            "alt_dl_limit": 2048,
            "alt_up_limit": 1024,
            "scheduler_enabled": True,
            "schedule_from_hour": 8,
            "schedule_from_min": 30,
            "schedule_to_hour": 22,
            "schedule_to_min": 0,
            "scheduler_days": 1,
            "dht": True,
            "pex": True,
            "lsd": False,
            "encryption": 1,
            "anonymous_mode": True,
            "max_ratio_enabled": True,
            "max_ratio": 2.0,
            "max_seeding_time_enabled": True,
            "max_seeding_time": 120,
            "max_inactive_seeding_time_enabled": False,
            "max_inactive_seeding_time": 60,
            "share_limits_mode": 1,
            "max_ratio_act": 1,
            "queueing_enabled": True,
            "max_active_downloads": 4,
            "max_active_uploads": 4,
            "max_active_torrents": 8,
        }

        dlg = PreferencesDialog(None, mock_settings, mock_client)
        self.assertTrue(dlg._is_qbt5())
        dlg._on_close()

        mock_client.set_app_preferences.assert_called_once()
        saved = mock_client.set_app_preferences.call_args[0][0]
        self.assertEqual(saved["listen_port"], 6881)
        self.assertEqual(saved["torrent_content_layout"], "Subfolder")
        self.assertTrue(saved["add_stopped_enabled"])
        self.assertTrue(saved["category_changed_tmm_enabled"])
        self.assertEqual(saved["share_limits_mode"], 1)
        self.assertEqual(saved["dl_limit"], 10240)
        self.assertNotIn("start_paused_enabled", saved)

        # qBittorrent 4.x key path
        mock_client.reset_mock()
        mock_client.get_app_preferences.return_value = {
            "start_paused_enabled": True,
            "torrent_changed_tmm_enabled": True,
        }
        dlg4 = PreferencesDialog(None, mock_settings, mock_client)
        self.assertFalse(dlg4._is_qbt5())
        dlg4._on_close()
        saved4 = mock_client.set_app_preferences.call_args[0][0]
        self.assertTrue(saved4["start_paused_enabled"])
        self.assertTrue(saved4["torrent_changed_tmm_enabled"])

    def test_preferences_fetch_trackers_worker(self):
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda k, d=None: "127.0.0.1" if "ip" in k else "8080"
        mock_client = MagicMock()
        mock_client.get_app_preferences.return_value = {}

        dlg = PreferencesDialog(None, mock_settings, mock_client)
        dlg.add_trackers_url_entry.set_text("https://example.com/trackers.txt")

        fake_resp = MagicMock()
        fake_resp.__enter__ = MagicMock(return_value=io.BytesIO(b"udp://a:80\nudp://b:80\n"))
        fake_resp.__exit__ = MagicMock(return_value=False)

        with patch("gtkittorrent.views.dialogs.preferences_dialog.urllib.request.urlopen", return_value=fake_resp), \
             patch("gtkittorrent.views.dialogs.preferences_dialog.GLib.idle_add", side_effect=lambda fn, *a: fn(*a)), \
             patch("gtkittorrent.views.dialogs.preferences_dialog.threading.Thread") as mock_thread:
            mock_thread.side_effect = lambda target, daemon=True: MagicMock(start=target)
            dlg._on_fetch_trackers_clicked()

        self.assertEqual(dlg.add_trackers_url_status_row.get_subtitle(), "2 trackers")


class TestClientExtraAndAppOpen(unittest.TestCase):
    @patch("gtkittorrent.client.client.qbittorrentapi.Client")
    def test_additional_client_methods(self, mock_api_cls):
        mock_api = mock_api_cls.return_value
        client = QBittorrentClient()

        self.assertTrue(client.set_auto_management(["h1"], enable=True))
        mock_api.torrents_set_auto_management.assert_called_with(enable=True, torrent_hashes=["h1"])

        self.assertTrue(client.create_category("ISO", "/dl/iso"))
        self.assertTrue(client.edit_category("ISO", "/dl/iso2"))
        self.assertTrue(client.remove_categories(["ISO"]))
        self.assertTrue(client.create_tags(["fast"]))
        self.assertTrue(client.delete_tags(["fast"]))
        self.assertTrue(client.edit_tracker("h1", "http://a", "http://b"))
        self.assertTrue(client.remove_trackers("h1", ["http://b"]))

        mock_api.app_get_free_space_at_path.return_value = 12345
        self.assertEqual(client.get_free_space("/dl"), 12345)

        mock_api.app_version.return_value = "v5.0.0"
        self.assertEqual(client.get_version(), "v5.0.0")

        mock_api.log_main.return_value = [{"id": 1, "message": "ok"}]
        self.assertEqual(len(client.get_logs()), 1)

        mock_api.torrents_set_auto_management.side_effect = RuntimeError("boom")
        self.assertFalse(client.set_auto_management(["h1"]))

    def test_app_do_open_routes_torrent_and_magnet(self):
        from gtkittorrent.app import GTKittorrentApp

        app = MagicMock(spec=GTKittorrentApp)
        app.win = Gtk.Window()
        app.client = MagicMock()

        f_torrent = MagicMock()
        f_torrent.get_path.return_value = "/tmp/ubuntu.torrent"
        f_torrent.get_uri.return_value = "file:///tmp/ubuntu.torrent"

        f_magnet = MagicMock()
        f_magnet.get_path.return_value = None
        f_magnet.get_uri.return_value = "magnet:///?xt=urn:btih:1234"

        with patch("gtkittorrent.views.dialogs.add_torrent_dialog.AddTorrentDialog") as mock_dlg_cls:
            mock_dlg = MagicMock()
            mock_dlg_cls.return_value = mock_dlg
            GTKittorrentApp.do_open(app, [f_torrent, f_magnet], 2, "")

            self.assertEqual(mock_dlg_cls.call_count, 2)
            mock_dlg_cls.assert_any_call(app.win, app.client, torrent_file="/tmp/ubuntu.torrent")
            mock_dlg_cls.assert_any_call(app.win, app.client, torrent_url="magnet:?xt=urn:btih:1234")
            self.assertEqual(mock_dlg.present.call_count, 2)

        app.win.destroy()
