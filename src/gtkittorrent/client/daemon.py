import os
import shutil
import socket
import subprocess
import threading
import time
import urllib.request
import urllib.error
import logging
from gi.repository import GLib

from ..utils.qbt_config import read_qbt_config, configure_qbt_webui

logger = logging.getLogger(__name__)

class LocalDaemonManager:
    """Manages detecting, launching, monitoring, and controlling local qBittorrent daemon instances."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = LocalDaemonManager()
        return cls._instance

    def __init__(self):
        self.managed_process = None
        self._is_starting = False

    def get_binary_info(self, preference="auto"):
        """Inspect system for available qBittorrent binaries.
        
        Args:
            preference: 'auto', 'nox', or 'gui'
            
        Returns:
            dict: Info with available binaries and recommendation.
        """
        nox_path = shutil.which("qbittorrent-nox")
        gui_path = shutil.which("qbittorrent")

        has_nox = bool(nox_path)
        has_gui = bool(gui_path)

        preferred = None
        preferred_path = None

        if preference == "nox" and has_nox:
            preferred = "qbittorrent-nox"
            preferred_path = nox_path
        elif preference == "gui" and has_gui:
            preferred = "qbittorrent"
            preferred_path = gui_path
        else: # auto
            if has_nox:
                preferred = "qbittorrent-nox"
                preferred_path = nox_path
            elif has_gui:
                preferred = "qbittorrent"
                preferred_path = gui_path

        # If user only has GUI, recommend installing nox for pure headless experience
        recommend_nox = has_gui and not has_nox

        return {
            "has_nox": has_nox,
            "nox_path": nox_path,
            "has_gui": has_gui,
            "gui_path": gui_path,
            "preferred": preferred,
            "preferred_path": preferred_path,
            "recommend_nox": recommend_nox,
            "any_installed": has_nox or has_gui
        }

    def is_port_open(self, host="127.0.0.1", port=8080, timeout=0.8):
        """Check if port is accepting TCP connections."""
        try:
            with socket.create_connection((host, int(port)), timeout=timeout):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def is_engine_responsive(self, host_url="http://127.0.0.1:8080", timeout=1.2):
        """Check if qBittorrent Web API responds at target URL."""
        test_url = f"{host_url.rstrip('/')}/api/v2/app/webapiVersion"
        req = urllib.request.Request(
            test_url,
            headers={"User-Agent": "GTKittorrent-Probe/1.0"}
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status in (200, 204)
        except urllib.error.HTTPError as e:
            # 401 Unauthorized or 403 Forbidden means qBittorrent WebUI is alive and running!
            if e.code in (401, 403, 200, 204):
                return True
            return False
        except Exception:
            return False

    def is_engine_running(self, host_ip="127.0.0.1", port=8080):
        """Check if local engine is running via HTTP probe or port."""
        protocol = "http"
        url = f"{protocol}://{host_ip}:{port}"
        if self.is_engine_responsive(url):
            return True
        return self.is_port_open(host_ip, port)

    def prepare_local_configuration(self, port=8080):
        """Ensure Web UI is enabled in qBittorrent configuration before starting.
        Bypasses localhost authentication for seamless local integration.
        """
        config = read_qbt_config()
        if not config["exists"] or not config["webui_enabled"] or config.get("localhost_auth", True):
            success, err = configure_qbt_webui(port=port, enable=True, bypass_localhost_auth=True)
            if success:
                logger.info("Auto-configured qBittorrent Web UI in ~/.config/qBittorrent/qBittorrent.conf")
            else:
                logger.warning(f"Could not auto-configure qBittorrent.conf: {err}")

    def start_daemon_async(self, port=8080, preference="auto", callback=None):
        """Start local qBittorrent process in background thread and monitor readiness.
        
        Args:
            port: Port to run on (default 8080)
            preference: 'auto', 'nox', or 'gui'
            callback: callable(success: bool, message: str) called on GLib main thread
        """
        if self._is_starting:
            if callback:
                callback(False, "Engine is already starting...")
            return

        bin_info = self.get_binary_info(preference=preference)
        if not bin_info["preferred_path"]:
            if callback:
                callback(False, "qBittorrent is not installed. Please install qbittorrent-nox or qbittorrent.")
            return

        self._is_starting = True

        def _worker():
            # If engine is already running, succeed immediately
            if self.is_engine_running("127.0.0.1", port):
                self._is_starting = False
                logger.info(f"{bin_info['preferred']} is already running on port {port}")
                if callback:
                    GLib.idle_add(callback, True, f"{bin_info['preferred']} is already running")
                return

            # 1. Prepare config if needed (enable Web UI & bypass localhost auth)
            self.prepare_local_configuration(port=port)

            cmd = [bin_info["preferred_path"]]
            if bin_info["preferred"] == "qbittorrent-nox":
                cmd.extend(["--confirm-legal-notice", f"--webui-port={port}"])
            else:
                cmd.extend(["--no-splash", f"--webui-port={port}"])

            logger.info(f"Launching local qBittorrent engine: {' '.join(cmd)}")
            try:
                # Start in new session (detached daemon)
                proc = subprocess.Popen(
                    cmd,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )
                self.managed_process = proc
            except Exception as e:
                self._is_starting = False
                logger.error(f"Failed to spawn daemon process: {e}")
                if callback:
                    GLib.idle_add(callback, False, f"Failed to launch {bin_info['preferred']}: {e}")
                return

            # Wait for Web UI to become responsive (up to 12 seconds)
            started = False
            for _ in range(24):
                time.sleep(0.5)
                if self.is_engine_running("127.0.0.1", port):
                    started = True
                    break
                if proc.poll() is not None:
                    if self.is_engine_running("127.0.0.1", port):
                        started = True
                    break

            self._is_starting = False
            if started:
                msg = f"Started {bin_info['preferred']} successfully"
                logger.info(msg)
                if callback:
                    GLib.idle_add(callback, True, msg)
            else:
                exit_code = proc.poll()
                err_msg = f"Timed out waiting for {bin_info['preferred']} to start"
                if exit_code is not None:
                    err_msg = f"{bin_info['preferred']} exited unexpectedly (code {exit_code})"
                logger.error(err_msg)
                if callback:
                    GLib.idle_add(callback, False, err_msg)

        threading.Thread(target=_worker, daemon=True).start()

    def stop_daemon(self, client=None):
        """Stop local daemon cleanly."""
        stopped = False
        # 1. Try graceful Web API shutdown if client is provided and connected
        if client and hasattr(client, "client") and client.client:
            try:
                if hasattr(client.client, "app_shutdown"):
                    client.client.app_shutdown()
                    logger.info("Sent app_shutdown via Web API")
                    stopped = True
            except Exception as e:
                logger.debug(f"API shutdown failed: {e}")

        # 2. Terminate managed subprocess if alive
        if self.managed_process and self.managed_process.poll() is None:
            try:
                self.managed_process.terminate()
                self.managed_process.wait(timeout=2.0)
                logger.info("Terminated managed qBittorrent process")
                stopped = True
            except Exception:
                try:
                    self.managed_process.kill()
                    stopped = True
                except Exception:
                    pass

        # 3. Fallback: terminate unmanaged local qbittorrent processes if still listening
        try:
            subprocess.run(["pkill", "-TERM", "qbittorrent-nox"], check=False)
            stopped = True
        except Exception:
            pass

        return stopped

    def restart_daemon_async(self, port=8080, client=None, preference="auto", callback=None):
        """Restart local daemon process asynchronously."""
        def _restart_worker():
            self.stop_daemon(client=client)
            # Wait for port to become free (up to 3 seconds)
            for _ in range(6):
                time.sleep(0.5)
                if not self.is_port_open("127.0.0.1", port):
                    break
            # Start daemon
            self.start_daemon_async(port=port, preference=preference, callback=callback)

        threading.Thread(target=_restart_worker, daemon=True).start()
