"""Pure identity check for the owner's interchangeable TWRP/OrangeFox Recovery.

No transport,properties,USB or subprocess is constructed by this module.
Actual serial/product/slot and storage protections remain caller obligations.
"""
PROPERTIES = ('ro.orangefox.boot', 'ro.twrp.boot', 'ro.twrp.version')


def inspect_recovery(properties):
    """Accept actual recovery markers;an ADB transport state alone is insufficient."""
    values = {key: properties.get(key, '') for key in PROPERTIES}
    if any(not isinstance(value, str) or len(value) > 256 or
           any(ord(char) < 32 for char in value) for value in values.values()):
        raise ValueError('invalid Recovery identity properties')
    if values['ro.orangefox.boot'] == '1':
        family = 'OrangeFox'
    elif values['ro.twrp.boot'] == '1' and values['ro.twrp.version'].strip():
        family = 'TWRP'
    else:
        raise ValueError('actual TWRP/OrangeFox Recovery markers required')
    return dict(family=family, properties=values,
                identity_scope='property identity only;not hardware or storage authority')
