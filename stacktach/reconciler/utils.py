def empty_reconciler_instance():
    r_instance = {
        'id': None,
        'tenant': None,
        'launched_at': None,
        'deleted': False,
        'deleted_at': None,
        'instance_type_id': None,
        'os_architecture': '',
        'os_distro': '',
        'os_version': '',
        'rax_options': '',
    }
    return r_instance
