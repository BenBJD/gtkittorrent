python_sources = [
  'gtkittorrent/__init__.py',
  'gtkittorrent/__main__.py',
  'gtkittorrent/app.py',
  'gtkittorrent/main.py',
  'gtkittorrent/settings.py',
]

py_installation.install_sources(
  python_sources,
  subdir: 'gtkittorrent'
)

py_installation.install_sources(
  [
    'gtkittorrent/client/__init__.py',
    'gtkittorrent/client/client.py',
    'gtkittorrent/client/daemon.py',
  ],
  subdir: 'gtkittorrent/client'
)

py_installation.install_sources(
  [
    'gtkittorrent/models/__init__.py',
    'gtkittorrent/models/file_item.py',
    'gtkittorrent/models/filter_item.py',
    'gtkittorrent/models/peer.py',
    'gtkittorrent/models/torrent.py',
    'gtkittorrent/models/tracker.py',
  ],
  subdir: 'gtkittorrent/models'
)

py_installation.install_sources(
  [
    'gtkittorrent/utils/__init__.py',
    'gtkittorrent/utils/formatters.py',
    'gtkittorrent/utils/qbt_config.py',
  ],
  subdir: 'gtkittorrent/utils'
)

py_installation.install_sources(
  [
    'gtkittorrent/views/__init__.py',
    'gtkittorrent/views/main_window.py',
    'gtkittorrent/views/sidebar.py',
    'gtkittorrent/views/status_bar.py',
    'gtkittorrent/views/torrent_table.py',
    'gtkittorrent/views/welcome_window.py',
  ],
  subdir: 'gtkittorrent/views'
)

py_installation.install_sources(
  [
    'gtkittorrent/views/details/__init__.py',
    'gtkittorrent/views/details/content_tab.py',
    'gtkittorrent/views/details/details_notebook.py',
    'gtkittorrent/views/details/general_tab.py',
    'gtkittorrent/views/details/log_tab.py',
    'gtkittorrent/views/details/peers_tab.py',
    'gtkittorrent/views/details/speed_tab.py',
    'gtkittorrent/views/details/trackers_tab.py',
  ],
  subdir: 'gtkittorrent/views/details'
)

py_installation.install_sources(
  [
    'gtkittorrent/views/dialogs/__init__.py',
    'gtkittorrent/views/dialogs/add_torrent_dialog.py',
    'gtkittorrent/views/dialogs/instance_dialog.py',
    'gtkittorrent/views/dialogs/preferences_dialog.py',
    'gtkittorrent/views/dialogs/simple_dialogs.py',
  ],
  subdir: 'gtkittorrent/views/dialogs'
)

conf = configuration_data()
conf.set('PYTHON', py_installation.full_path())
conf.set('PYTHON_DIR', py_installation.get_install_dir())
conf.set('VERSION', meson.project_version())

configure_file(
  input: 'gtkittorrent.in',
  output: 'gtkittorrent',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)
