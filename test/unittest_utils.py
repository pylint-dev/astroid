from logilab.common.testlib import TestCase, unittest_main

from logilab.astng import builder, nodes
from logilab.astng.node_classes import are_exclusive

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
        
    def test_if(self):
        astng = builder.string_build('''

if 1:
    a = 1
    a = 2
elif 2:
    a = 12
    a = 13
else:
    a = 3
    a = 4
        ''')
        a1 = astng.locals['a'][0]
        a2 = astng.locals['a'][1]
        a3 = astng.locals['a'][2]
        a4 = astng.locals['a'][3]
        a5 = astng.locals['a'][4]
        a6 = astng.locals['a'][5]
        self.assertEquals(are_exclusive(a1, a2), False)
        self.assertEquals(are_exclusive(a1, a3), True)
        self.assertEquals(are_exclusive(a1, a5), True)
        self.assertEquals(are_exclusive(a3, a5), True)
        self.assertEquals(are_exclusive(a3, a4), False)
        self.assertEquals(are_exclusive(a5, a6), False)
        
    def test_try_except(self):
        astng = builder.string_build('''
try:
    def exclusive_func2():
        "docstring"
except TypeError:
    def exclusive_func2():
        "docstring"
except:
    def exclusive_func2():
        "docstring"
else:
    def exclusive_func2():
        "this one redefine the one defined line 42"

        ''')
        f1 = astng.locals['exclusive_func2'][0]
        f2 = astng.locals['exclusive_func2'][1]
        f3 = astng.locals['exclusive_func2'][2]
        f4 = astng.locals['exclusive_func2'][3]
        self.assertEquals(are_exclusive(f1, f2), True)
        self.assertEquals(are_exclusive(f1, f3), True)
        self.assertEquals(are_exclusive(f1, f4), False)
        self.assertEquals(are_exclusive(f2, f4), True)
        self.assertEquals(are_exclusive(f3, f4), True)
        self.assertEquals(are_exclusive(f3, f2), True)
        
        self.assertEquals(are_exclusive(f2, f1), True)
        self.assertEquals(are_exclusive(f4, f1), False)
        self.assertEquals(are_exclusive(f4, f2), True)

if __name__ == '__main__':
    unittest_main()
   
