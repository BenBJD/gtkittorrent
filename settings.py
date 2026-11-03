import json
import os
import uuid
from gi.repository import GLib

class Settings:
    def __init__(self, config_dir=None):
        if config_dir:
            self.config_dir = config_dir
        else:
            config_parent = GLib.get_user_config_dir()
            self.config_dir = os.path.join(config_parent, "gtkittorrent")
            old_config_dir = os.path.join(config_parent, "gtkitorrent")
            if not os.path.exists(self.config_dir) and os.path.exists(old_config_dir):
                try:
                    import shutil
                    shutil.copytree(old_config_dir, self.config_dir)
                except Exception:
                    pass
        self.config_file = os.path.join(self.config_dir, "settings.json")
        self.defaults = {
            "host": "http://127.0.0.1:8080",
            "host_ip": "127.0.0.1",
            "port": "8080",
            "use_https": False,
            "username": "admin",
            "password": "adminpassword",
            "configured": False,
            "welcome_completed": False,
            "current_instance_id": "default",
            "engine_autostart": True,
            "engine_stop_on_exit": False,
            "engine_binary_preference": "auto",
            "column_order": [
                "#",
                "Name",
                "Size",
                "Done",
                "Status",
                "Seeds",
                "Peers",
                "Down Speed",
                "Up Speed",
                "ETA",
                "Ratio",
                "Category",
                "Tags",
                "Added On",
            ],
            "column_widths": {
                "#": 40,
                "Name": 280,
                "Size": 75,
                "Done": 160,
                "Status": 95,
                "Seeds": 65,
                "Peers": 65,
                "Down Speed": 85,
                "Up Speed": 85,
                "ETA": 65,
                "Ratio": 60,
                "Category": 85,
                "Tags": 85,
                "Added On": 120,
            },
            "visible_columns": {
                "#": True,
                "Name": True,
                "Size": True,
                "Done": True,
                "Status": True,
                "Seeds": True,
                "Peers": True,
                "Down Speed": True,
                "Up Speed": True,
                "ETA": True,
                "Ratio": True,
                "Category": True,
                "Tags": True,
                "Added On": True,
            },
            "instances": []
        }
        self.data = self.defaults.copy()
        self.load()

    def _ensure_instances(self):
        instances = self.data.get("instances")
        if not isinstance(instances, list):
            instances = []
            self.data["instances"] = instances

        if len(instances) == 0 and self.data.get("configured", False):
            host_ip = str(self.data.get("host_ip") or "127.0.0.1")
            port = str(self.data.get("port") or "8080")
            use_https = bool(self.data.get("use_https", False))
            username = str(self.data.get("username") or "admin")
            password = str(self.data.get("password") or "adminpassword")
            protocol = "https" if use_https else "http"
            host = self.data.get("host") or f"{protocol}://{host_ip}:{port}"
            is_local = host_ip in ("127.0.0.1", "localhost", "::1")
            default_inst = {
                "id": "default",
                "name": "Local qBittorrent" if is_local else "Server",
                "host_ip": host_ip,
                "port": port,
                "use_https": use_https,
                "username": username,
                "password": password,
                "host": host,
                "local": is_local
            }
            self.data["instances"] = [default_inst]
            self.data["current_instance_id"] = "default"
        else:
            has_local = False
            for inst in self.data["instances"]:
                if "id" not in inst:
                    inst["id"] = uuid.uuid4().hex[:8]
                if "name" not in inst:
                    inst["name"] = f"{inst.get('host_ip', '127.0.0.1')}:{inst.get('port', '8080')}"
                if "use_https" not in inst:
                    inst["use_https"] = False
                protocol = "https" if inst.get("use_https") else "http"
                if "host" not in inst:
                    inst["host"] = f"{protocol}://{inst.get('host_ip', '127.0.0.1')}:{inst.get('port', '8080')}"
                if "local" not in inst:
                    is_local_ip = inst.get("host_ip") in ("127.0.0.1", "localhost", "::1")
                    if is_local_ip and not has_local and "local" in inst.get("name", "").lower():
                        inst["local"] = True
                        has_local = True
                    else:
                        inst["local"] = False
                elif inst.get("local"):
                    if has_local:
                        inst["local"] = False
                    else:
                        has_local = True

        current_id = self.data.get("current_instance_id")
        inst_ids = [inst["id"] for inst in self.data["instances"]]
        if len(self.data["instances"]) > 0 and current_id not in inst_ids:
            self.data["current_instance_id"] = self.data["instances"][0]["id"]

        self._sync_top_level_from_current()

    def _sync_top_level_from_current(self):
        curr = self.get_current_instance()
        if curr:
            self.data["host_ip"] = curr.get("host_ip", "127.0.0.1")
            self.data["port"] = curr.get("port", "8080")
            self.data["username"] = curr.get("username", "admin")
            self.data["password"] = curr.get("password", "")
            self.data["use_https"] = curr.get("use_https", False)
            self.data["host"] = curr.get("host", f"http://{curr.get('host_ip', '127.0.0.1')}:{curr.get('port', '8080')}")
            self.data["name"] = curr.get("name", "Local qBittorrent")

    def load(self):
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_data = json.load(f)
                    if isinstance(loaded_data, dict):
                        self.data.update(loaded_data)
            except Exception as e:
                print(f"Error loading settings: {e}")
        self._ensure_instances()

    def save(self):
        if not os.path.exists(self.config_dir):
            try:
                os.makedirs(self.config_dir)
            except Exception as e:
                print(f"Error creating config directory: {e}")
                return
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key, default=None):
        if key in self.data:
            return self.data[key]
        if default is not None:
            return default
        return self.defaults.get(key)

    def set(self, key, value):
        self.data[key] = value
        if key in ["host_ip", "port", "username", "password", "use_https", "host", "name"]:
            curr = self.get_current_instance()
            if curr:
                curr[key] = value
                if key in ["host_ip", "port", "use_https"]:
                    protocol = "https" if curr.get("use_https") else "http"
                    curr["host"] = f"{protocol}://{curr.get('host_ip')}:{curr.get('port')}"
                    self.data["host"] = curr["host"]
        self.save()

    def get_instances(self):
        return list(self.data.get("instances", []))

    def get_current_instance_id(self):
        return self.data.get("current_instance_id")

    def get_current_instance(self):
        curr_id = self.data.get("current_instance_id")
        for inst in self.data.get("instances", []):
            if inst.get("id") == curr_id:
                return inst
        instances = self.data.get("instances", [])
        if instances:
            return instances[0]
        host_ip = str(self.data.get("host_ip") or "127.0.0.1")
        port = str(self.data.get("port") or "8080")
        use_https = bool(self.data.get("use_https", False))
        protocol = "https" if use_https else "http"
        return {
            "id": "default",
            "name": self.data.get("name") or "Local qBittorrent",
            "host_ip": host_ip,
            "port": port,
            "use_https": use_https,
            "username": str(self.data.get("username") or "admin"),
            "password": str(self.data.get("password") or ""),
            "host": self.data.get("host") or f"{protocol}://{host_ip}:{port}",
            "local": host_ip in ("127.0.0.1", "localhost", "::1")
        }

    def get_local_instance(self):
        for inst in self.data.get("instances", []):
            if inst.get("local", False):
                return inst
        return None

    def ensure_local_instance(self, port="8080", username="admin", password=""):
        local = self.get_local_instance()
        if not local:
            return self.add_instance(
                "Local qBittorrent",
                "127.0.0.1",
                str(port),
                username,
                password,
                local=True,
                make_active=False
            )
        return local

    def get_instance(self, instance_id):
        for inst in self.data.get("instances", []):
            if inst.get("id") == instance_id:
                return inst
        return None

    def set_current_instance_id(self, instance_id):
        inst = self.get_instance(instance_id)
        if inst:
            self.data["current_instance_id"] = instance_id
            self._sync_top_level_from_current()
            self.save()
            return True
        return False

    def add_instance(self, name, host_ip, port, username, password, use_https=False, local=False, make_active=True):
        new_id = uuid.uuid4().hex[:8]
        protocol = "https" if use_https else "http"
        full_host = f"{protocol}://{host_ip}:{port}"
        if local:
            for other in self.data.get("instances", []):
                other["local"] = False
        inst = {
            "id": new_id,
            "name": name.strip() or ("Local qBittorrent" if local else "Server"),
            "host_ip": str(host_ip).strip(),
            "port": str(port).strip(),
            "use_https": bool(use_https),
            "username": str(username).strip(),
            "password": str(password),
            "host": full_host,
            "local": bool(local)
        }
        self.data.setdefault("instances", []).append(inst)
        if make_active:
            self.data["current_instance_id"] = new_id
            self._sync_top_level_from_current()
        self.save()
        return inst

    def update_instance(self, instance_id, **kwargs):
        inst = self.get_instance(instance_id)
        if not inst:
            return False
        if kwargs.get("local"):
            for other in self.data.get("instances", []):
                if other.get("id") != instance_id:
                    other["local"] = False
        for k in ["name", "host_ip", "port", "username", "password", "use_https", "local"]:
            if k in kwargs and kwargs[k] is not None:
                inst[k] = kwargs[k]
        protocol = "https" if inst.get("use_https") else "http"
        inst["host"] = f"{protocol}://{inst.get('host_ip')}:{inst.get('port')}"
        if self.get_current_instance_id() == instance_id:
            self._sync_top_level_from_current()
        self.save()
        return True
        for k in ["name", "host_ip", "port", "username", "password", "use_https"]:
            if k in kwargs and kwargs[k] is not None:
                inst[k] = kwargs[k]
        protocol = "https" if inst.get("use_https") else "http"
        inst["host"] = f"{protocol}://{inst.get('host_ip')}:{inst.get('port')}"
        if self.get_current_instance_id() == instance_id:
            self._sync_top_level_from_current()
        self.save()
        return True

    def delete_instance(self, instance_id):
        instances = self.data.get("instances", [])
        if len(instances) <= 1:
            return False
        
        inst_to_del = self.get_instance(instance_id)
        if not inst_to_del:
            return False
        
        self.data["instances"] = [inst for inst in instances if inst.get("id") != instance_id]
        if self.data.get("current_instance_id") == instance_id:
            self.data["current_instance_id"] = self.data["instances"][0]["id"]
            self._sync_top_level_from_current()
        self.save()
        return True

    def get_column_widths(self):
        defaults = self.defaults.get("column_widths", {})
        saved = self.data.get("column_widths")
        if isinstance(saved, dict):
            merged = defaults.copy()
            merged.update(saved)
            return merged
        return defaults.copy()

    def set_column_widths(self, widths):
        if isinstance(widths, dict):
            self.data["column_widths"] = dict(widths)
            self.save()

    def set_column_width(self, col_name, width):
        if "column_widths" not in self.data or not isinstance(self.data["column_widths"], dict):
            self.data["column_widths"] = self.get_column_widths()
        self.data["column_widths"][col_name] = width
        self.save()

    def get_visible_columns(self):
        defaults = self.defaults.get("visible_columns", {})
        saved = self.data.get("visible_columns")
        if isinstance(saved, dict):
            merged = defaults.copy()
            merged.update(saved)
            return merged
        return defaults.copy()

    def set_visible_columns(self, cols):
        if isinstance(cols, dict):
            self.data["visible_columns"] = dict(cols)
            self.save()

    def set_column_visible(self, col_name, visible):
        if "visible_columns" not in self.data or not isinstance(self.data["visible_columns"], dict):
            self.data["visible_columns"] = self.get_visible_columns()
        self.data["visible_columns"][col_name] = bool(visible)
        self.save()

    def get_column_order(self):
        defaults = list(self.defaults.get("column_order", []))
        saved = self.data.get("column_order")
        if isinstance(saved, list) and saved:
            result = [col for col in saved if col in defaults]
            for col in defaults:
                if col not in result:
                    result.append(col)
            return result
        return defaults

    def set_column_order(self, order):
        if isinstance(order, list):
            self.data["column_order"] = list(order)
            self.save()
