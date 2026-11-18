import gi
gi.require_version('Gtk', '4.0')
from gi.repository import GObject, Gio
from ..utils.formatters import format_bytes, format_percent


class FileItem(GObject.Object):
    index = GObject.Property(type=int, default=0)
    name = GObject.Property(type=str, default="")
    display_name = GObject.Property(type=str, default="")
    is_folder = GObject.Property(type=bool, default=False)
    size = GObject.Property(type=GObject.TYPE_INT64, default=0)
    size_str = GObject.Property(type=str, default="0 B")
    progress = GObject.Property(type=float, default=0.0)
    progress_str = GObject.Property(type=str, default="0.0%")
    priority = GObject.Property(type=int, default=1)  # 0=Do not download, 1=Normal, 6=High, 7=Maximum
    priority_str = GObject.Property(type=str, default="Normal")
    remaining_str = GObject.Property(type=str, default="0 B")

    PRIORITY_NAMES = {
        0: "Do not download",
        1: "Normal",
        6: "High",
        7: "Maximum",
    }

    def __init__(self, data=None, is_folder=False, display_name=""):
        super().__init__()
        self.is_folder = is_folder
        self.children = Gio.ListStore(item_type=FileItem) if is_folder else None
        self._leaf_items = []
        if display_name:
            self.display_name = display_name
        if data:
            self.update(data)

    def update(self, data):
        self.index = int(data.get('index', self.index))
        full_name = str(data.get('name', self.name))
        self.name = full_name
        if not self.display_name:
            self.display_name = full_name.rsplit("/", 1)[-1] if "/" in full_name else full_name
        sz = int(data.get('size', self.size))
        self.size = sz
        self.size_str = format_bytes(sz)

        prog = float(data.get('progress', self.progress))
        self.progress = prog
        self.progress_str = format_percent(prog)

        prio = int(data.get('priority', self.priority))
        self.priority = prio
        self.priority_str = self.PRIORITY_NAMES.get(prio, str(prio))

        rem_bytes = max(0, int(sz * (1.0 - prog)))
        self.remaining_str = format_bytes(rem_bytes)

    def get_descendant_leaves(self):
        if not self.is_folder:
            return [self]
        leaves = []
        for i in range(self.children.get_n_items()):
            child = self.children.get_item(i)
            leaves.extend(child.get_descendant_leaves())
        return leaves

    def refresh_folder_aggregates(self):
        if not self.is_folder or self.children is None:
            return
        total_size = 0
        done_bytes = 0.0
        rem_bytes = 0
        prios = set()

        for i in range(self.children.get_n_items()):
            child = self.children.get_item(i)
            if child.is_folder:
                child.refresh_folder_aggregates()
            total_size += child.size
            done_bytes += child.size * child.progress
            rem_bytes += max(0, int(child.size * (1.0 - child.progress)))
            if child.is_folder and child.priority == -1:
                prios.add(-1)
            else:
                prios.add(child.priority)

        self.size = total_size
        self.size_str = format_bytes(total_size)
        prog = (done_bytes / total_size) if total_size > 0 else 0.0
        self.progress = prog
        self.progress_str = format_percent(prog)
        self.remaining_str = format_bytes(rem_bytes)
        if len(prios) == 1:
            p = next(iter(prios))
            self.priority = p
            self.priority_str = "Mixed" if p == -1 else self.PRIORITY_NAMES.get(p, str(p))
        else:
            self.priority = -1
            self.priority_str = "Mixed"


def build_file_tree(files_data, root_store=None):
    """Build a hierarchical Gio.ListStore of FileItem nodes from flat file dicts.

    Returns (root_store, leaf_items_by_index).
    """
    if root_store is None:
        root_store = Gio.ListStore(item_type=FileItem)
    else:
        root_store.remove_all()

    folders = {}  # tuple(path_parts) -> FileItem
    leaves_by_index = {}

    def ensure_folder(parts):
        if parts in folders:
            return folders[parts]
        node = FileItem(
            data={"name": "/".join(parts)},
            is_folder=True,
            display_name=parts[-1],
        )
        folders[parts] = node
        if len(parts) == 1:
            root_store.append(node)
        else:
            parent = ensure_folder(parts[:-1])
            parent.children.append(node)
        return node

    for f_data in files_data:
        raw_name = str(f_data.get("name", "")).replace("\\", "/")
        parts = [p for p in raw_name.split("/") if p]
        if not parts:
            parts = [raw_name or "file"]
        leaf = FileItem(data=f_data, is_folder=False, display_name=parts[-1])
        leaves_by_index[leaf.index] = leaf
        if len(parts) == 1:
            root_store.append(leaf)
        else:
            parent = ensure_folder(tuple(parts[:-1]))
            parent.children.append(leaf)

    for i in range(root_store.get_n_items()):
        item = root_store.get_item(i)
        if item.is_folder:
            item.refresh_folder_aggregates()

    return root_store, leaves_by_index
