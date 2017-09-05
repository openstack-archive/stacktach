import pbr.version


version_info = pbr.version.VersionInfo('stacktach')


def get_version():
    return version_info.version_string()
