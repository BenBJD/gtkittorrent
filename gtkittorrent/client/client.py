import logging
import qbittorrentapi

class QBittorrentClient:
    """Enhanced client wrapper around qbittorrent-api with complete Web UI feature coverage."""

    def __init__(self, host='http://127.0.0.1:8080', username='admin', password='adminpassword'):
        self.host = host
        self.username = username
        self.password = password
        self.client = None
        self.logger = logging.getLogger(__name__)
        self._initialize_client()

    def _initialize_client(self):
        self.client = qbittorrentapi.Client(
            host=self.host,
            username=self.username,
            password=self.password
        )

    def update_settings(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self._initialize_client()
        return self.connect()

    def connect(self):
        try:
            self.client.auth_log_in()
            return True
        except qbittorrentapi.LoginFailed:
            self.logger.error("Login failed: Invalid username or password")
            return False
        except qbittorrentapi.APIConnectionError as e:
            self.logger.error(f"Connection error: Could not connect to {self.host}. {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False

    def is_connected(self):
        try:
            return self.client.is_logged_in if self.client else False
        except Exception:
            return False

    @staticmethod
    def test_connection_params(host, username, password):
        """Test connection parameters without modifying instance state.
        Returns tuple: (success: bool, message: str, version: str)
        """
        try:
            temp_client = qbittorrentapi.Client(
                host=host,
                username=username,
                password=password,
                REQUESTS_ARGS={'timeout': (5, 5)}
            )
            temp_client.auth_log_in()
            try:
                ver = temp_client.app_version()
                api_ver = temp_client.app_web_api_version()
                return True, f"Connected to qBittorrent {ver} (API v{api_ver})", str(ver)
            except Exception:
                return True, "Connected successfully!", ""
        except qbittorrentapi.LoginFailed:
            return False, "Login failed: Invalid username or password", ""
        except qbittorrentapi.APIConnectionError:
            return False, f"Could not connect to {host}: Connection refused or unreachable", ""
        except Exception as e:
            return False, f"Connection error: {e}", ""

    def test_connection(self, host=None, username=None, password=None):
        target_host = host if host is not None else self.host
        target_user = username if username is not None else self.username
        target_pass = password if password is not None else self.password
        return self.test_connection_params(target_host, target_user, target_pass)

    # Sync API
    def sync_maindata(self, rid=0):
        try:
            return self.client.sync_maindata(rid=rid)
        except Exception as e:
            self.logger.debug(f"Failed sync_maindata: {e}")
            return None

    def sync_torrent_peers(self, torrent_hash, rid=0):
        try:
            return self.client.sync_torrent_peers(torrent_hash=torrent_hash, rid=rid)
        except Exception as e:
            self.logger.debug(f"Failed sync_torrent_peers for {torrent_hash}: {e}")
            return None

    # Torrent Information
    def get_torrents(self, filter_name=None, category=None, tag=None, sort=None, reverse=False):
        try:
            kwargs = {}
            if filter_name:
                kwargs['filter'] = filter_name
            if category:
                kwargs['category'] = category
            if tag:
                kwargs['tag'] = tag
            if sort:
                kwargs['sort'] = sort
                kwargs['reverse'] = reverse
            return self.client.torrents_info(**kwargs)
        except Exception as e:
            self.logger.error(f"Failed to get torrents: {e}")
            return []

    def get_torrent_properties(self, torrent_hash):
        try:
            return self.client.torrents_properties(torrent_hash=torrent_hash)
        except Exception as e:
            self.logger.error(f"Failed to get properties for {torrent_hash}: {e}")
            return {}

    def get_torrent_contents(self, torrent_hash):
        try:
            return self.client.torrents_files(torrent_hash=torrent_hash)
        except Exception as e:
            self.logger.error(f"Failed to get contents for {torrent_hash}: {e}")
            return []

    def get_torrent_trackers(self, torrent_hash):
        try:
            return self.client.torrents_trackers(torrent_hash=torrent_hash)
        except Exception as e:
            self.logger.error(f"Failed to get trackers for {torrent_hash}: {e}")
            return []

    # Torrent Operations
    def _to_hash_list(self, hashes):
        if isinstance(hashes, (list, tuple, set)):
            return list(hashes)
        return [hashes]

    def pause_torrent(self, hashes):
        try:
            self.client.torrents_pause(torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to pause torrent(s): {e}")
            return False

    def resume_torrent(self, hashes):
        try:
            self.client.torrents_resume(torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to resume torrent(s): {e}")
            return False

    def set_force_start(self, hashes, value=True):
        try:
            self.client.torrents_set_force_start(enable=value, torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to set force start: {e}")
            return False

    def delete_torrent(self, hashes, delete_files=False):
        try:
            self.client.torrents_delete(delete_files=delete_files, torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete torrent(s): {e}")
            return False

    def recheck_torrent(self, hashes):
        try:
            self.client.torrents_recheck(torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to recheck torrent(s): {e}")
            return False

    def reannounce_torrent(self, hashes):
        try:
            self.client.torrents_reannounce(torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to reannounce torrent(s): {e}")
            return False

    # Queue Priority Operations
    def top_priority(self, hashes):
        try:
            self.client.torrents_top_priority(torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to set top priority: {e}")
            return False

    def increase_priority(self, hashes):
        try:
            self.client.torrents_increase_priority(torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to increase priority: {e}")
            return False

    def decrease_priority(self, hashes):
        try:
            self.client.torrents_decrease_priority(torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to decrease priority: {e}")
            return False

    def bottom_priority(self, hashes):
        try:
            self.client.torrents_bottom_priority(torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to set bottom priority: {e}")
            return False

    # Location & Renaming
    def set_location(self, hashes, location):
        try:
            self.client.torrents_set_location(location=location, torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to set location: {e}")
            return False

    def rename_torrent(self, torrent_hash, new_name):
        try:
            self.client.torrents_rename(torrent_hash=torrent_hash, new_torrent_name=new_name)
            return True
        except Exception as e:
            self.logger.error(f"Failed to rename torrent: {e}")
            return False

    def rename_file(self, torrent_hash, old_path, new_path):
        try:
            self.client.torrents_rename_file(torrent_hash=torrent_hash, old_path=old_path, new_path=new_path)
            return True
        except Exception as e:
            self.logger.error(f"Failed to rename file: {e}")
            return False

    # Categories & Tags
    def get_categories(self):
        try:
            return self.client.torrents_categories()
        except Exception as e:
            self.logger.error(f"Failed to get categories: {e}")
            return {}

    def create_category(self, name, save_path=""):
        try:
            self.client.torrents_create_category(name=name, save_path=save_path)
            return True
        except Exception as e:
            self.logger.error(f"Failed to create category: {e}")
            return False

    def edit_category(self, name, save_path=""):
        try:
            self.client.torrents_edit_category(name=name, save_path=save_path)
            return True
        except Exception as e:
            self.logger.error(f"Failed to edit category: {e}")
            return False

    def remove_categories(self, categories):
        try:
            cats = categories if isinstance(categories, (list, tuple)) else [categories]
            self.client.torrents_remove_categories(categories=cats)
            return True
        except Exception as e:
            self.logger.error(f"Failed to remove categories: {e}")
            return False

    def set_category(self, hashes, category):
        try:
            self.client.torrents_set_category(category=category, torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to set category: {e}")
            return False

    def get_tags(self):
        try:
            return self.client.torrents_tags()
        except Exception as e:
            self.logger.error(f"Failed to get tags: {e}")
            return []

    def create_tags(self, tags):
        try:
            t_list = tags if isinstance(tags, (list, tuple)) else [tags]
            self.client.torrents_create_tags(tags=t_list)
            return True
        except Exception as e:
            self.logger.error(f"Failed to create tags: {e}")
            return False

    def delete_tags(self, tags):
        try:
            t_list = tags if isinstance(tags, (list, tuple)) else [tags]
            self.client.torrents_delete_tags(tags=t_list)
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete tags: {e}")
            return False

    def add_tags(self, hashes, tags):
        try:
            t_list = tags if isinstance(tags, (list, tuple)) else [tags]
            self.client.torrents_add_tags(tags=t_list, torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to add tags: {e}")
            return False

    def remove_tags(self, hashes, tags):
        try:
            t_list = tags if isinstance(tags, (list, tuple)) else [tags]
            self.client.torrents_remove_tags(tags=t_list, torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to remove tags: {e}")
            return False

    # Speed limits & features
    def set_download_limit(self, hashes, limit_bytes_sec):
        try:
            self.client.torrents_set_download_limit(limit=limit_bytes_sec, torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to set download limit: {e}")
            return False

    def set_upload_limit(self, hashes, limit_bytes_sec):
        try:
            self.client.torrents_set_upload_limit(limit=limit_bytes_sec, torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to set upload limit: {e}")
            return False

    def toggle_sequential_download(self, hashes):
        try:
            self.client.torrents_toggle_sequential_download(torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to toggle sequential download: {e}")
            return False

    def toggle_first_last_piece_priority(self, hashes):
        try:
            self.client.torrents_toggle_first_last_piece_priority(torrent_hashes=self._to_hash_list(hashes))
            return True
        except Exception as e:
            self.logger.error(f"Failed to toggle first/last piece priority: {e}")
            return False

    def set_file_priority(self, torrent_hash, file_ids, priority):
        """Priority: 0 (do not download), 1 (normal), 6 (high), 7 (maximal)"""
        try:
            f_ids = file_ids if isinstance(file_ids, (list, tuple)) else [file_ids]
            self.client.torrents_file_priority(torrent_hash=torrent_hash, file_ids=f_ids, priority=priority)
            return True
        except Exception as e:
            self.logger.error(f"Failed to set file priority: {e}")
            return False

    # Trackers
    def add_trackers(self, torrent_hash, urls):
        try:
            url_list = urls if isinstance(urls, (list, tuple)) else [urls]
            self.client.torrents_add_trackers(torrent_hash=torrent_hash, urls=url_list)
            return True
        except Exception as e:
            self.logger.error(f"Failed to add trackers: {e}")
            return False

    def edit_tracker(self, torrent_hash, orig_url, new_url):
        try:
            self.client.torrents_edit_tracker(torrent_hash=torrent_hash, orig_url=orig_url, new_url=new_url)
            return True
        except Exception as e:
            self.logger.error(f"Failed to edit tracker: {e}")
            return False

    def remove_trackers(self, torrent_hash, urls):
        try:
            url_list = urls if isinstance(urls, (list, tuple)) else [urls]
            self.client.torrents_remove_trackers(torrent_hash=torrent_hash, urls=url_list)
            return True
        except Exception as e:
            self.logger.error(f"Failed to remove trackers: {e}")
            return False

    # Adding Torrents
    def add_torrent(self, urls=None, torrent_files=None, savepath=None, category=None,
                    tags=None, is_paused=False, is_sequential=False, is_first_last_piece_priority=False,
                    skip_checking=False, rename=None):
        try:
            kwargs = {}
            if savepath:
                kwargs['save_path'] = savepath
            if category:
                kwargs['category'] = category
            if tags:
                kwargs['tags'] = tags
            if is_paused:
                kwargs['is_paused'] = is_paused
            if is_sequential:
                kwargs['is_sequential_download'] = is_sequential
            if is_first_last_piece_priority:
                kwargs['is_first_last_piece_priority'] = is_first_last_piece_priority
            if skip_checking:
                kwargs['is_skip_checking'] = skip_checking
            if rename:
                kwargs['rename'] = rename

            self.client.torrents_add(urls=urls, torrent_files=torrent_files, **kwargs)
            return True
        except Exception as e:
            self.logger.error(f"Failed to add torrent: {e}")
            return False

    # Transfer & Alt Speed Mode
    def get_transfer_info(self):
        try:
            return self.client.transfer_info()
        except Exception as e:
            self.logger.debug(f"Failed to get transfer info: {e}")
            return {}

    def get_speed_limits_mode(self):
        try:
            mode = self.client.transfer_speed_limits_mode()
            return str(mode).strip() in ("1", "true", "True")
        except Exception as e:
            self.logger.debug(f"Failed to get speed limits mode: {e}")
            return False

    def toggle_speed_limits_mode(self):
        try:
            self.client.transfer_toggle_speed_limits_mode()
            return True
        except Exception as e:
            self.logger.error(f"Failed to toggle speed limits mode: {e}")
            return False

    def set_speed_limits_mode(self, enabled: bool):
        try:
            if hasattr(self.client, "transfer_set_speed_limits_mode"):
                self.client.transfer_set_speed_limits_mode(intended_state=enabled)
            else:
                curr = self.get_speed_limits_mode()
                if curr != enabled:
                    self.client.transfer_toggle_speed_limits_mode()
            return True
        except Exception as e:
            self.logger.error(f"Failed to set speed limits mode: {e}")
            return False

    # Logs
    def get_logs(self, normal=True, info=True, warning=True, critical=True, last_known_id=-1):
        try:
            return self.client.log_main(
                normal=normal, info=info, warning=warning, critical=critical, last_known_id=last_known_id
            )
        except Exception as e:
            self.logger.debug(f"Failed to get logs: {e}")
            return []

    # App Preferences & Server Info
    def get_app_preferences(self):
        try:
            return self.client.app_preferences()
        except Exception as e:
            self.logger.error(f"Failed to get app preferences: {e}")
            return {}

    def set_app_preferences(self, prefs):
        try:
            self.client.app_set_preferences(prefs=prefs)
            return True
        except Exception as e:
            self.logger.error(f"Failed to set app preferences: {e}")
            return False

    def get_free_space(self, path):
        try:
            return self.client.app_get_free_space_at_path(path=path)
        except Exception as e:
            self.logger.debug(f"Failed to get free space for {path}: {e}")
            return None

    def get_version(self):
        try:
            return self.client.app_version()
        except Exception:
            return "Unknown"

    def get_webapi_version(self):
        try:
            return self.client.app_web_api_version()
        except Exception:
            return "Unknown"
