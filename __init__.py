# The version of Review Board.
#
# This is in the format of:
#
#   (Major, Minor, Micro, alpha/beta/rc/final, Release Number, Released)
#
VERSION = (1, 0, 0, 'rc', 4, False)


def get_version_string():
    version = '%s.%s' % (VERSION[0], VERSION[1])

    if VERSION[2]:
        version += str(VERSION[2])

    if VERSION[3] != 'final':
        if VERSION[3] == 'rc':
            version += ' RC%s' % VERSION[4]
        else:
            version += ' %s %s' % (release_tag, VERSION[4])

    if not is_release():
        version += " (dev)"

    return version


def get_package_version():
    version = '%s.%s' % (VERSION[0], VERSION[1])

    if VERSION[2]:
        version += str(VERSION[2])

    if VERSION[3] != 'final':
        version += '%s%s' % (VERSION[3], VERSION[4])

    return version


def is_release():
    return VERSION[5]
