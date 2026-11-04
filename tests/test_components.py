import unittest
import tempfile
from unittest.mock import MagicMock, patch
import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, GObject

from gtkittorrent.utils.formatters import (
    format_bytes,
    format_speed,
    format_eta,
    format_timestamp,
    format_duration,
    format_ratio,
    format_percent,
    get_state_display
)
from gtkittorrent.models.torrent import TorrentItem
from gtkittorrent.models.tracker import TrackerItem
from gtkittorrent.models.peer import PeerItem
from gtkittorrent.models.file_item import FileItem
from gtkittorrent.client import QBittorrentClient
from gtkittorrent.views.torrent_table import TorrentTable
from gtkittorrent.views.sidebar import Sidebar
from gtkittorrent.views.details.speed_tab import SpeedTab
from gtkittorrent.views.details.log_tab import LogTab
from gtkittorrent.views.details.content_tab import ContentTab
from gtkittorrent.views.details.trackers_tab import TrackersTab
from gtkittorrent.views.details.peers_tab import PeersTab
from gtkittorrent.views.welcome_window import WelcomeWindow
from gtkittorrent.settings import Settings
from gtkittorrent.views.dialogs import (
    AddTorrentDialog,
    PreferencesDialog,
    InstanceDialog,
    CategoryDialog,
    TagDialog,
    LocationDialog,
    SpeedLimitDialog
)

class TestFormatters(unittest.TestCase):
    def test_format_bytes(self):
        self.assertEqual(format_bytes(0), "0 B")
        self.assertEqual(format_bytes(512), "512 B")
        self.assertEqual(format_bytes(1024), "1.0 KiB")
        self.assertEqual(format_bytes(1048576), "1.0 MiB")
        self.assertEqual(format_bytes(1073741824), "1.0 GiB")
        self.assertEqual(format_bytes(-5), "0 B")
        self.assertEqual(format_bytes(None), "0 B")

    def test_format_speed(self):
        self.assertEqual(format_speed(0), "0 B/s")
        self.assertEqual(format_speed(1024), "1.0 KiB/s")
        self.assertEqual(format_speed(5242880), "5.0 MiB/s")

    def test_format_eta(self):
        self.assertEqual(format_eta(0), "0s")
        self.assertEqual(format_eta(45), "45s")
        self.assertEqual(format_eta(125), "2m 5s")
        self.assertEqual(format_eta(3665), "1h 1m")
        self.assertEqual(format_eta(90000), "1d 1h")
        self.assertEqual(format_eta(8640000), "∞")
        self.assertEqual(format_eta(-1), "∞")

    def test_format_ratio(self):
        self.assertEqual(format_ratio(0.0), "0.00")
        self.assertEqual(format_ratio(1.5432), "1.54")
        self.assertEqual(format_ratio(10001), "∞")
        self.assertEqual(format_ratio(-1), "—")

    def test_get_state_display(self):
        disp, icon = get_state_display("downloading")
        self.assertEqual(disp, "Downloading")
        self.assertEqual(icon, "folder-download-symbolic")

        disp, icon = get_state_display("uploading")
        self.assertEqual(disp, "Seeding")


class TestTorrentModel(unittest.TestCase):
    def test_torrent_item(self):
        data = {
            'hash': 'abc123',
            'name': 'Linux ISO',
            'size': 2147483648,
            'progress': 0.75,
            'state': 'downloading',
            'dlspeed': 2097152,
            'upspeed': 1048576,
            'eta': 500,
            'ratio': 0.5,
            'category': 'ISOs',
            'tags': 'linux, fedora',
            'added_on': 1600000000,
            'completion_on': 0,
            'save_path': '/home/downloads'
        }
        item = TorrentItem(data)
        self.assertEqual(item.hash, 'abc123')
        self.assertEqual(item.name, 'Linux ISO')
        self.assertEqual(item.size, 2147483648)
        self.assertEqual(item.size_str, '2.0 GiB')
        self.assertAlmostEqual(item.progress, 0.75)
        self.assertEqual(item.progress_str, '75.0%')
        self.assertEqual(item.state, 'downloading')
        self.assertEqual(item.state_str, 'Downloading')
        self.assertEqual(item.dlspeed_str, '2.0 MiB/s')
        self.assertEqual(item.upspeed_str, '1.0 MiB/s')
        self.assertEqual(item.category, 'ISOs')
        self.assertEqual(item.tags, 'linux, fedora')

        # Test status filter matching
        self.assertTrue(item.matches_status_filter('all'))
        self.assertTrue(item.matches_status_filter('downloading'))
        self.assertFalse(item.matches_status_filter('seeding'))
        self.assertTrue(item.matches_status_filter('active'))


