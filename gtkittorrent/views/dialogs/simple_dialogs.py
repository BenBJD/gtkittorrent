import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw

class CategoryDialog(Adw.MessageDialog):
    """Dialog for creating or editing a category."""
    def __init__(self, parent, category_name="", save_path="", is_edit=False):
        super().__init__(
            transient_for=parent,
            heading="Edit Category" if is_edit else "New Category",
            body="Specify category name and default save path."
        )
        self.is_edit = is_edit

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        
        self.name_entry = Gtk.Entry(placeholder_text="Category name")
        self.name_entry.set_text(category_name)
        if is_edit:
            self.name_entry.set_editable(False)
            self.name_entry.set_sensitive(False)
        box.append(self.name_entry)

        self.path_entry = Gtk.Entry(placeholder_text="Save path (optional)")
        self.path_entry.set_text(save_path or "")
        box.append(self.path_entry)

        self.set_extra_child(box)

        self.add_response("cancel", "Cancel")
        self.add_response("save", "Save" if is_edit else "Add")
        self.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        self.set_default_response("save")
        self.set_close_response("cancel")

    def get_data(self):
        return self.name_entry.get_text().strip(), self.path_entry.get_text().strip()


class TagDialog(Adw.MessageDialog):
    """Dialog for creating one or more tags."""
    def __init__(self, parent):
        super().__init__(
            transient_for=parent,
            heading="New Tag",
            body="Enter tag name (comma-separated for multiple tags):"
        )
        self.entry = Gtk.Entry(placeholder_text="tag1, tag2")
        self.entry.set_margin_top(12)
        self.entry.set_margin_bottom(12)
        self.entry.set_margin_start(12)
        self.entry.set_margin_end(12)
        self.set_extra_child(self.entry)

        self.add_response("cancel", "Cancel")
        self.add_response("add", "Add")
        self.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)
        self.set_default_response("add")
        self.set_close_response("cancel")

    def get_tags(self):
        text = self.entry.get_text().strip()
        if not text:
            return []
        return [t.strip() for t in text.split(",") if t.strip()]


class LocationDialog(Adw.MessageDialog):
    """Dialog for setting the torrent save path/location."""
    def __init__(self, parent, current_path=""):
        super().__init__(
            transient_for=parent,
            heading="Set Location",
            body="Choose new download location for selected torrent(s):"
        )
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6, margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        
        self.entry = Gtk.Entry(hexpand=True)
        self.entry.set_text(current_path or "")
        box.append(self.entry)

        browse_btn = Gtk.Button(icon_name="folder-open-symbolic", tooltip_text="Browse...")
        browse_btn.connect("clicked", self._on_browse)
        box.append(browse_btn)

        self.set_extra_child(box)

        self.add_response("cancel", "Cancel")
        self.add_response("save", "Save")
        self.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        self.set_default_response("save")
        self.set_close_response("cancel")

    def _on_browse(self, btn):
        dialog = Gtk.FileChooserNative(
            title="Select Save Directory",
            transient_for=self.get_transient_for(),
            action=Gtk.FileChooserAction.SELECT_FOLDER,
            accept_label="_Select",
            cancel_label="_Cancel"
        )
        def on_resp(d, resp):
            if resp == Gtk.ResponseType.ACCEPT:
                f = d.get_file()
                if f:
                    self.entry.set_text(f.get_path())
            d.destroy()
        dialog.connect("response", on_resp)
        dialog.show()

    def get_location(self):
        return self.entry.get_text().strip()


class SpeedLimitDialog(Adw.MessageDialog):
    """Dialog for setting torrent download/upload rate limits."""
    def __init__(self, parent, current_dl=0, current_up=0):
        super().__init__(
            transient_for=parent,
            heading="Set Torrent Speed Limits",
            body="Set speed limits in KiB/s (0 for unlimited):"
        )
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)

        dl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        dl_lbl = Gtk.Label(text="Download Limit:", xalign=0, hexpand=True)
        self.dl_spin = Gtk.SpinButton(
            adjustment=Gtk.Adjustment(lower=0, upper=1000000, step_increment=10, page_increment=100),
            climb_rate=1.0, digits=0
        )
        self.dl_spin.set_value(current_dl / 1024 if current_dl > 0 else 0)
        dl_box.append(dl_lbl)
        dl_box.append(self.dl_spin)
        box.append(dl_box)

        up_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        up_lbl = Gtk.Label(text="Upload Limit:", xalign=0, hexpand=True)
        self.up_spin = Gtk.SpinButton(
            adjustment=Gtk.Adjustment(lower=0, upper=1000000, step_increment=10, page_increment=100),
            climb_rate=1.0, digits=0
        )
        self.up_spin.set_value(current_up / 1024 if current_up > 0 else 0)
        up_box.append(up_lbl)
        up_box.append(self.up_spin)
        box.append(up_box)

        self.set_extra_child(box)

        self.add_response("cancel", "Cancel")
        self.add_response("save", "Apply")
        self.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        self.set_default_response("save")
        self.set_close_response("cancel")

    def get_limits(self):
        # Convert KiB/s to bytes/sec
        dl = int(self.dl_spin.get_value() * 1024)
        up = int(self.up_spin.get_value() * 1024)
        return dl, up
