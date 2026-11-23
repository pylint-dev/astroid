class A:
    @property
    def test(self):
        '''Docstring'''
        return 42

A.test  # inferred: Property(property_docstring.A.test)  # inferred.doc_node: 'Docstring'
