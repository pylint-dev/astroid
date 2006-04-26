# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.

# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""tests for the astng inference capabilities

Copyright (c) 2005-2006 LOGILAB S.A. (Paris, FRANCE).
http://www.logilab.fr/ -- mailto:contact@logilab.fr
"""

__revision__ = "$Id: unittest_inference.py,v 1.20 2006-04-19 15:17:41 syt Exp $"

from os.path import join, abspath

from logilab.astng import builder, nodes, inference, utils, YES, Instance
from logilab.common.testlib import TestCase, unittest_main

def get_name_node(start_from, name, index=0):
    return [n for n in start_from.nodes_of_class(nodes.Name) if n.name == name][index]

def get_node_of_class(start_from, klass):
    return start_from.nodes_of_class(klass).next()

builder = builder.ASTNGBuilder()

class InferenceUtilsTC(TestCase):

    def test_path_wrapper(self):
        infer_default = inference.path_wrapper(inference.infer_default)
        infer_end = inference.path_wrapper(inference.infer_end)
        self.failUnlessRaises(inference.InferenceError,
                              infer_default(1).next)
        self.failUnlessEqual(infer_end(1).next(), 1)
        
class InferenceTC(TestCase):

    DATA = '''
import exceptions

class C(object):
    "new style"
    attr = 4
    
    def meth1(self, arg1, optarg=0):
        var = object()
        print "yo", arg1, optarg
        self.iattr = "hop"
        return var
        
    def meth2(self):
        self.meth1(*self.meth3)
        
    def meth3(self, d=attr):
        b = self.attr
        c = self.iattr
        return b, c
    
ex = exceptions.Exception("msg")
v = C().meth1(1)
a, b, c = ex, 1, "bonjour"
[d, e, f] = [ex, 1.0, ("bonjour", v)]
g, h = f
i, (j, k) = u"glup", f

a, b= b, a # Gasp !
'''
        
    def setUp(self):
        self.astng = builder.string_build(self.DATA, __name__, __file__)

    def test_module_inference(self):
        infered = self.astng.infer()
        obj = infered.next()
        self.failUnlessEqual(obj.name, __name__)
        self.failUnlessEqual(obj.root().name, __name__)
        self.failUnlessRaises(StopIteration, infered.next)
        
    def test_class_inference(self):
        infered = self.astng['C'].infer()
        obj = infered.next()
        self.failUnlessEqual(obj.name, 'C')
        self.failUnlessEqual(obj.root().name, __name__)
        self.failUnlessRaises(StopIteration, infered.next)
        
    def test_function_inference(self):
        infered = self.astng['C']['meth1'].infer()
        obj = infered.next()
        self.failUnlessEqual(obj.name, 'meth1')
        self.failUnlessEqual(obj.root().name, __name__)
        self.failUnlessRaises(StopIteration, infered.next)

    def test_name_inference(self):
        infered = self.astng['C']['meth1']['var'].infer()
        var = infered.next()
        self.failUnlessEqual(var.name, 'object')
        self.failUnlessEqual(var.root().name, '__builtin__')
        self.failUnlessRaises(StopIteration, infered.next)
        
    def test_tupleassign_name_inference(self):
        infered = self.astng['a'].infer()
        exc = infered.next()
        self.failUnless(isinstance(exc, inference.Instance))
        self.failUnlessEqual(exc.name, 'Exception')
        self.failUnlessEqual(exc.root().name, 'exceptions')
        self.failUnlessRaises(StopIteration, infered.next)
        infered = self.astng['b'].infer()
        const = infered.next()
        self.failUnless(isinstance(const, nodes.Const))
        self.failUnlessEqual(const.value, 1)
        self.failUnlessRaises(StopIteration, infered.next)
        infered = self.astng['c'].infer()
        const = infered.next()
        self.failUnless(isinstance(const, nodes.Const))
        self.failUnlessEqual(const.value, "bonjour")
        self.failUnlessRaises(StopIteration, infered.next)
        
    def test_listassign_name_inference(self):
        infered = self.astng['d'].infer()
        exc = infered.next()
        self.failUnless(isinstance(exc, inference.Instance))
        self.failUnlessEqual(exc.name, 'Exception')
        self.failUnlessEqual(exc.root().name, 'exceptions')
        self.failUnlessRaises(StopIteration, infered.next)
        infered = self.astng['e'].infer()
        const = infered.next()
        self.failUnless(isinstance(const, nodes.Const))
        self.failUnlessEqual(const.value, 1.0)
        self.failUnlessRaises(StopIteration, infered.next)
        infered = self.astng['f'].infer()
        const = infered.next()
        self.failUnless(isinstance(const, nodes.Tuple))
        self.failUnlessRaises(StopIteration, infered.next)
        
    def test_advanced_tupleassign_name_inference1(self):
        infered = self.astng['g'].infer()
        const = infered.next()
        self.failUnless(isinstance(const, nodes.Const))
        self.failUnlessEqual(const.value, "bonjour")
        self.failUnlessRaises(StopIteration, infered.next)
        infered = self.astng['h'].infer()
        var = infered.next()
        self.failUnlessEqual(var.name, 'object')
        self.failUnlessEqual(var.root().name, '__builtin__')
        self.failUnlessRaises(StopIteration, infered.next)
        
    def test_advanced_tupleassign_name_inference2(self):
        infered = self.astng['i'].infer()
        const = infered.next()
        self.failUnless(isinstance(const, nodes.Const))
        self.failUnlessEqual(const.value, u"glup")
        self.failUnlessRaises(StopIteration, infered.next)
        infered = self.astng['j'].infer()
        const = infered.next()
        self.failUnless(isinstance(const, nodes.Const))
        self.failUnlessEqual(const.value, "bonjour")
        self.failUnlessRaises(StopIteration, infered.next)
        infered = self.astng['k'].infer()
        var = infered.next()
        self.failUnlessEqual(var.name, 'object')
        self.failUnlessEqual(var.root().name, '__builtin__')
        self.failUnlessRaises(StopIteration, infered.next)
        
    def test_swap_assign_inference(self):
        infered = self.astng.locals['a'][1].infer()
        const = infered.next()
        self.failUnless(isinstance(const, nodes.Const))
        self.failUnlessEqual(const.value, 1)
        self.failUnlessRaises(StopIteration, infered.next)
        infered = self.astng.locals['b'][1].infer()
        exc = infered.next()
        self.failUnless(isinstance(exc, inference.Instance))
        self.failUnlessEqual(exc.name, 'Exception')
        self.failUnlessEqual(exc.root().name, 'exceptions')
        self.failUnlessRaises(StopIteration, infered.next)
        
    def test_getattr_inference1(self):
        infered = self.astng['ex'].infer(path=[])
        exc = infered.next()
        self.failUnless(isinstance(exc, inference.Instance))
        self.failUnlessEqual(exc.name, 'Exception')
        self.failUnlessEqual(exc.root().name, 'exceptions')
        self.failUnlessRaises(StopIteration, infered.next)
        
    def test_getattr_inference2(self):
        infered = get_node_of_class(self.astng['C']['meth2'], nodes.Getattr).infer()
        meth1 = infered.next()
        self.failUnlessEqual(meth1.name, 'meth1')
        self.failUnlessEqual(meth1.root().name, __name__)
        self.failUnlessRaises(StopIteration, infered.next)
        
    def test_getattr_inference3(self):
        infered = self.astng['C']['meth3']['b'].infer()
        const = infered.next()
        self.failUnless(isinstance(const, nodes.Const))
        self.failUnlessEqual(const.value, 4)
        self.failUnlessRaises(StopIteration, infered.next)
        
    def test_getattr_inference4(self):
        infered = self.astng['C']['meth3']['c'].infer()
        const = infered.next()
        self.failUnless(isinstance(const, nodes.Const))
        self.failUnlessEqual(const.value, "hop")
        self.failUnlessRaises(StopIteration, infered.next)
        
    def test_callfunc_inference(self):
        infered = self.astng['v'].infer()
        meth1 = infered.next()
        self.failUnless(isinstance(meth1, inference.Instance))
        self.failUnlessEqual(meth1.name, 'object')
        self.failUnlessEqual(meth1.root().name, '__builtin__')
        self.failUnlessRaises(StopIteration, infered.next)

    def test_args_default_inference1(self):
        optarg = get_name_node(self.astng['C']['meth1'], 'optarg')
        infered = optarg.infer()
        obj1 = infered.next()
        self.failUnless(isinstance(obj1, nodes.Const))
        self.failUnlessEqual(obj1.value, 0)
        obj1 = infered.next()
        self.failUnless(obj1 is YES)
        self.failUnlessRaises(StopIteration, infered.next)

    def test_args_default_inference2(self):
        infered = self.astng['C']['meth3']['d'].infer(name='d')
        obj1 = infered.next()
        self.failUnless(isinstance(obj1, nodes.Const))
        self.failUnlessEqual(obj1.value, 4)
        obj1 = infered.next()
        self.failUnless(obj1 is YES)
        self.failUnlessRaises(StopIteration, infered.next)
        
    def test_inference_restrictions(self):
        infered = get_name_node(self.astng['C']['meth1'], 'arg1').infer()
        obj1 = infered.next()
        self.failUnless(obj1 is YES)
        self.failUnlessRaises(StopIteration, infered.next)

    def test_del(self):
        data = '''
del undefined_attr
        '''
        astng = builder.string_build(data, __name__, __file__)
        self.failUnlessRaises(inference.InferenceError,
                              astng.node.getChildNodes()[0].infer().next)
        
    def test_ancestors_inference(self):
        data = '''
class A:
    pass

class A(A):
    pass
        '''
        astng = builder.string_build(data, __name__, __file__)
        a1 = astng.locals['A'][0]
        a2 = astng.locals['A'][1]
        a2_ancestors = list(a2.ancestors())
        self.failUnlessEqual(len(a2_ancestors), 1)
        self.failUnless(a2_ancestors[0] is a1)

    def test_ancestors_inference2(self):
        data = '''
class A:
    pass

class B(A): pass

class A(B):
    pass
        '''
        astng = builder.string_build(data, __name__, __file__)
        a1 = astng.locals['A'][0]
        a2 = astng.locals['A'][1]
        a2_ancestors = list(a2.ancestors())
        self.failUnlessEqual(len(a2_ancestors), 2)
        self.failUnless(a2_ancestors[0] is astng.locals['B'][0])
        self.failUnless(a2_ancestors[1] is a1, a2_ancestors[1])


    def test_f_arg_f(self):
        data = '''
def f(f=1):
    return f

a = f()
        '''
        astng = builder.string_build(data, __name__, __file__)
        a = astng['a']
        a_infer = a.infer()
        self.failUnlessEqual(a_infer.next().value, 1)
        self.failUnlessEqual(a_infer.next(), YES)
        self.failUnlessRaises(StopIteration, a_infer.next)
        
    def test_exc_ancestors(self):
        data = '''
def f():
    raise NotImplementedError
        '''
        astng = builder.string_build(data, __name__, __file__)
        names = astng.nodes_of_class(nodes.Name)
        nie = names.next().infer().next()
        self.failUnless(isinstance(nie, nodes.Class))
        nie_ancestors = [c.name for c in nie.ancestors()]
        self.failUnlessEqual(nie_ancestors, ['RuntimeError', 'StandardError', 'Exception'])

    def test_except_inference(self):
        data = '''
try:
    print hop
except NameError, ex:
    ex1 = ex
except Exception, ex:
    ex2 = ex
    raise
        '''
        astng = builder.string_build(data, __name__, __file__)
        ex1 = astng['ex1']
        ex1_infer = ex1.infer()
        infered = list(ex1.infer())
        #print 'EX1:', ex1
        #print 'INFEREND', infered
        ex1 = ex1_infer.next()
        self.failUnless(isinstance(ex1, inference.Instance))
        self.failUnlessEqual(ex1.name, 'NameError')
        self.failUnlessRaises(StopIteration, ex1_infer.next)
        ex2 = astng['ex2']
        ex2_infer = ex2.infer()
        ex2 = ex2_infer.next()
        self.failUnless(isinstance(ex2, inference.Instance))
        self.failUnlessEqual(ex2.name, 'Exception')
        self.failUnlessRaises(StopIteration, ex2_infer.next)

    def test_del(self):
        data = '''
a = 1
b = a
del a
c = a
a = 2
d = a
        '''
        astng = builder.string_build(data, __name__, __file__)
        n = astng['b']
        n_infer = n.infer()
        infered = n_infer.next()
        self.failUnless(isinstance(infered, nodes.Const))
        self.failUnlessEqual(infered.value, 1)
        self.failUnlessRaises(StopIteration, n_infer.next)
        n = astng['c']
        n_infer = n.infer()
        self.failUnlessRaises(inference.InferenceError, n_infer.next)
        n = astng['d']
        n_infer = n.infer()
        infered = n_infer.next()
        self.failUnless(isinstance(infered, nodes.Const))
        self.failUnlessEqual(infered.value, 2)
        self.failUnlessRaises(StopIteration, n_infer.next)

    def test_builtin_types(self):
        data = '''
l = [1]
t = (2,)
d = {}
s = ''
u = u''
        '''
        astng = builder.string_build(data, __name__, __file__)
        n = astng['l']
        infered = n.infer().next()
        self.failUnless(isinstance(infered, nodes.List))
        self.failUnless(isinstance(infered, inference.Instance))
        self.failUnlessEqual(infered.getitem(0).value, 1)
        self.failUnless(isinstance(infered._proxied, nodes.Class))
        self.failUnlessEqual(infered._proxied.name, 'list')
        self.failUnless('append' in infered._proxied.locals)
        n = astng['t']
        infered = n.infer().next()
        self.failUnless(isinstance(infered, nodes.Tuple))
        self.failUnless(isinstance(infered, inference.Instance))
        self.failUnlessEqual(infered.getitem(0).value, 2)
        self.failUnless(isinstance(infered._proxied, nodes.Class))
        self.failUnlessEqual(infered._proxied.name, 'tuple')
        n = astng['d']
        infered = n.infer().next()
        self.failUnless(isinstance(infered, nodes.Dict))
        self.failUnless(isinstance(infered, inference.Instance))
        self.failUnless(isinstance(infered._proxied, nodes.Class))
        self.failUnlessEqual(infered._proxied.name, 'dict')
        self.failUnless('get' in infered._proxied.locals)
        n = astng['s']
        infered = n.infer().next()
        self.failUnless(isinstance(infered, nodes.Const))
        self.failUnless(isinstance(infered, inference.Instance))
        self.failUnlessEqual(infered.name, 'str')
        self.failUnless('lower' in infered._proxied.locals)
        n = astng['u']
        infered = n.infer().next()
        self.failUnless(isinstance(infered, nodes.Const))
        self.failUnless(isinstance(infered, inference.Instance))
        self.failUnlessEqual(infered.name, 'unicode')
        self.failUnless('lower' in infered._proxied.locals)
        
    def test_descriptor_are_callable(self):
        data = '''
class A:
    statm = staticmethod(open)
    clsm = classmethod('whatever')
        '''
        astng = builder.string_build(data, __name__, __file__)
        statm = astng['A'].igetattr('statm').next()
        self.failUnless(statm.callable())
        clsm = astng['A'].igetattr('clsm').next()
        self.failUnless(clsm.callable())

    def test_bt_ancestor_crash(self):
        data = '''
class Warning(Warning):
    pass
        '''
        astng = builder.string_build(data, __name__, __file__)
        w = astng['Warning']
        ancestors = w.ancestors()
        ancestor = ancestors.next()
        self.failUnlessEqual(ancestor.name, 'Warning')
        self.failUnlessEqual(ancestor.root().name, 'exceptions')
        ancestor = ancestors.next()
        self.failUnlessEqual(ancestor.name, 'Exception')
        self.failUnlessEqual(ancestor.root().name, 'exceptions')
        self.failUnlessRaises(StopIteration, ancestors.next)
        
    def test_qqch(self):
        data = '''
from logilab.common.modutils import load_module_from_name
xxx = load_module_from_name('__pkginfo__')
        '''
        astng = builder.string_build(data, __name__, __file__)
        xxx = astng['xxx']
        infered = list(xxx.infer())
        self.failUnlessEqual([n.__class__ for n in infered],
                             [nodes.Const, YES.__class__, YES.__class__])

    def test_method_argument(self):
        data = '''
class ErudiEntitySchema:
    """a entity has a type, a set of subject and or object relations"""
    def __init__(self, e_type, **kwargs):
        kwargs['e_type'] = e_type.capitalize().encode()

    def meth(self, e_type, *args, **kwargs):
        kwargs['e_type'] = e_type.capitalize().encode()
        print args
        '''
        astng = builder.string_build(data, __name__, __file__)
        arg = get_name_node(astng['ErudiEntitySchema']['__init__'], 'e_type')
        self.failUnlessEqual([n.__class__ for n in arg.infer()],
                             [YES.__class__])
        arg = get_name_node(astng['ErudiEntitySchema']['__init__'], 'kwargs')
        self.failUnlessEqual([n.__class__ for n in arg.infer()],
                             [nodes.Dict])
        arg = get_name_node(astng['ErudiEntitySchema']['meth'], 'e_type')
        self.failUnlessEqual([n.__class__ for n in arg.infer()],
                             [YES.__class__])
        arg = get_name_node(astng['ErudiEntitySchema']['meth'], 'args')
        self.failUnlessEqual([n.__class__ for n in arg.infer()],
                             [nodes.Tuple])
        arg = get_name_node(astng['ErudiEntitySchema']['meth'], 'kwargs')
        self.failUnlessEqual([n.__class__ for n in arg.infer()],
                             [nodes.Dict])


    def test_tuple_then_list(self):
        data = '''
def test_view(rql, vid, tags=()):
    tags = list(tags)
    tags.append(vid)
        '''
        astng = builder.string_build(data, __name__, __file__)
        name = get_name_node(astng['test_view'], 'tags', -1)
        it = name.infer()
        tags = it.next()
        self.failUnlessEqual(tags.__class__, Instance)
        self.failUnlessEqual(tags._proxied.name, 'list')
        self.failUnlessRaises(StopIteration, it.next)



    def test_mulassign_inference(self):
        data = '''
        
def first_word(line):
    """Return the first word of a line"""

    return line.split()[0]

def last_word(line):
    """Return last word of a line"""

    return line.split()[-1]

def process_line(word_pos):
    """Silly function: returns (ok, callable) based on argument.

       For test purpose only.
    """

    if word_pos > 0:
        return (True, first_word)
    elif word_pos < 0:
        return  (True, last_word)
    else:
        return (False, None)

if __name__ == '__main__':

    line_number = 0
    for a_line in file('test_callable.py'):
        tupletest  = process_line(line_number)
        (ok, fct)  = process_line(line_number)
        if ok:
            fct(a_line)
'''
        astng = builder.string_build(data, __name__, __file__)
        self.failUnlessEqual(len(list(astng['process_line'].infer_call_result(None))),
                             3)
        self.failUnlessEqual(len(list(astng['tupletest'].infer())),
                             3)
        self.failUnlessEqual([str(infered)
                              for infered in astng['fct'].infer()],
                              ['Function(first_word)', 'Function(last_word)', 'Const(None)'])

    def test_float_complex_ambiguity(self):
        data = '''
def no_conjugate_member(magic_flag):
    """should not raise E1101 on something.conjugate"""
    if magic_flag:
        something = 1.0
    else:
        something = 1.0j
    if isinstance(something, float):
        return something
    return something.conjugate()
        '''
        astng = builder.string_build(data, __name__, __file__)
        self.failUnlessEqual([i.value for i in astng['no_conjugate_member'].ilookup('something')],
                             [1.0, 1.0j])
        
if __name__ == '__main__':
    from logilab.common.testlib import unittest_main
    unittest_main()
