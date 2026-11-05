project('gtkittorrent',
  version: '0.2.0',
  meson_version: '>= 0.62.0',
  default_options: ['warning_level=2']
)

gnome = import('gnome')
python = import('python')

py_installation = python.find_installation('python3')

subdir('data')
subdir('src')

pytest = find_program('pytest', required: false)
if pytest.found()
  test('pytest', pytest,
    args: ['-v'],
    workdir: meson.project_source_root(),
    env: {'PYTHONPATH': meson.project_source_root() / 'src'}
  )
endif

gnome.post_install(
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
