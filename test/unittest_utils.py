from logilab.common.testlib import TestCase, unittest_main

from logilab.astng import builder, nodes
from logilab.astng.utils import are_exclusive
builder = builder.ASTNGBuilder()

class AreExclusiveTC(TestCase):
    def test_not_exclusive(self):
        astng = builder.string_build("""
x = 10
for x in range(5):
    print x
   
if x > 0:
    print '#' * x        
        """, __name__, __file__)
        xass1 = astng.locals['x'][0]
        assert xass1.lineno == 2
        xnames = [n for n in astng.nodes_of_class(nodes.Name) if n.name == 'x']
        assert len(xnames) == 3
        assert xnames[1].lineno == 6
        self.assertEquals(are_exclusive(xass1, xnames[1]), False)
        self.assertEquals(are_exclusive(xass1, xnames[2]), False)
        
if __name__ == '__main__':
    unittest_main()
   
