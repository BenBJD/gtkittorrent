import os
import configparser
import logging

logger = logging.getLogger(__name__)

def get_qbt_config_paths():
    """Return a list of potential qBittorrent config file paths."""
    config_dir = os.path.expanduser("~/.config/qBittorrent")
    return [
        os.path.join(config_dir, "qBittorrent.conf"),
        os.path.join(config_dir, "qBittorrent-nox.conf")
    ]

def find_existing_config_path():
    """Find the first existing qBittorrent config path, or default to standard."""
    paths = get_qbt_config_paths()
    for p in paths:
        if os.path.isfile(p):
            return p
    return paths[0]

def read_qbt_config():
    """Parse qBittorrent config file and extract Web UI settings.
    
    Returns:
        dict: Information about configuration existence, WebUI state, port, auth, etc.
    """
    path = find_existing_config_path()
    info = {
        "exists": os.path.isfile(path),
        "path": path,
        "webui_enabled": False,
        "webui_port": 8080,
        "webui_username": "admin",
        "localhost_auth": True,
        "has_password": False,
    }

    if not info["exists"]:
        return info

    try:
        parser = configparser.RawConfigParser()
        parser.optionxform = str  # Preserve case
        parser.read(path, encoding='utf-8')

        webui_section = None
        for sec in parser.sections():
            if sec.lower() == "webui":
                webui_section = sec
                break

        if webui_section:
            # Enabled
            if parser.has_option(webui_section, "Enabled"):
                raw_enabled = parser.get(webui_section, "Enabled").strip().lower()
                info["webui_enabled"] = raw_enabled in ("true", "1", "yes")

            # Port
            if parser.has_option(webui_section, "Port"):
                try:
                    info["webui_port"] = int(parser.get(webui_section, "Port").strip())
                except ValueError:
                    info["webui_port"] = 8080

            # Username
            if parser.has_option(webui_section, "Username"):
                uname = parser.get(webui_section, "Username").strip()
                if uname:
                    info["webui_username"] = uname

            # LocalHostAuth (in qBittorrent, false means bypass authentication for localhost)
            if parser.has_option(webui_section, "LocalHostAuth"):
                raw_auth = parser.get(webui_section, "LocalHostAuth").strip().lower()
                info["localhost_auth"] = raw_auth in ("true", "1", "yes")

            # Check if password is set
            has_pw = any(
                parser.has_option(webui_section, opt)
                for opt in ["Password_PBKDF2", "Password_SHA256", "Password"]
            )
            info["has_password"] = has_pw

    except Exception as e:
        logger.error(f"Error reading qBittorrent config from {path}: {e}")

    return info

def configure_qbt_webui(port=8080, enable=True, bypass_localhost_auth=True):
    """Update or create the [WebUI] section in qBittorrent config file.
    
    Args:
        port (int): Port for Web UI (default 8080)
        enable (bool): Whether to enable Web UI
        bypass_localhost_auth (bool): If True, sets LocalHostAuth=false to bypass auth on 127.0.0.1
        
    Returns:
        tuple: (success: bool, error_message: str | None)
    """
    path = find_existing_config_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)

    try:
        parser = configparser.RawConfigParser()
        parser.optionxform = str
        if os.path.isfile(path):
            parser.read(path, encoding='utf-8')

        webui_section = "WebUI"
        for sec in parser.sections():
            if sec.lower() == "webui":
                webui_section = sec
                break

        if not parser.has_section(webui_section):
            parser.add_section(webui_section)

        parser.set(webui_section, "Enabled", "true" if enable else "false")
        parser.set(webui_section, "Port", str(port))
        if bypass_localhost_auth:
            parser.set(webui_section, "LocalHostAuth", "false")

        with open(path, "w", encoding='utf-8') as f:
            parser.write(f)

        return True, None
    except Exception as e:
        logger.error(f"Failed to configure qBittorrent WebUI at {path}: {e}")
        return False, str(e)
