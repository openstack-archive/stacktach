BASE_IMAGE = 0x1
SNAPSHOT_IMAGE = 0x2

LINUX_IMAGE = 0x10
WINDOWS_IMAGE = 0x20
FREEBSD_IMAGE = 0x40

OS_UBUNTU = 0x100
OS_DEBIAN = 0x200
OS_CENTOS = 0x400
OS_RHEL = 0x800


def isset(num, flag):
    if not num:
        return False
    return num & flag > 0


flags = {'base' : BASE_IMAGE,
         'snapshot' : SNAPSHOT_IMAGE,
         'linux' : LINUX_IMAGE,
         'windows': WINDOWS_IMAGE,
         'freebsd': FREEBSD_IMAGE,
         'ubuntu' : OS_UBUNTU,
         'debian' : OS_DEBIAN,
         'centos' : OS_CENTOS,
         'rhel' : OS_RHEL}


def readable(num):
    result = []
    for k, v in flags.iteritems():
        if isset(num, v):
            result.append(k)
    return result


def get_numeric_code(payload, default=0):
    meta = payload.get('image_meta', {})
    if default == None:
        default = 0
    num = default

    image_type = meta.get('image_type', '')
    if image_type == 'base':
        num |= BASE_IMAGE
    if image_type == 'snapshot':
        num |= SNAPSHOT_IMAGE

    os_type = meta.get('os_type', payload.get('os_type', ''))
    if os_type == 'linux':
        num |= LINUX_IMAGE
    if os_type == 'windows':
        num |= WINDOWS_IMAGE
    if os_type == 'freebsd':
        num |= FREEBSD_IMAGE

    os_distro = meta.get('os_distro', '')
    if os_distro == 'ubuntu':
        num |= OS_UBUNTU
    if os_distro == 'debian':
        num |= OS_DEBIAN
    if os_distro == 'centos':
        num |= OS_CENTOS
    if os_distro == 'rhel':
        num |= OS_RHEL

    return num
