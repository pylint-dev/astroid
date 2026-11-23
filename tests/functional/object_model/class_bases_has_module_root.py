# Regression test for pylint-dev/pylint#11491.
#
# Inferring ``Class.__bases__`` must return a Tuple parented to the class so
# callers can safely use ``.root()`` (e.g. pylint's stdlib checker).
class C:
    pass
# +4: inferred: Tuple(ClassDef(builtins.object))
# +3: inferred.parent: ClassDef(class_bases_has_module_root.C)
# +2: inferred.parent.name: 'C'
# +1: inferred.root(): Module(class_bases_has_module_root)
C.__bases__
