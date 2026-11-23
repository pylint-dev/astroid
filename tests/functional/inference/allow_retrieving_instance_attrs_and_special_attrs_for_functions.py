class A:
    def test(self):
        "a"
    # Add `__doc__` to `FunctionDef.instance_attrs` via an `AugAssign`
    test.__doc__ += 'b'
    # +2: inferred: FunctionDef(allow_retrieving_instance_attrs_and_special_attrs_for_functions.A.test)
    # +1: inferred.getattr(__doc__): AssignAttr, Const('a')
    test
