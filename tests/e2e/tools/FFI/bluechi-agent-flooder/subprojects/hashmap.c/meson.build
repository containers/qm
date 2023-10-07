project('hashmap.c',
    ['c'],
    license : 'MIT',
)

inc_hashmapc = include_directories('.')

lib_hashmapc = library('hashmapc',
    ['hashmap.c'],
    include_directories : include_directories('.'),
    soversion : '0',
    gnu_symbol_visibility: 'hidden'
)

hashmapc_dep = declare_dependency(
    link_with : lib_hashmapc,
    include_directories : inc_hashmapc
)
