def empty_reconciler_instance():
    r_instance = {
        'id': None,
        'tenant': None,
        'launched_at': None,
        'deleted': False,
        'deleted_at': None,
        'instance_type_ud': None,
        'os_architecture': None,
        'os_distro': None,
        'os_version': None,
        'rax_options': None,
    }
    return r_instance
