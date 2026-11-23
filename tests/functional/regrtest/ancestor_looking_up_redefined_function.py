class Foo:
    def _format(self):
        pass

    def format(self):
        self.format = self._format
        self.format()
# +3: inferred: ClassDef(ancestor_looking_up_redefined_function.Foo)
# +2: inferred.ancestors().lookup('format')[1]: [FunctionDef(builtins.format)]
# +1: inferred.ancestors().lookup('format')[1][0]: FunctionDef(builtins.format)
Foo
