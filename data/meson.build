desktop_file = 'io.github.BenBJD.gtkittorrent.desktop'
desktop_file_path = meson.current_source_dir() / desktop_file

install_data(
  desktop_file,
  install_dir: get_option('datadir') / 'applications'
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils, args: [desktop_file_path])
endif

metainfo_file = 'io.github.BenBJD.gtkittorrent.metainfo.xml'
metainfo_file_path = meson.current_source_dir() / metainfo_file

install_data(
  metainfo_file,
  install_dir: get_option('datadir') / 'metainfo'
)

appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test('Validate metainfo file', appstreamcli, args: ['validate', '--no-net', metainfo_file_path])
endif

install_data(
  'icons/hicolor/scalable/apps/io.github.BenBJD.gtkittorrent.svg',
  install_dir: get_option('datadir') / 'icons/hicolor/scalable/apps'
)
