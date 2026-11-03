import unittest
from unittest.mock import MagicMock
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from client import QBittorrentClient
from window import MainWindow

class TestGTKittorrent(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock(spec=QBittorrentClient)
        self.app = Adw.Application(application_id="test.app")
        self.app.settings = MagicMock()
        # Mock settings.get to return some defaults
        def get_setting(key, default=None):
            defaults = {
                "host_ip": "127.0.0.1",
                "port": "8080",
                "username": "admin",
                "password": "password",
                "use_https": False
            }
            return defaults.get(key, default if default is not None else "test")
        self.app.settings.get.side_effect = get_setting
        
        # We need to wrap it in a dummy activate to avoid issues
        self.app.connect("activate", lambda x: None)

    def test_window_creation(self):
        # Mock torrent data
        self.mock_client.get_torrents.return_value = [
            {'hash': '123', 'name': 'Test Torrent', 'size': 1000000, 'progress': 0.5, 'state': 'downloading', 'dlspeed': 50000}
        ]
        self.mock_client.get_torrent_properties.return_value = {'save_path': '/tmp', 'addition_date': 123456789}
        self.mock_client.get_torrent_trackers.return_value = []
        self.mock_client.get_torrent_contents.return_value = []
        
        # We need to run this in a context where GTK is initialized
        # but since we're just testing instantiation, it might work
        win = MainWindow(self.app, self.mock_client)
        self.assertIsNotNone(win)
        self.assertEqual(win.get_title(), "GTKittorrent")
        
        # Check if model has the item
        self.assertEqual(win.model.get_n_items(), 1)
        item = win.model.get_item(0)
        self.assertEqual(item.name, 'Test Torrent')

    def test_details_panel(self):
        self.mock_client.get_torrents.return_value = [
            {'hash': '123', 'name': 'Test Torrent', 'size': 1000000}
        ]
        self.mock_client.get_torrent_properties.return_value = {'save_path': '/tmp/test', 'comment': 'Test Comment'}
        self.mock_client.get_torrent_trackers.return_value = [{'url': 'http://tracker.com', 'status': 'working'}]
        self.mock_client.get_torrent_contents.return_value = [{'name': 'file1.bin', 'size': 1000000}]

        win = MainWindow(self.app, self.mock_client)
        item = win.model.get_item(0)
        
        # Select item
        win.selection_model.select_item(0, True)
        
        # Check details panel
        self.assertEqual(win.details_panel.torrent_hash, '123')
        self.assertIn('/tmp/test', win.details_panel.general_label.get_text())
        self.assertIn('working', win.details_panel.trackers_label.get_text())
        self.assertIn('file1.bin', win.details_panel.content_label.get_text())

    def test_format_speed(self):
        win = MainWindow(self.app, self.mock_client)
        self.assertEqual(win.format_speed(500), "500 B/s")
        self.assertEqual(win.format_speed(1500), "1.5 KB/s")
        self.assertEqual(win.format_speed(1500000), "1.4 MB/s")

if __name__ == "__main__":
    unittest.main()
