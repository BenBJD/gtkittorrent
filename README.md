<img src="packaging/io.github.BenBJD.gtkittorrent.svg" width="128" height="128" alt="GTKittorrent Logo">

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

## Contributing and Local Deployment

#### Prerequisites:

```bash
# Arch (and derivatives)
sudo pacman -S uv gtk4 libadwaita base-devel
# TODO: More distros
```

### Setup & Running

```bash
git clone https://github.com/BenBJD/gtkittorrent.git
cd gtkittorrent

uv sync
uv run gtkittorrent
```