"""One validated loopback ADB endpoint per independently reviewed bundle."""

LOOPBACK = '127.0.0.1'
LEGACY_ARCHIVE_PORT = 5039


def port_number(value):
    if type(value) is not int or not 1 <= value <= 65535:
        raise ValueError('ADB port must be an integer in 1..65535')
    return value


def bundle_port(bundle):
    # Earlier immutable archives recorded this endpoint in their runner
    # source rather than in the bundle. New reviews can select any local port.
    return port_number(bundle.get('adb_server_port', LEGACY_ARCHIVE_PORT))


def device_arguments(adb, port, serial, *args):
    return (adb, '-H', LOOPBACK, '-P', str(port_number(port)), '-s', serial, *args)
