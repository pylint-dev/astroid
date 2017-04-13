import astroid


def _json_transform():
    # pylint always thinks that json.loads returns a bool.
    # Message: Instance of 'bool' has no 'get' member (no-member)
    return astroid.parse('''
    def loads(s, encoding=None, cls=None, object_hook=None, parse_float=None,
        parse_int=None, parse_constant=None, object_pairs_hook=None, **kw):
        if 1 in kw: return {}
        if 2 in kw: return []
        if 3 in kw: return True
        if 4 in kw: return ""
        if 5 in kw: return u""
        if 6 in kw: return None
        if 7 in kw: return 3.14
    ''')


astroid.register_module_extender(astroid.MANAGER, 'json', _json_transform)
astroid.register_module_extender(astroid.MANAGER, 'simplejson', _json_transform)
