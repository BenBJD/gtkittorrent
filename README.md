<p align="center">
  <img src="data/icons/hicolor/scalable/apps/io.github.BenBJD.gtkittorrent.svg" width="128" height="128" alt="GTKittorrent Logo">
</p>

<h1 align="center">GTKittorrent</h1>

<p align="center">
  A modern, full-featured GTK4 and Libadwaita frontend for qBittorrent, designed to achieve feature parity with qBittorrent's official Qt desktop UI while following GNOME design conventions.
</p>

## Features

### 🎛 Full Torrent Management
- **Sorting & Columns**: Sort by Queue Priority (`#`), Name, Size, Done/Progress, Status, Seeds (connected/swarm), Peers (connected/swarm), Down Speed, Up Speed, ETA, Share Ratio, Category, Tags, and Added On with resizable columns and persistent widths saved in settings.
- **Drag-to-Rearrange Columns**: Drag and reorder columns directly in the torrent table, with column positions automatically preserved and restored across sessions.
- **Column Selector & Auto-Resize**: Dedicated column selector dropdown (via top bar button or right-clicking table headers) to toggle visibility for each column, with instant "Resize Columns to Fit" and "Reset Column Order" actions.
- **Filtering & Search**: Real-time name/hash search filter bar with instant results.
- **Multi-Selection**: Bulk actions on multiple torrents (Shift/Ctrl select and Ctrl+A).
- **Rich Context Menu**:
  - Pause, Resume, Force Start.
  - Queue Priorities: Top, Up, Down, Bottom.
  - Force Recheck & Force Reannounce.
  - Set Download & Upload Speed Limits.
  - Set Save Location / Move Storage.
  - Rename Torrent.
  - Add & Remove Tags.
  - Set Categories.
  - Delete with option to also delete files on disk.

### 📁 Sidebar Filtering
- **Queue Priority Toolbar**: Dedicated priority controls (Top, Up, Down, Bottom) situated directly at the top of the sidebar for quick queue reordering.
- **Status Filters**: All, Downloading, Seeding, Completed, Resumed/Active, Paused/Inactive, Stalled, Stalled Downloading, Stalled Uploading, Checking, Moving, and Errored with live count badges.
- **Categories**: Full category manager (Add, Edit save path, Delete) with torrent counts.
- **Tags**: Create, manage, and filter by tags with counts.
- **Trackers**: Filter torrents by tracker hostname.

### 📊 Comprehensive Details Panel
- **General Tab**:
  - Organized **Transfer** statistics: Elapsed Time, Remaining ETA, Downloaded, Uploaded, DL/UL Speeds, Seeds, Peers, Share Ratio, Reannounce countdown.
  - Detailed **Information**: Total Size, Pieces count & size, Hash, Save Path, Created By, Added On, Completed On, Comment.
- **Trackers Tab**: Full tracker table (Tier, URL, Status, Peers, Seeds, Leechers, Message) with Add, Edit, Remove, and Force Reannounce controls.
- **Peers Tab**: Connected swarm peers table with IP, Port, Client, Flags, Progress, and Live Down/Up speeds.
- **Content / Files Tab**: Complete file list with individual file progress, sizes, and file priorities (Do Not Download, Normal, High, Maximum) and file renaming.
- **Speed Tab**: Real-time bandwidth graph drawn with Cairo showing download and upload speeds over time.
- **Execution Log Tab**: qBittorrent server execution log with Normal, Info, Warning, and Critical level toggles.

### 🖥️ Multiple Instances & Server Chooser
- **Top Bar Instance Chooser**: Dropdown button in the header bar showing the active instance name and address with quick-switch popover.
- **Instant Instance Switching**: Seamlessly switch between local qBittorrent and remote servers with a single click, automatically reloading torrents and connection stats.
- **Add & Edit Instances**: Built-in instance dialog supporting custom instance names, IP/domain, port, credentials, HTTPS, and a real-time connection verification test.
- **Instance Management**: Rename, edit connection parameters, or delete instances with confirmation directly from the dropdown menu.

### 🌐 Status Bar & Dialogs
- **Welcome & Setup Screen**: First-run setup assistant with real-time connection verification, server IP, port, credentials, and HTTPS configuration.
- **Preferences Dialog**: Full settings window covering Web UI server with a **Test Connection** button, Downloads (save path, incomplete paths, `.!qB` extension, pre-allocation), Global & Alternative Speed limits, and BitTorrent queuing & privacy settings.
- **Status Bar**: Global download and upload speeds, total session transfer statistics, DHT nodes count, connection state, free disk space indicator, and Alternative Speed Limits (Turtle Mode) toggle.
- **Add Torrent Dialog**: Comprehensive options for adding files or URLs/magnets (select save directory, assign category and tags, start paused, sequential download, first/last pieces first, skip hash checking).

## Prerequisites

GTK4, Libadwaita, and Python GObject introspection libraries:

### Debian / Ubuntu
```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1
```

### Arch Linux / Manjaro
```bash
sudo pacman -S python-gobject gtk4 libadwaita
```

### Fedora
```bash
sudo dnf install python3-gobject gtk4 libadwaita
```

## Installation

### Using uv / pip
```bash
git clone https://github.com/BenBJD/gtkittorrent.git
cd gtkittorrent
pip install .
```
Or build and install the wheel directly:
```bash
uv build
pip install dist/*.whl
```

## Usage

1. Ensure qBittorrent is running with Web UI enabled (Tools -> Preferences -> Web UI).
2. Default connection: `http://127.0.0.1:8080` (credentials can be configured in Preferences).
3. Run GTKittorrent:
```bash
# If installed as a package / wheel
gtkittorrent

# Or directly from source checkout
python main.py
# or
python -m gtkittorrent
```
