<img src="data/icons/hicolor/scalable/apps/io.github.BenBJD.gtkittorrent.svg" width="128" height="128" alt="GTKittorrent Logo">

# GTKittorrent

A modern, full-featured GTK4 and Libadwaita frontend for qBittorrent, designed to (eventually) achieve feature parity with qBittorrent's official Qt desktop UI while following GNOME design conventions.

## What is implemented

- Support for multiple instances, including automatic setup for a local qbittorrent-nox or qbittorrent.
- The usual qBittorrent functionality for downloading and managing torrents.
- Some of the qBittorrent settings
- TODO: List more

## What is not (yet?) implemented

- Torrent creation
- RSS and Search
- Most of the less vital settings for everyday use, anything advanced
- TODO: List more

## Installation

The headless version of qBittorrent is recommended for a smoother experience.
It uses the same connection method and configuration files as the official qBittorrent Qt UI, plus both headless and gui versions can be installed without conflict.
Search your package manager for `qbittorrent-nox`.

### Arch Linux (and derivatives)

Install from the AUR using your preferred helper:

```bash
yay -S gtkittorrent
# or
paru -S gtkittorrent
```

### Flatpak

```bash
# TODO: This
```

### From Source

#### Dependencies

```bash
# Arch Linux (and derivatives)
sudo pacman -S python python-gobject libadwaita base-devel meson ninja
yay -S python-qbittorrent-api # or paru -S python-qbittorrent-api

# Fedora
sudo dnf install python3 python3-gobject libadwaita meson ninja-build python3-pip
pip install --user qbittorrent-api # For Fedora 38+ add --break-system-packages

# Ubuntu / Debian (24.04+)
sudo apt install python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 meson ninja-build python3-pip
pip install --user qbittorrent-api # For 23.04+ add --break-system-packages
```

#### Build and Install

```bash
git clone https://github.com/BenBJD/gtkittorrent.git
cd gtkittorrent

# Configure build directory
meson setup build --prefix=/usr

# Compile and install system-wide
meson compile -C build
sudo meson install -C build
```

## Contributing

For development, `uv` is recommended:

### Prerequisites:

```bash
# Arch (and derivatives)
sudo pacman -S uv libadwaita base-devel meson ninja

# Fedora
sudo dnf install uv libadwaita meson ninja-build

# Ubuntu / Debian (24.04+)
sudo apt install libadwaita-1-dev gir1.2-adw-1 meson ninja-build
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Setup & Running

```bash
git clone https://github.com/BenBJD/gtkittorrent.git
cd gtkittorrent

uv sync
uv run gtkittorrent
```

### Running Tests

```bash
# Run unit tests via pytest
uv run pytest

# Or run full test suite with Meson
meson setup build
meson test -C build --print-errorlogs
```