class TestTorrentTable(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock(spec=QBittorrentClient)
        self.table = TorrentTable(self.mock_client)

    def test_search_and_filter(self):
        item1 = TorrentItem({'hash': '111', 'name': 'Ubuntu 24.04', 'state': 'downloading', 'category': 'ISOs', 'tags': 'distro', 'dlspeed': 1000})
        item2 = TorrentItem({'hash': '222', 'name': 'Arch Linux', 'state': 'uploading', 'category': 'ISOs', 'tags': 'distro', 'dlspeed': 0, 'upspeed': 500})
        item3 = TorrentItem({'hash': '333', 'name': 'My Video', 'state': 'pausedDL', 'category': 'Videos', 'tags': 'personal', 'dlspeed': 0})

        self.table.raw_store.append(item1)
        self.table.raw_store.append(item2)
        self.table.raw_store.append(item3)

        self.assertEqual(self.table.sort_model.get_n_items(), 3)

        # Filter by search
        self.table.set_search_query("ubuntu")
        self.assertEqual(self.table.filter_model.get_n_items(), 1)
        self.assertEqual(self.table.filter_model.get_item(0).name, "Ubuntu 24.04")

        # Clear search
        self.table.set_search_query("")
        self.assertEqual(self.table.filter_model.get_n_items(), 3)

        # Filter by category
        self.table.set_sidebar_filter("category", "Videos")
        self.assertEqual(self.table.filter_model.get_n_items(), 1)
        self.assertEqual(self.table.filter_model.get_item(0).name, "My Video")

        # Filter by status
        self.table.set_sidebar_filter("status", "seeding")
        self.assertEqual(self.table.filter_model.get_n_items(), 1)
        self.assertEqual(self.table.filter_model.get_item(0).name, "Arch Linux")

    def test_row_dynamic_binding_update(self):
        class DummyListItem(GObject.Object):
            def __init__(self, item):
                super().__init__()
                self._item = item
                self._child = None
            def get_item(self): return self._item
            def set_child(self, c): self._child = c
            def get_child(self): return self._child

        item = TorrentItem({'hash': '999', 'name': 'Ubuntu', 'state': 'stoppedDL'})
        col_status = self.table.column_view.get_columns().get_item(4)
        factory = col_status.get_factory()
        dummy = DummyListItem(item)

        factory.emit('setup', dummy)
        factory.emit('bind', dummy)
        lbl = dummy.get_child()
        self.assertEqual(lbl.get_text(), "Stopped")

        # Update item state
        item.update({'state': 'downloading'})
        self.assertEqual(lbl.get_text(), "Downloading")

        # Unbind
        factory.emit('unbind', dummy)


class TestClientMethods(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.mock_client = MagicMock(spec=QBittorrentClient)
        self.mock_client.get_torrents.return_value = []
        self.mock_client.get_transfer_info.return_value = {}
        self.mock_client.get_categories.return_value = {}
        self.mock_client.get_tags.return_value = []
        self.mock_client.get_free_space.return_value = 1000

    def tearDown(self):
        self.tmp_dir.cleanup()

    @patch('qbittorrentapi.Client')
    def test_client_operations(self, mock_api_cls):
        mock_api = mock_api_cls.return_value
        client = QBittorrentClient()

        # Connect
        client.connect()
        mock_api.auth_log_in.assert_called_once()

        # Torrents
        client.pause_torrent("hash1")
        mock_api.torrents_pause.assert_called_with(torrent_hashes=['hash1'])

        client.resume_torrent(["hash1", "hash2"])
        mock_api.torrents_resume.assert_called_with(torrent_hashes=['hash1', 'hash2'])

        client.delete_torrent("hash1", delete_files=True)
        mock_api.torrents_delete.assert_called_with(delete_files=True, torrent_hashes=['hash1'])

        client.top_priority("hash1")
        mock_api.torrents_top_priority.assert_called_with(torrent_hashes=['hash1'])

        client.set_location("hash1", "/new/path")
        mock_api.torrents_set_location.assert_called_with(location="/new/path", torrent_hashes=['hash1'])

        client.create_category("TestCat", "/save/path")
        mock_api.torrents_create_category.assert_called_with(name="TestCat", save_path="/save/path")

        client.add_tags("hash1", ["tagA", "tagB"])
        mock_api.torrents_add_tags.assert_called_with(tags=['tagA', 'tagB'], torrent_hashes=['hash1'])

        # Speed limits mode boolean parsing
        mock_api.transfer_speed_limits_mode.return_value = "0"
        self.assertFalse(client.get_speed_limits_mode())

        mock_api.transfer_speed_limits_mode.return_value = "1"
        self.assertTrue(client.get_speed_limits_mode())

        mock_api.transfer_speed_limits_mode.return_value = 0
        self.assertFalse(client.get_speed_limits_mode())

        client.set_speed_limits_mode(True)
        mock_api.transfer_set_speed_limits_mode.assert_called_with(intended_state=True)

    @patch('qbittorrentapi.Client')
    def test_connection_testing(self, mock_api_cls):
        mock_api = mock_api_cls.return_value
        mock_api.app_version.return_value = 'v5.3.0'
        mock_api.app_web_api_version.return_value = '2.16.2'

        success, msg, ver = QBittorrentClient.test_connection_params('http://127.0.0.1:8080', 'admin', 'adminpassword')
        self.assertTrue(success)
        self.assertIn('v5.3.0', msg)
        self.assertEqual(ver, 'v5.3.0')

    def test_settings_get_with_default(self):
        s = Settings(config_dir=self.tmp_dir.name)
        self.assertEqual(s.get("unknown_dummy_key", False), False)
        self.assertEqual(s.get("unknown_dummy_key", "custom"), "custom")
        self.assertEqual(s.defaults["host_ip"], "127.0.0.1")
        self.assertTrue(bool(s.get("host_ip")))

    def test_welcome_window(self):
        mock_settings = MagicMock()
        def get_setting(key, default=None):
            vals = {"host_ip": "127.0.0.1", "port": "8080", "username": "admin", "password": "adminpassword", "use_https": False}
            return vals.get(key, default)
        mock_settings.get.side_effect = get_setting
        mock_client = MagicMock()

        welcome = WelcomeWindow(None, mock_settings, mock_client, is_reconnect=False)
        self.assertIsNotNone(welcome)
        self.assertEqual(welcome.get_title(), "Welcome to GTKittorrent")
        
        host_ip, port, username, password, use_https, full_host = welcome._get_form_values()
        self.assertEqual(host_ip, "127.0.0.1")
        self.assertEqual(full_host, "http://127.0.0.1:8080")

    def test_preferences_dialog_test_connection(self):
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda k, d=None: "127.0.0.1" if "ip" in k else "8080"
        mock_client = MagicMock()
        mock_client.get_app_preferences.return_value = {}

        pref_dlg = PreferencesDialog(None, mock_settings, mock_client)
        self.assertIsNotNone(pref_dlg.test_btn)
        self.assertEqual(pref_dlg.test_btn.get_label(), "Test Connection")

        # Test UI feedback
        pref_dlg._on_test_connection_result(True, "Success connecting!")
        self.assertTrue(pref_dlg.test_feedback_box.get_visible())
        self.assertIn("Success", pref_dlg.test_feedback_lbl.get_text())

    def test_preferences_dialog_download_paths_and_temp_path_sensitivity(self):
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda k, d=None: "127.0.0.1" if "ip" in k else "8080"
        mock_client = MagicMock()
        mock_client.get_app_preferences.return_value = {
            "save_path": "/home/user/Downloads",
            "temp_path_enabled": False,
            "temp_path": "/home/user/Downloads/incomplete"
        }

        pref_dlg = PreferencesDialog(None, mock_settings, mock_client)
        
        # Verify browse buttons exist
        self.assertIsNotNone(pref_dlg.save_path_browse_btn)
        self.assertIsNotNone(pref_dlg.temp_path_browse_btn)
        self.assertEqual(pref_dlg.save_path_entry.get_text(), "/home/user/Downloads")
        self.assertEqual(pref_dlg.temp_path_entry.get_text(), "/home/user/Downloads/incomplete")

        # Since temp_path_enabled is False, temp_path_entry should be greyed out (not sensitive)
        self.assertFalse(pref_dlg.temp_path_switch.get_active())
        self.assertFalse(pref_dlg.temp_path_entry.get_sensitive())

        # When toggled to True, temp_path_entry should become sensitive
        pref_dlg.temp_path_switch.set_active(True)
        self.assertTrue(pref_dlg.temp_path_entry.get_sensitive())

        # When toggled back to False, temp_path_entry should become insensitive
        pref_dlg.temp_path_switch.set_active(False)
        self.assertFalse(pref_dlg.temp_path_entry.get_sensitive())

        # Test browsing directory helper
        with patch("gtkittorrent.views.dialogs.preferences_dialog.Gtk.FileChooserNative") as mock_chooser_cls:
            mock_chooser = MagicMock()
            mock_chooser_cls.return_value = mock_chooser
            
            # Simulate user selecting a folder
            def fake_connect(signal, callback):
                if signal == "response":
                    fake_file = MagicMock()
                    fake_file.get_path.return_value = "/new/downloads/folder"
                    mock_chooser.get_file.return_value = fake_file
                    callback(mock_chooser, Gtk.ResponseType.ACCEPT)
            mock_chooser.connect.side_effect = fake_connect

            pref_dlg._on_browse_directory(pref_dlg.save_path_entry, "Select Save Directory")
            self.assertEqual(pref_dlg.save_path_entry.get_text(), "/new/downloads/folder")

    def test_preferences_dialog_engine_controls(self):
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda k, d=None: "127.0.0.1" if "ip" in k else "8080"
        mock_client = MagicMock()
        mock_client.get_app_preferences.return_value = {}

        pref_dlg = PreferencesDialog(None, mock_settings, mock_client)
        
        # Verify row and buttons exist
        self.assertIsNotNone(pref_dlg.engine_control_row)
        self.assertIsNotNone(pref_dlg.engine_start_btn)
        self.assertIsNotNone(pref_dlg.engine_stop_btn)
        self.assertIsNotNone(pref_dlg.engine_restart_btn)

        # Status update UI: when running
        pref_dlg._update_engine_status_ui(True, 8080)
        self.assertIn("Running", pref_dlg.engine_control_row.get_subtitle())
        self.assertFalse(pref_dlg.engine_start_btn.get_sensitive())
        self.assertTrue(pref_dlg.engine_stop_btn.get_sensitive())
        self.assertTrue(pref_dlg.engine_restart_btn.get_sensitive())

        # Status update UI: when stopped
        pref_dlg._update_engine_status_ui(False, 8080)
        self.assertIn("Stopped", pref_dlg.engine_control_row.get_subtitle())
        self.assertTrue(pref_dlg.engine_start_btn.get_sensitive())
        self.assertFalse(pref_dlg.engine_stop_btn.get_sensitive())
        self.assertTrue(pref_dlg.engine_restart_btn.get_sensitive())

        # Test start click triggers start_daemon_async
        with patch.object(pref_dlg.daemon_mgr, "start_daemon_async") as mock_start:
            pref_dlg._on_engine_start_clicked(pref_dlg.engine_start_btn)
            mock_start.assert_called_once()

        # Test stop click triggers stop_daemon
        with patch.object(pref_dlg.daemon_mgr, "stop_daemon") as mock_stop:
            with patch("threading.Thread") as mock_thread:
                pref_dlg._on_engine_stop_clicked(pref_dlg.engine_stop_btn)
                mock_thread.assert_called_once()

        # Test restart click triggers restart_daemon_async
        with patch.object(pref_dlg.daemon_mgr, "restart_daemon_async") as mock_restart:
            pref_dlg._on_engine_restart_clicked(pref_dlg.engine_restart_btn)
            mock_restart.assert_called_once()


class TestDetailsTabs(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.mock_client = MagicMock(spec=QBittorrentClient)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_speed_tab(self):
        speed_tab = SpeedTab(self.mock_client)
        speed_tab.add_data_point(1024 * 1024, 512 * 1024)
        self.assertEqual(len(speed_tab.dl_history), 60)
        self.assertEqual(speed_tab.dl_history[-1], 1024 * 1024)

    def test_content_tab(self):
        self.mock_client.get_torrent_contents.return_value = [
            {'index': 0, 'name': 'file1.txt', 'size': 1024, 'progress': 1.0, 'priority': 1},
            {'index': 1, 'name': 'file2.mkv', 'size': 1048576, 'progress': 0.5, 'priority': 6}
        ]
        content_tab = ContentTab(self.mock_client)
        item = TorrentItem({'hash': 'abc'})
        content_tab.update(item)
        self.assertEqual(content_tab.model.get_n_items(), 2)
        f1 = content_tab.model.get_item(0)
        self.assertEqual(f1.name, 'file1.txt')
        self.assertEqual(f1.priority_str, 'Normal')

    def test_trackers_tab(self):
        self.mock_client.get_torrent_trackers.return_value = [
            {'tier': 1, 'url': 'http://tracker1.com/announce', 'status': 'working', 'num_peers': 10, 'num_seeds': 20}
        ]
        trackers_tab = TrackersTab(self.mock_client)
        item = TorrentItem({'hash': 'abc'})
        trackers_tab.update(item)
        self.assertEqual(trackers_tab.model.get_n_items(), 1)
        t = trackers_tab.model.get_item(0)
        self.assertEqual(t.url, 'http://tracker1.com/announce')

    def test_details_notebook_tab_icons(self):
        from gtkittorrent.views.details.details_notebook import DetailsNotebook
        nb = DetailsNotebook(self.mock_client)
        pages = [
            (nb.general_tab, "General"),
            (nb.trackers_tab, "Trackers"),
            (nb.peers_tab, "Peers"),
            (nb.content_tab, "Content"),
            (nb.speed_tab, "Speed"),
            (nb.log_tab, "Execution Log"),
        ]
        for child, title in pages:
            page = nb.stack.get_page(child)
            self.assertEqual(page.get_title(), title)
            icon_name = page.get_icon_name()
            self.assertIsNotNone(icon_name)
            self.assertTrue(len(icon_name) > 0)
            self.assertTrue(icon_name.endswith("-symbolic"))

    def test_settings_instances_management(self):
        s = Settings(config_dir=self.tmp_dir.name)
        s.ensure_local_instance()
        instances = s.get_instances()
        self.assertGreaterEqual(len(instances), 1)
        curr = s.get_current_instance()
        self.assertIsNotNone(curr)

        # Add new instance
        new_inst = s.add_instance(
            name="My Server",
            host_ip="192.168.1.50",
            port="8080",
            username="admin",
            password="secretpassword",
            use_https=True,
            make_active=True
        )
        self.assertEqual(new_inst["name"], "My Server")
        self.assertEqual(new_inst["host"], "https://192.168.1.50:8080")
        self.assertEqual(s.get_current_instance_id(), new_inst["id"])
        self.assertEqual(s.get("host"), "https://192.168.1.50:8080")
        self.assertEqual(s.get("host_ip"), "192.168.1.50")

        # Update instance
        s.update_instance(new_inst["id"], name="Updated Server", port="8081")
        updated = s.get_instance(new_inst["id"])
        self.assertEqual(updated["name"], "Updated Server")
        self.assertEqual(updated["port"], "8081")
        self.assertEqual(s.get("port"), "8081")

        # Switch back to first instance
        first_id = instances[0]["id"]
        self.assertTrue(s.set_current_instance_id(first_id))
        self.assertEqual(s.get_current_instance_id(), first_id)

        # Delete new instance
        self.assertTrue(s.delete_instance(new_inst["id"]))
        self.assertIsNone(s.get_instance(new_inst["id"]))

        # Cannot delete the only remaining instance
        while len(s.get_instances()) > 1:
            s.delete_instance(s.get_instances()[-1]["id"])
        self.assertFalse(s.delete_instance(s.get_instances()[0]["id"]))

    def test_instance_dialog(self):
        s = Settings(config_dir=self.tmp_dir.name)
        # Test Add Mode
        dlg = InstanceDialog(None, s, instance=None)
        self.assertEqual(dlg.get_title(), "Add qBittorrent Instance")
        self.assertEqual(dlg.save_btn.get_label(), "Add")
        dlg.name_entry.set_text("Test Remote Server")
        dlg.host_entry.set_text("remote.local")
        dlg.port_entry.set_text("9090")
        dlg.username_entry.set_text("user")
        dlg.password_entry.set_text("pass")
        dlg.https_switch.set_active(True)

        saved = []
        dlg.on_saved = lambda inst, is_active: saved.append((inst, is_active))
        dlg._on_save_clicked(None)

        self.assertEqual(len(saved), 1)
        inst, is_active = saved[0]
        self.assertEqual(inst["name"], "Test Remote Server")
        self.assertEqual(inst["host"], "https://remote.local:9090")
        self.assertTrue(is_active)

        # Test Edit Mode
        edit_dlg = InstanceDialog(None, s, instance=inst)
        self.assertEqual(edit_dlg.get_title(), "Edit Instance")
        self.assertEqual(edit_dlg.save_btn.get_label(), "Save")
        self.assertEqual(edit_dlg.name_entry.get_text(), "Test Remote Server")
        self.assertEqual(edit_dlg.host_entry.get_text(), "remote.local")

        # Clean up
        s.delete_instance(inst["id"])

    def test_main_window_instance_switching(self):
        from gtkittorrent.views.main_window import MainWindow
        app = Adw.Application(application_id="test.instance.app")
        app.settings = Settings(config_dir=self.tmp_dir.name)
        app.settings.ensure_local_instance()
        mock_client = MagicMock()
        mock_client.get_torrents.return_value = []
        mock_client.get_transfer_info.return_value = {}
        mock_client.get_app_preferences.return_value = {}
        mock_client.get_categories.return_value = {}
        mock_client.get_tags.return_value = []

        win = MainWindow(app, mock_client)
        self.assertIsNotNone(win.instance_btn)
        self.assertIsNotNone(win.instance_popover)
        self.assertFalse(hasattr(win, "menu_btn"))
        self.assertIn(win.instance_label.get_text(), [inst["name"] for inst in app.settings.get_instances()])

        # Add an instance and switch to it
        server_inst = app.settings.add_instance(
            name="Backup Server",
            host_ip="10.0.0.5",
            port="8080",
            username="admin",
            password="pwd",
            make_active=False
        )
        win.switch_to_instance(server_inst["id"])
        self.assertEqual(win.instance_label.get_text(), "Backup Server")
        mock_client.update_settings.assert_called_with("http://10.0.0.5:8080", "admin", "pwd")

        # Test adding an instance via dialog callback (with is_active=True)
        # Verifies the button and popover update immediately without needing to click current server
        new_added = app.settings.add_instance(
            name="New Immediate Server",
            host_ip="10.0.0.6",
            port="8080",
            username="admin",
            password="pwd",
            make_active=True
        )
        win._on_instance_saved(new_added, is_active=True)
        self.assertEqual(win.instance_label.get_text(), "New Immediate Server")
        mock_client.update_settings.assert_called_with("http://10.0.0.6:8080", "admin", "pwd")

        # Clean up
        app.settings.delete_instance(server_inst["id"])
        app.settings.delete_instance(new_added["id"])

        # Test _on_add_instance_clicked opens WelcomeWindow
        with patch("gtkittorrent.views.main_window.WelcomeWindow") as mock_welcome_cls:
            mock_welcome = MagicMock()
            mock_welcome_cls.return_value = mock_welcome
            win._on_add_instance_clicked()
            mock_welcome_cls.assert_called_with(app, app.settings, mock_client, is_reconnect=False)
            mock_welcome.set_transient_for.assert_called_with(win)
            mock_welcome.present.assert_called_once()

    def test_sidebar_priority_buttons(self):
        sidebar = Sidebar(self.mock_client)
        self.assertIsNotNone(sidebar.top_prio_btn)
        self.assertIsNotNone(sidebar.up_prio_btn)
        self.assertIsNotNone(sidebar.down_prio_btn)
        self.assertIsNotNone(sidebar.bottom_prio_btn)

        emitted = []
        sidebar.connect("priority-clicked", lambda s, action: emitted.append(action))
        sidebar.top_prio_btn.emit("clicked")
        sidebar.up_prio_btn.emit("clicked")
        sidebar.down_prio_btn.emit("clicked")
        sidebar.bottom_prio_btn.emit("clicked")

        self.assertEqual(emitted, ["top", "up", "down", "bottom"])

    def test_torrent_table_column_widths_and_settings(self):
        settings = Settings(config_dir=self.tmp_dir.name)
        table = TorrentTable(self.mock_client, settings=settings)
        table.reset_column_widths()

        # Verify initial widths
        col_view = table.column_view
        cols = {col_view.get_columns().get_item(i).get_title(): col_view.get_columns().get_item(i).get_fixed_width()
                for i in range(col_view.get_columns().get_n_items())}

        self.assertEqual(cols["#"], 40)
        self.assertGreater(cols["Name"], 200)
        self.assertEqual(cols["Size"], 75)
        self.assertEqual(cols["Done"], 160)
        self.assertEqual(cols["Seeds"], 65)
        self.assertEqual(cols["Peers"], 65)

        # Test resetting column widths to defaults
        table.reset_column_widths()
        self.assertEqual(table.columns_by_title["Name"].get_fixed_width(), 280)
        self.assertEqual(table.columns_by_title["Done"].get_fixed_width(), 160)
        saved = settings.get_column_widths()
        self.assertEqual(saved["Name"], 280)

        # Test updating column width and persistence
        name_col = table.columns_by_title["Name"]
        name_col.set_fixed_width(350)
        table._persist_column_widths()

        saved = settings.get_column_widths()
        self.assertEqual(saved["Name"], 350)

        # Test column visibility toggle & popover
        self.assertTrue(table.is_column_visible("Seeds"))
        table.set_column_visible("Seeds", False)
        self.assertFalse(table.is_column_visible("Seeds"))
        self.assertFalse(table.columns_by_title["Seeds"].get_visible())
        self.assertFalse(settings.get_visible_columns()["Seeds"])

        # Test popover creation
        popover = table.create_column_selector_popover()
        self.assertIsNotNone(popover)

        # Restore
        table.set_column_visible("Seeds", True)
        self.assertTrue(table.columns_by_title["Seeds"].get_visible())
        table.reset_column_widths()

    def test_torrent_table_column_order_and_reorder(self):
        settings = Settings(config_dir=self.tmp_dir.name)
        table = TorrentTable(self.mock_client, settings=settings)

        # Initial order
        cols_model = table.column_view.get_columns()
        initial_order = [cols_model.get_item(i).get_title() for i in range(cols_model.get_n_items())]
        self.assertEqual(initial_order[0], "#")
        self.assertEqual(initial_order[1], "Name")

        # Simulate column reordering by moving column at index 1 ("Name") to index 0
        name_col = table.columns_by_title["Name"]
        table.column_view.remove_column(name_col)
        table.column_view.insert_column(0, name_col)

        new_order = [cols_model.get_item(i).get_title() for i in range(cols_model.get_n_items())]
        self.assertEqual(new_order[0], "Name")
        self.assertEqual(new_order[1], "#")

        # Check saved order in settings
        saved_order = settings.get_column_order()
        self.assertEqual(saved_order[0], "Name")
        self.assertEqual(saved_order[1], "#")

        # Create a new table instance with same settings; it should load the saved order
        new_table = TorrentTable(self.mock_client, settings=settings)
        loaded_cols = new_table.column_view.get_columns()
        loaded_order = [loaded_cols.get_item(i).get_title() for i in range(loaded_cols.get_n_items())]
        self.assertEqual(loaded_order[0], "Name")
        self.assertEqual(loaded_order[1], "#")

        # Test reset column order
        new_table.reset_column_order()
        reset_cols = new_table.column_view.get_columns()
        reset_order = [reset_cols.get_item(i).get_title() for i in range(reset_cols.get_n_items())]
        self.assertEqual(reset_order[0], "#")
        self.assertEqual(reset_order[1], "Name")
        self.assertEqual(settings.get_column_order(), table.default_order)

    def test_torrent_table_header_drag_workaround(self):
        """Header title 'pressed' handlers must be blocked so GTK's reorder drag gesture survives."""
        table = TorrentTable(self.mock_client, settings=None)
        signal_id = GObject.signal_lookup("pressed", Gtk.GestureClick)
        match = GObject.SignalMatchType.ID | GObject.SignalMatchType.UNBLOCKED

        def unblocked_count():
            count = 0
            title = table.column_view.get_first_child().get_first_child()
            while title is not None:
                ctrls = title.observe_controllers()
                for i in range(ctrls.get_n_items()):
                    c = ctrls.get_item(i)
                    if isinstance(c, Gtk.GestureClick) and GObject.signal_handler_find(c, match, signal_id, 0, None, None, None):
                        count += 1
                title = title.get_next_sibling()
            return count

        self.assertEqual(unblocked_count(), 0)
        # Re-adding a column recreates its header widget; the workaround must re-apply
        col = table.columns_by_title["Size"]
        table.column_view.remove_column(col)
        table.column_view.insert_column(2, col)
        self.assertEqual(unblocked_count(), 0)

    def test_status_bar_alt_speed_and_popover(self):
        from gtkittorrent.views.status_bar import StatusBar
        status_bar = StatusBar(self.mock_client)

        # Check icon name
        self.assertEqual(status_bar.alt_speed_btn.get_icon_name(), "power-profile-performance-symbolic")

        # Test initial state
        self.assertFalse(status_bar.alt_speed_btn.get_active())
        self.assertNotIn("suggested-action", status_bar.alt_speed_btn.get_css_classes())

        # Test updating with preferences
        prefs = {"alt_dl_limit": 102400, "alt_up_limit": 51200}
        self.mock_client.get_speed_limits_mode.return_value = True
        status_bar.update_status({"connection_status": "connected"}, prefs=prefs)

        self.assertTrue(status_bar.alt_speed_btn.get_active())
        self.assertIn("suggested-action", status_bar.alt_speed_btn.get_css_classes())
        self.assertIn("100 KiB/s", status_bar.alt_speed_btn.get_tooltip_text())

        # Test popover open & save
        status_bar._open_speed_popover()
        self.assertEqual(status_bar.popover_dl_adj.get_value(), 100)
        self.assertEqual(status_bar.popover_up_adj.get_value(), 50)
        self.assertTrue(status_bar.popover_enable_switch.get_active())

        # Change values and save
        status_bar.popover_dl_adj.set_value(250)
        status_bar.popover_up_adj.set_value(120)
        status_bar._on_popover_save_clicked(None)

        self.mock_client.set_app_preferences.assert_called_with({
            "alt_dl_limit": 250 * 1024,
            "alt_up_limit": 120 * 1024
        })

    def test_main_window_headerbar_modifications(self):
        from gtkittorrent.views.main_window import MainWindow
        app = Adw.Application(application_id="io.test.gtkittorrent", flags=Gio.ApplicationFlags.FLAGS_NONE)
        win = MainWindow(app, self.mock_client)

        # Ensure column selector button and refresh button were removed
        self.assertFalse(hasattr(win, "col_selector_btn"))
        self.assertFalse(hasattr(win, "refresh_btn"))

        # Ensure toggle details button has the secondary panel icon
        self.assertEqual(win.toggle_details_btn.get_icon_name(), "sidebar-show-right-symbolic")


class TestLocalDaemonAndConfig(unittest.TestCase):
    def test_daemon_binary_info(self):
        from gtkittorrent.client.daemon import LocalDaemonManager
        mgr = LocalDaemonManager.get_instance()
        info = mgr.get_binary_info()
        self.assertIn("has_nox", info)
        self.assertIn("has_gui", info)
        self.assertIn("preferred", info)
        self.assertIn("recommend_nox", info)

    def test_qbt_config_read_and_write(self):
        import tempfile, os
        from gtkittorrent.utils import qbt_config
        with tempfile.TemporaryDirectory() as tmpdir:
            test_conf = os.path.join(tmpdir, "qBittorrent.conf")
            with patch.object(qbt_config, "find_existing_config_path", return_value=test_conf):
                # 1. Non-existent initially
                info = qbt_config.read_qbt_config()
                self.assertFalse(info["exists"])

                # 2. Configure
                success, err = qbt_config.configure_qbt_webui(port=8999, enable=True, bypass_localhost_auth=True)
                self.assertTrue(success)
                self.assertIsNone(err)

                # 3. Read back
                info = qbt_config.read_qbt_config()
                self.assertTrue(info["exists"])
                self.assertTrue(info["webui_enabled"])
                self.assertEqual(info["webui_port"], 8999)
                self.assertFalse(info["localhost_auth"])

    def test_welcome_window_carousel(self):
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda k, d=None: "127.0.0.1" if "ip" in k else "8080"
        mock_client = MagicMock()

        # Test initial open (mode selection)
        welcome = WelcomeWindow(None, mock_settings, mock_client, is_reconnect=False)
        self.assertIsNotNone(welcome.carousel)
        self.assertEqual(welcome.carousel.get_n_pages(), 3)
        self.assertFalse(welcome.back_btn.get_visible())

        # Test navigation to local page
        welcome._go_to_page(1)
        self.assertTrue(welcome.back_btn.get_visible())
        self.assertIn("Local", welcome.title_widget.get_title())

        # Test navigation to remote page
        welcome._go_to_page(2)
        self.assertTrue(welcome.back_btn.get_visible())
        self.assertIn("Remote", welcome.title_widget.get_title())

        # Test back to mode page
        welcome._go_to_page(0)
        self.assertFalse(welcome.back_btn.get_visible())

    def test_welcome_window_reconnect_routing(self):
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda k, d=None: "127.0.0.1" if "ip" in k else "8080"
        mock_client = MagicMock()

        # Reconnect on local instance routes to local page (page 1)
        welcome = WelcomeWindow(None, mock_settings, mock_client, is_reconnect=True)
        self.assertTrue(welcome.back_btn.get_visible())
        self.assertIn("Local", welcome.title_widget.get_title())

    def test_main_window_offline_banner(self):
        from gtkittorrent.views.main_window import MainWindow
        mock_client = MagicMock()
        mock_client.get_torrents.return_value = []
        mock_client.is_connected.return_value = False
        mock_client.get_transfer_info.return_value = {}
        mock_client.get_app_preferences.return_value = {}
        mock_client.get_free_space.return_value = 1000

        app = Adw.Application(application_id="io.test.gtkittorrent", flags=Gio.ApplicationFlags.FLAGS_NONE)
        app.settings = MagicMock()
        app.settings.get_current_instance.return_value = {
            "id": "default", "name": "Local qBittorrent", "host_ip": "127.0.0.1", "port": 8080
        }
        win = MainWindow(app, mock_client)
        self.assertTrue(hasattr(win, "offline_banner"))
        self.assertTrue(win.offline_banner.get_revealed())
        self.assertIn("Local", win.offline_banner.get_title())
        self.assertEqual(win.offline_banner.get_button_label(), "Start Engine")

    def test_main_window_startup_loading_and_cancel(self):
        from gtkittorrent.views.main_window import MainWindow
        mock_client = MagicMock()
        mock_client.get_torrents.return_value = []
        mock_client.is_connected.return_value = False
        mock_client.get_transfer_info.return_value = {}
        mock_client.get_app_preferences.return_value = {}
        mock_client.get_free_space.return_value = 1000

        app = Adw.Application(application_id="io.test.gtkittorrent.loading", flags=Gio.ApplicationFlags.FLAGS_NONE)
        app.settings = MagicMock()
        app.settings.get_current_instance.return_value = {
            "id": "local", "name": "Local qBittorrent", "host_ip": "127.0.0.1", "port": 8080
        }

        win = MainWindow(app, mock_client)
        self.assertTrue(hasattr(win, "content_stack"))
        self.assertTrue(hasattr(win, "loading_spinner"))
        self.assertTrue(hasattr(win, "loading_page"))

        # Default child is main view
        self.assertEqual(win.content_stack.get_visible_child_name(), "main")

        # When starting connection, switches to loading view
        with patch("threading.Thread") as mock_thread:
            win.start_initial_connection()
            self.assertEqual(win.content_stack.get_visible_child_name(), "loading")
            self.assertIn("Local qBittorrent", win.loading_page.get_title())

        # When user cancels loading
        win._cancel_loading()
        self.assertEqual(win.content_stack.get_visible_child_name(), "main")
        self.assertTrue(win.offline_banner.get_revealed())

    def test_settings_ensure_local_instance(self):
        import tempfile
        from gtkittorrent.settings import Settings
        with tempfile.TemporaryDirectory() as tmpdir:
            s = Settings(config_dir=tmpdir)
            self.assertIsNone(s.get_local_instance())
            
            # Call ensure_local_instance
            loc = s.ensure_local_instance()
            self.assertIsNotNone(loc)
            self.assertTrue(loc["local"])
            self.assertEqual(loc["name"], "Local qBittorrent")
            self.assertEqual(s.get_local_instance()["id"], loc["id"])

            # Calling again returns same instance
            loc2 = s.ensure_local_instance()
            self.assertEqual(loc2["id"], loc["id"])

    def test_welcome_window_multi_instance_flow(self):
        mock_settings = MagicMock()
        mock_settings.get.side_effect = lambda k, d=None: "127.0.0.1" if "ip" in k else "8080"
        mock_settings.get_instances.return_value = []
        mock_client = MagicMock()

        welcome = WelcomeWindow(None, mock_settings, mock_client, is_reconnect=False)
        self.assertFalse(hasattr(welcome, "finish_header_btn"))

        # Remote default name should be "Server"
        self.assertEqual(welcome.name_entry.get_text(), "Server")

        # Simulate local engine status reporting running
        welcome._on_local_engine_status_result(True, 8080)
        self.assertTrue(welcome.local_success_banner.get_revealed())

        # Saving local and adding another should return to page 0 with local greyed out
        welcome._on_local_save_and_add_another()
        self.assertFalse(welcome.local_row.get_sensitive())
        self.assertEqual(welcome.local_row_suffix_img.get_icon_name(), "emblem-ok-symbolic")

        # Test remote add another flow resets and returns to page 0
        welcome._go_to_page(2)
        welcome.name_entry.set_text("My Seedbox")
        welcome._on_remote_save_result(True, "Connected", "My Seedbox", "192.168.1.50", "8080", "admin", "pw", False, "http://192.168.1.50:8080", finish_after=False)
        self.assertEqual(welcome.name_entry.get_text(), "Server")
        self.assertFalse(welcome.local_row.get_sensitive())

        # Test finish flow marks welcome_completed
        welcome._finish_and_open()
        mock_settings.set.assert_any_call("welcome_completed", True)
        mock_settings.set.assert_any_call("configured", True)

    def test_remote_first_does_not_add_local(self):
        import tempfile
        from gtkittorrent.settings import Settings
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(config_dir=tmpdir)
            self.assertEqual(settings.get_instances(), [])
            self.assertIsNone(settings.get_local_instance())

            # Add a remote instance
            inst = settings.add_instance("My NAS", "192.168.1.10", 8080, "admin", "secret", local=False)
            self.assertFalse(inst["local"])
            self.assertEqual(len(settings.get_instances()), 1)
            self.assertIsNone(settings.get_local_instance())

            # Test in welcome window
            mock_client = MagicMock()
            welcome = WelcomeWindow(None, settings, mock_client, is_reconnect=False)
            self.assertFalse(welcome.local_configured)
            self.assertTrue(welcome.local_row.get_sensitive())

    def test_welcome_window_opened_post_setup(self):
        import tempfile
        from gtkittorrent.settings import Settings
        with tempfile.TemporaryDirectory() as tmpdir:
            settings = Settings(config_dir=tmpdir)
            settings.set("welcome_completed", True)
            inst = settings.add_instance("Home Server", "192.168.1.100", 8080, "admin", "secret", local=False)

            mock_client = MagicMock()
            welcome = WelcomeWindow(None, settings, mock_client, is_reconnect=False)
            
            # Since welcome_completed is True, header has Done button
            self.assertTrue(hasattr(welcome, "done_header_btn"))
            self.assertEqual(welcome.done_header_btn.get_label(), "Done")

            # Configured instances are shown with the Done button at bottom
            self.assertTrue(welcome.configured_instances_group.get_visible())
            self.assertTrue(welcome.mode_finish_btn.get_visible())
            self.assertEqual(welcome.mode_finish_btn.get_label(), "Done")
            self.assertEqual(len(welcome.summary_rows), 1)


if __name__ == "__main__":
    unittest.main()
