# copyright 2003-2013 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
#
# This file is part of astroid.
#
# astroid is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# astroid is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with astroid. If not, see <http://www.gnu.org/licenses/>.
"""tests for the astroid inference capabilities
"""
import sys
from functools import partial
import unittest

import six

from astroid import InferenceError, builder, nodes
from astroid.inference import infer_end as inference_infer_end
from astroid.bases import YES, Instance, BoundMethod, UnboundMethod,\
                                path_wrapper, BUILTINS
from astroid import test_utils
from astroid.tests import resources


def get_node_of_class(start_from, klass):
    return next(start_from.nodes_of_class(klass))

builder = builder.AstroidBuilder()

if sys.version_info < (3, 0):
    EXC_MODULE = 'exceptions'
else:
    EXC_MODULE = BUILTINS


class InferenceUtilsTest(unittest.TestCase):

    def test_path_wrapper(self):
        def infer_default(self, *args):
            raise InferenceError
        infer_default = path_wrapper(infer_default)
        infer_end = path_wrapper(inference_infer_end)
        with self.assertRaises(InferenceError):
            next(infer_default(1))
        self.assertEqual(next(infer_end(1)), 1)


def _assertInferElts(node_type, self, node, elts):
     infered = next(node.infer())
     self.assertIsInstance(infered, node_type)
     self.assertEqual(sorted(elt.value for elt in infered.elts),
                      elts)

def partialmethod(func, arg):
    """similar to functools.partial but return a lambda instead of a class so returned value may be
    turned into a method.
    """
    return lambda *args, **kwargs: func(arg, *args, **kwargs)

class InferenceTest(resources.SysPathSetup, unittest.TestCase):

    # additional assertInfer* method for builtin types

    def assertInferConst(self, node, expected):
        infered = next(node.infer())
        self.assertIsInstance(infered, nodes.Const)
        self.assertEqual(infered.value, expected)

    def assertInferDict(self, node, expected):
        infered = next(node.infer())
        self.assertIsInstance(infered, nodes.Dict)

        elts = set([(key.value, value.value)
                    for (key, value) in infered.items])
        self.assertEqual(sorted(elts), sorted(expected.items()))

    assertInferTuple = partialmethod(_assertInferElts, nodes.Tuple)
    assertInferList = partialmethod(_assertInferElts, nodes.List)
    assertInferSet = partialmethod(_assertInferElts, nodes.Set)

    CODE = '''
        class C(object):
            "new style"
            attr = 4

            def meth1(self, arg1, optarg=0):
                var = object()
                print ("yo", arg1, optarg)
                self.iattr = "hop"
                return var

            def meth2(self):
                self.meth1(*self.meth3)

            def meth3(self, d=attr):
                b = self.attr
                c = self.iattr
                return b, c

        ex = Exception("msg")
        v = C().meth1(1)
        m_unbound = C.meth1
        m_bound = C().meth1
        a, b, c = ex, 1, "bonjour"
        [d, e, f] = [ex, 1.0, ("bonjour", v)]
        g, h = f
        i, (j, k) = "glup", f

        a, b= b, a # Gasp !
        '''

    ast = test_utils.build_module(CODE, __name__)

    def test_module_inference(self):
        infered = self.ast.infer()
        obj = next(infered)
        self.assertEqual(obj.name, __name__)
        self.assertEqual(obj.root().name, __name__)
        self.assertRaises(StopIteration, partial(next, infered))

    def test_class_inference(self):
        infered = self.ast['C'].infer()
        obj = next(infered)
        self.assertEqual(obj.name, 'C')
        self.assertEqual(obj.root().name, __name__)
        self.assertRaises(StopIteration, partial(next, infered))

    def test_function_inference(self):
        infered = self.ast['C']['meth1'].infer()
        obj = next(infered)
        self.assertEqual(obj.name, 'meth1')
        self.assertEqual(obj.root().name, __name__)
        self.assertRaises(StopIteration, partial(next, infered))

    def test_builtin_name_inference(self):
        infered = self.ast['C']['meth1']['var'].infer()
        var = next(infered)
        self.assertEqual(var.name, 'object')
        self.assertEqual(var.root().name, BUILTINS)
        self.assertRaises(StopIteration, partial(next, infered))

    def test_tupleassign_name_inference(self):
        infered = self.ast['a'].infer()
        exc = next(infered)
        self.assertIsInstance(exc, Instance)
        self.assertEqual(exc.name, 'Exception')
        self.assertEqual(exc.root().name, EXC_MODULE)
        self.assertRaises(StopIteration, partial(next, infered))
        infered = self.ast['b'].infer()
        const = next(infered)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, 1)
        self.assertRaises(StopIteration, partial(next, infered))
        infered = self.ast['c'].infer()
        const = next(infered)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, "bonjour")
        self.assertRaises(StopIteration, partial(next, infered))

    def test_listassign_name_inference(self):
        infered = self.ast['d'].infer()
        exc = next(infered)
        self.assertIsInstance(exc, Instance)
        self.assertEqual(exc.name, 'Exception')
        self.assertEqual(exc.root().name, EXC_MODULE)
        self.assertRaises(StopIteration, partial(next, infered))
        infered = self.ast['e'].infer()
        const = next(infered)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, 1.0)
        self.assertRaises(StopIteration, partial(next, infered))
        infered = self.ast['f'].infer()
        const = next(infered)
        self.assertIsInstance(const, nodes.Tuple)
        self.assertRaises(StopIteration, partial(next, infered))

    def test_advanced_tupleassign_name_inference1(self):
        infered = self.ast['g'].infer()
        const = next(infered)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, "bonjour")
        self.assertRaises(StopIteration, partial(next, infered))
        infered = self.ast['h'].infer()
        var = next(infered)
        self.assertEqual(var.name, 'object')
        self.assertEqual(var.root().name, BUILTINS)
        self.assertRaises(StopIteration, partial(next, infered))

    def test_advanced_tupleassign_name_inference2(self):
        infered = self.ast['i'].infer()
        const = next(infered)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, u"glup")
        self.assertRaises(StopIteration, partial(next, infered))
        infered = self.ast['j'].infer()
        const = next(infered)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, "bonjour")
        self.assertRaises(StopIteration, partial(next, infered))
        infered = self.ast['k'].infer()
        var = next(infered)
        self.assertEqual(var.name, 'object')
        self.assertEqual(var.root().name, BUILTINS)
        self.assertRaises(StopIteration, partial(next, infered))

    def test_swap_assign_inference(self):
        infered = self.ast.locals['a'][1].infer()
        const = next(infered)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, 1)
        self.assertRaises(StopIteration, partial(next, infered))
        infered = self.ast.locals['b'][1].infer()
        exc = next(infered)
        self.assertIsInstance(exc, Instance)
        self.assertEqual(exc.name, 'Exception')
        self.assertEqual(exc.root().name, EXC_MODULE)
        self.assertRaises(StopIteration, partial(next, infered))

    def test_getattr_inference1(self):
        infered = self.ast['ex'].infer()
        exc = next(infered)
        self.assertIsInstance(exc, Instance)
        self.assertEqual(exc.name, 'Exception')
        self.assertEqual(exc.root().name, EXC_MODULE)
        self.assertRaises(StopIteration, partial(next, infered))

    def test_getattr_inference2(self):
        infered = get_node_of_class(self.ast['C']['meth2'], nodes.Getattr).infer()
        meth1 = next(infered)
        self.assertEqual(meth1.name, 'meth1')
        self.assertEqual(meth1.root().name, __name__)
        self.assertRaises(StopIteration, partial(next, infered))

    def test_getattr_inference3(self):
        infered = self.ast['C']['meth3']['b'].infer()
        const = next(infered)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, 4)
        self.assertRaises(StopIteration, partial(next, infered))

    def test_getattr_inference4(self):
        infered = self.ast['C']['meth3']['c'].infer()
        const = next(infered)
        self.assertIsInstance(const, nodes.Const)
        self.assertEqual(const.value, "hop")
        self.assertRaises(StopIteration, partial(next, infered))

    def test_callfunc_inference(self):
        infered = self.ast['v'].infer()
        meth1 = next(infered)
        self.assertIsInstance(meth1, Instance)
        self.assertEqual(meth1.name, 'object')
        self.assertEqual(meth1.root().name, BUILTINS)
        self.assertRaises(StopIteration, partial(next, infered))

    def test_unbound_method_inference(self):
        infered = self.ast['m_unbound'].infer()
        meth1 = next(infered)
        self.assertIsInstance(meth1, UnboundMethod)
        self.assertEqual(meth1.name, 'meth1')
        self.assertEqual(meth1.parent.frame().name, 'C')
        self.assertRaises(StopIteration, partial(next, infered))

    def test_bound_method_inference(self):
        infered = self.ast['m_bound'].infer()
        meth1 = next(infered)
        self.assertIsInstance(meth1, BoundMethod)
        self.assertEqual(meth1.name, 'meth1')
        self.assertEqual(meth1.parent.frame().name, 'C')
        self.assertRaises(StopIteration, partial(next, infered))

    def test_args_default_inference1(self):
        optarg = test_utils.get_name_node(self.ast['C']['meth1'], 'optarg')
        infered = optarg.infer()
        obj1 = next(infered)
        self.assertIsInstance(obj1, nodes.Const)
        self.assertEqual(obj1.value, 0)
        obj1 = next(infered)
        self.assertIs(obj1, YES, obj1)
        self.assertRaises(StopIteration, partial(next, infered))

    def test_args_default_inference2(self):
        infered = self.ast['C']['meth3'].ilookup('d')
        obj1 = next(infered)
        self.assertIsInstance(obj1, nodes.Const)
        self.assertEqual(obj1.value, 4)
        obj1 = next(infered)
        self.assertIs(obj1, YES, obj1)
        self.assertRaises(StopIteration, partial(next, infered))

    def test_inference_restrictions(self):
        infered = test_utils.get_name_node(self.ast['C']['meth1'], 'arg1').infer()
        obj1 = next(infered)
        self.assertIs(obj1, YES, obj1)
        self.assertRaises(StopIteration, partial(next, infered))

    def test_ancestors_inference(self):
        code = '''
            class A(object):  #@
                pass

            class A(A):  #@
                pass
        '''
        a1, a2 = test_utils.extract_node(code, __name__)
        a2_ancestors = list(a2.ancestors())
        self.assertEqual(len(a2_ancestors), 2)
        self.assertIs(a2_ancestors[0], a1)

    def test_ancestors_inference2(self):
        code = '''
            class A(object):  #@
                pass

            class B(A):  #@
                pass

            class A(B):  #@
                pass
        '''
        a1, b, a2 = test_utils.extract_node(code, __name__)
        a2_ancestors = list(a2.ancestors())
        self.assertEqual(len(a2_ancestors), 3)
        self.assertIs(a2_ancestors[0], b)
        self.assertIs(a2_ancestors[1], a1)


    def test_f_arg_f(self):
        code = '''
            def f(f=1):
                return f

            a = f()
        '''
        ast = test_utils.build_module(code, __name__)
        a = ast['a']
        a_infered = a.infered()
        self.assertEqual(a_infered[0].value, 1)
        self.assertEqual(len(a_infered), 1)

    def test_exc_ancestors(self):
        code = '''
        def f():
            raise __(NotImplementedError)
        '''
        error = test_utils.extract_node(code, __name__)
        nie = error.infered()[0]
        self.assertIsInstance(nie, nodes.Class)
        nie_ancestors = [c.name for c in nie.ancestors()]
        if sys.version_info < (3, 0):
            self.assertEqual(nie_ancestors, ['RuntimeError', 'StandardError', 'Exception', 'BaseException', 'object'])
        else:
            self.assertEqual(nie_ancestors, ['RuntimeError', 'Exception', 'BaseException', 'object'])

    def test_except_inference(self):
        code = '''
            try:
                print (hop)
            except NameError as ex:
                ex1 = ex
            except Exception as ex:
                ex2 = ex
                raise
        '''
        ast = test_utils.build_module(code, __name__)
        ex1 = ast['ex1']
        ex1_infer = ex1.infer()
        ex1 = next(ex1_infer)
        self.assertIsInstance(ex1, Instance)
        self.assertEqual(ex1.name, 'NameError')
        self.assertRaises(StopIteration, partial(next, ex1_infer))
        ex2 = ast['ex2']
        ex2_infer = ex2.infer()
        ex2 = next(ex2_infer)
        self.assertIsInstance(ex2, Instance)
        self.assertEqual(ex2.name, 'Exception')
        self.assertRaises(StopIteration, partial(next, ex2_infer))

    def test_del1(self):
        code = '''
            del undefined_attr
        '''
        delete = test_utils.extract_node(code, __name__)
        self.assertRaises(InferenceError, delete.infer)

    def test_del2(self):
        code = '''
            a = 1
            b = a
            del a
            c = a
            a = 2
            d = a
        '''
        ast = test_utils.build_module(code, __name__)
        n = ast['b']
        n_infer = n.infer()
        infered = next(n_infer)
        self.assertIsInstance(infered, nodes.Const)
        self.assertEqual(infered.value, 1)
        self.assertRaises(StopIteration, partial(next, n_infer))
        n = ast['c']
        n_infer = n.infer()
        self.assertRaises(InferenceError, partial(next, n_infer))
        n = ast['d']
        n_infer = n.infer()
        infered = next(n_infer)
        self.assertIsInstance(infered, nodes.Const)
        self.assertEqual(infered.value, 2)
        self.assertRaises(StopIteration, partial(next, n_infer))

    def test_builtin_types(self):
        code = '''
            l = [1]
            t = (2,)
            d = {}
            s = ''
            s2 = '_'
        '''
        ast = test_utils.build_module(code, __name__)
        n = ast['l']
        infered = next(n.infer())
        self.assertIsInstance(infered, nodes.List)
        self.assertIsInstance(infered, Instance)
        self.assertEqual(infered.getitem(0).value, 1)
        self.assertIsInstance(infered._proxied, nodes.Class)
        self.assertEqual(infered._proxied.name, 'list')
        self.assertIn('append', infered._proxied.locals)
        n = ast['t']
        infered = next(n.infer())
        self.assertIsInstance(infered, nodes.Tuple)
        self.assertIsInstance(infered, Instance)
        self.assertEqual(infered.getitem(0).value, 2)
        self.assertIsInstance(infered._proxied, nodes.Class)
        self.assertEqual(infered._proxied.name, 'tuple')
        n = ast['d']
        infered = next(n.infer())
        self.assertIsInstance(infered, nodes.Dict)
        self.assertIsInstance(infered, Instance)
        self.assertIsInstance(infered._proxied, nodes.Class)
        self.assertEqual(infered._proxied.name, 'dict')
        self.assertIn('get', infered._proxied.locals)
        n = ast['s']
        infered = next(n.infer())
        self.assertIsInstance(infered, nodes.Const)
        self.assertIsInstance(infered, Instance)
        self.assertEqual(infered.name, 'str')
        self.assertIn('lower', infered._proxied.locals)
        n = ast['s2']
        infered = next(n.infer())
        self.assertEqual(infered.getitem(0).value, '_')

    def test_builtin_types(self):
        code = 's = {1}'
        ast = test_utils.build_module(code, __name__)
        n = ast['s']
        infered = next(n.infer())
        self.assertIsInstance(infered, nodes.Set)
        self.assertIsInstance(infered, Instance)
        self.assertEqual(infered.name, 'set')
        self.assertIn('remove', infered._proxied.locals)

    @test_utils.require_version(maxver='3.0')
    def test_unicode_type(self):
        code = '''u = u""'''
        ast = test_utils.build_module(code, __name__)
        n = ast['u']
        infered = next(n.infer())
        self.assertIsInstance(infered, nodes.Const)
        self.assertIsInstance(infered, Instance)
        self.assertEqual(infered.name, 'unicode')
        self.assertIn('lower', infered._proxied.locals)

    def test_descriptor_are_callable(self):
        code = '''
            class A:
                statm = staticmethod(open)
                clsm = classmethod('whatever')
        '''
        ast = test_utils.build_module(code, __name__)
        statm = next(ast['A'].igetattr('statm'))
        self.assertTrue(statm.callable())
        clsm = next(ast['A'].igetattr('clsm'))
        self.assertTrue(clsm.callable())

    def test_bt_ancestor_crash(self):
        code = '''
            class Warning(Warning):
                pass
        '''
        ast = test_utils.build_module(code, __name__)
        w = ast['Warning']
        ancestors = w.ancestors()
        ancestor = next(ancestors)
        self.assertEqual(ancestor.name, 'Warning')
        self.assertEqual(ancestor.root().name, EXC_MODULE)
        ancestor = next(ancestors)
        self.assertEqual(ancestor.name, 'Exception')
        self.assertEqual(ancestor.root().name, EXC_MODULE)
        ancestor = next(ancestors)
        self.assertEqual(ancestor.name, 'BaseException')
        self.assertEqual(ancestor.root().name, EXC_MODULE)
        ancestor = next(ancestors)
        self.assertEqual(ancestor.name, 'object')
        self.assertEqual(ancestor.root().name, BUILTINS)
        self.assertRaises(StopIteration, partial(next, ancestors))

    def test_qqch(self):
        code = '''
            from astroid.modutils import load_module_from_name
            xxx = load_module_from_name('__pkginfo__')
        '''
        ast = test_utils.build_module(code, __name__)
        xxx = ast['xxx']
        self.assertSetEqual({n.__class__ for n in xxx.infered()},
                            {nodes.Const, YES.__class__})

    def test_method_argument(self):
        code = '''
            class ErudiEntitySchema:
                """a entity has a type, a set of subject and or object relations"""
                def __init__(self, e_type, **kwargs):
                    kwargs['e_type'] = e_type.capitalize().encode()

                def meth(self, e_type, *args, **kwargs):
                    kwargs['e_type'] = e_type.capitalize().encode()
                    print(args)
            '''
        ast = test_utils.build_module(code, __name__)
        arg = test_utils.get_name_node(ast['ErudiEntitySchema']['__init__'], 'e_type')
        self.assertEqual([n.__class__ for n in arg.infer()],
                         [YES.__class__])
        arg = test_utils.get_name_node(ast['ErudiEntitySchema']['__init__'], 'kwargs')
        self.assertEqual([n.__class__ for n in arg.infer()],
                         [nodes.Dict])
        arg = test_utils.get_name_node(ast['ErudiEntitySchema']['meth'], 'e_type')
        self.assertEqual([n.__class__ for n in arg.infer()],
                         [YES.__class__])
        arg = test_utils.get_name_node(ast['ErudiEntitySchema']['meth'], 'args')
        self.assertEqual([n.__class__ for n in arg.infer()],
                         [nodes.Tuple])
        arg = test_utils.get_name_node(ast['ErudiEntitySchema']['meth'], 'kwargs')
        self.assertEqual([n.__class__ for n in arg.infer()],
                         [nodes.Dict])

    def test_tuple_then_list(self):
        code = '''
            def test_view(rql, vid, tags=()):
                tags = list(tags)
                __(tags).append(vid)
        '''
        name = test_utils.extract_node(code, __name__)
        it = name.infer()
        tags = next(it)
        self.assertIsInstance(tags, nodes.List)
        self.assertEqual(tags.elts, [])
        with self.assertRaises(StopIteration):
            next(it)

    def test_mulassign_inference(self):
        code = '''
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
        ast = test_utils.build_module(code, __name__)
        self.assertEqual(len(list(ast['process_line'].infer_call_result(
                                                                None))), 3)
        self.assertEqual(len(list(ast['tupletest'].infer())), 3)
        values = ['Function(first_word)', 'Function(last_word)', 'Const(NoneType)']
        self.assertEqual([str(infered)
                          for infered in ast['fct'].infer()], values)

    def test_float_complex_ambiguity(self):
        code = '''
            def no_conjugate_member(magic_flag):  #@
                """should not raise E1101 on something.conjugate"""
                if magic_flag:
                    something = 1.0
                else:
                    something = 1.0j
                if isinstance(something, float):
                    return something
                return __(something).conjugate()
        '''
        func, retval = test_utils.extract_node(code, __name__)
        self.assertEqual(
            [i.value for i in func.ilookup('something')],
            [1.0, 1.0j])
        self.assertEqual(
            [i.value for i in retval.infer()],
            [1.0, 1.0j])

    def test_lookup_cond_branches(self):
        code = '''
            def no_conjugate_member(magic_flag):
                """should not raise E1101 on something.conjugate"""
                something = 1.0
                if magic_flag:
                    something = 1.0j
                return something.conjugate()
        '''
        ast = test_utils.build_module(code, __name__)
        self.assertEqual([i.value for i in
                test_utils.get_name_node(ast, 'something', -1).infer()], [1.0, 1.0j])


    def test_simple_subscript(self):
        code = '''
            a = [1, 2, 3][0]
            b = (1, 2, 3)[1]
            c = (1, 2, 3)[-1]
            d = a + b + c
            print (d)
            e = {'key': 'value'}
            f = e['key']
            print (f)
        '''
        ast = test_utils.build_module(code, __name__)
        self.assertEqual([i.value for i in
                                test_utils.get_name_node(ast, 'a', -1).infer()], [1])
        self.assertEqual([i.value for i in
                                test_utils.get_name_node(ast, 'b', -1).infer()], [2])
        self.assertEqual([i.value for i in
                                test_utils.get_name_node(ast, 'c', -1).infer()], [3])
        self.assertEqual([i.value for i in
                                test_utils.get_name_node(ast, 'd', -1).infer()], [6])
        self.assertEqual([i.value for i in
                          test_utils.get_name_node(ast, 'f', -1).infer()], ['value'])

    #def test_simple_tuple(self):
        #"""test case for a simple tuple value"""
        ## XXX tuple inference is not implemented ...
        #code = """
#a = (1,)
#b = (22,)
#some = a + b
#"""
        #ast = builder.string_build(code, __name__, __file__)
        #self.assertEqual(ast['some'].infer.next().as_string(), "(1, 22)")

    def test_simple_for(self):
        code = '''
            for a in [1, 2, 3]:
                print (a)
            for b,c in [(1,2), (3,4)]:
                print (b)
                print (c)

            print ([(d,e) for e,d in ([1,2], [3,4])])
        '''
        ast = test_utils.build_module(code, __name__)
        self.assertEqual([i.value for i in
                            test_utils.get_name_node(ast, 'a', -1).infer()], [1, 2, 3])
        self.assertEqual([i.value for i in
                            test_utils.get_name_node(ast, 'b', -1).infer()], [1, 3])
        self.assertEqual([i.value for i in
                            test_utils.get_name_node(ast, 'c', -1).infer()], [2, 4])
        self.assertEqual([i.value for i in
                            test_utils.get_name_node(ast, 'd', -1).infer()], [2, 4])
        self.assertEqual([i.value for i in
                            test_utils.get_name_node(ast, 'e', -1).infer()], [1, 3])


    def test_simple_for_genexpr(self):
        code = '''
            print ((d,e) for e,d in ([1,2], [3,4]))
        '''
        ast = test_utils.build_module(code, __name__)
        self.assertEqual([i.value for i in
                            test_utils.get_name_node(ast, 'd', -1).infer()], [2, 4])
        self.assertEqual([i.value for i in
                            test_utils.get_name_node(ast, 'e', -1).infer()], [1, 3])


    def test_builtin_help(self):
        code = '''
            help()
        '''
        # XXX failing since __builtin__.help assignment has
        #     been moved into a function...
        node = test_utils.extract_node(code, __name__)
        infered = list(node.func.infer())
        self.assertEqual(len(infered), 1, infered)
        self.assertIsInstance(infered[0], Instance)
        self.assertEqual(infered[0].name, "_Helper")

    def test_builtin_open(self):
        code = '''
            open("toto.txt")
        '''
        node = test_utils.extract_node(code, __name__).func
        infered = list(node.infer())
        self.assertEqual(len(infered), 1)
        if hasattr(sys, 'pypy_version_info'):
            self.assertIsInstance(infered[0], nodes.Class)
            self.assertEqual(infered[0].name, 'file')
        else:
            self.assertIsInstance(infered[0], nodes.Function)
            self.assertEqual(infered[0].name, 'open')

    def test_callfunc_context_func(self):
        code = '''
            def mirror(arg=None):
                return arg

            un = mirror(1)
        '''
        ast = test_utils.build_module(code, __name__)
        infered = list(ast.igetattr('un'))
        self.assertEqual(len(infered), 1)
        self.assertIsInstance(infered[0], nodes.Const)
        self.assertEqual(infered[0].value, 1)

    def test_callfunc_context_lambda(self):
        code = '''
            mirror = lambda x=None: x

            un = mirror(1)
        '''
        ast = test_utils.build_module(code, __name__)
        infered = list(ast.igetattr('mirror'))
        self.assertEqual(len(infered), 1)
        self.assertIsInstance(infered[0], nodes.Lambda)
        infered = list(ast.igetattr('un'))
        self.assertEqual(len(infered), 1)
        self.assertIsInstance(infered[0], nodes.Const)
        self.assertEqual(infered[0].value, 1)

    def test_factory_method(self):
        code = '''
            class Super(object):
                  @classmethod
                  def instance(cls):
                          return cls()

            class Sub(Super):
                  def method(self):
                          print ('method called')

            sub = Sub.instance()
        '''
        ast = test_utils.build_module(code, __name__)
        infered = list(ast.igetattr('sub'))
        self.assertEqual(len(infered), 1)
        self.assertIsInstance(infered[0], Instance)
        self.assertEqual(infered[0]._proxied.name, 'Sub')


    def test_import_as(self):
        code = '''
            import os.path as osp
            print (osp.dirname(__file__))

            from os.path import exists as e
            assert e(__file__)

            from new import code as make_code
            print (make_code)
        '''
        ast = test_utils.build_module(code, __name__)
        infered = list(ast.igetattr('osp'))
        self.assertEqual(len(infered), 1)
        self.assertIsInstance(infered[0], nodes.Module)
        self.assertEqual(infered[0].name, 'os.path')
        infered = list(ast.igetattr('e'))
        self.assertEqual(len(infered), 1)
        self.assertIsInstance(infered[0], nodes.Function)
        self.assertEqual(infered[0].name, 'exists')
        if sys.version_info >= (3, 0):
            self.skipTest('<new> module has been removed')
        infered = list(ast.igetattr('make_code'))
        self.assertEqual(len(infered), 1)
        self.assertIsInstance(infered[0], Instance)
        self.assertEqual(str(infered[0]),
                             'Instance of %s.type' % BUILTINS)

    def _test_const_infered(self, node, value):
        infered = list(node.infer())
        self.assertEqual(len(infered), 1)
        self.assertIsInstance(infered[0], nodes.Const)
        self.assertEqual(infered[0].value, value)

    def test_unary_not(self):
        for code in ('a = not (1,); b = not ()',
                     'a = not {1:2}; b = not {}'):
            ast = builder.string_build(code, __name__, __file__)
            self._test_const_infered(ast['a'], False)
            self._test_const_infered(ast['b'], True)

    def test_binary_op_int_add(self):
        ast = builder.string_build('a = 1 + 2', __name__, __file__)
        self._test_const_infered(ast['a'], 3)

    def test_binary_op_int_sub(self):
        ast = builder.string_build('a = 1 - 2', __name__, __file__)
        self._test_const_infered(ast['a'], -1)

    def test_binary_op_float_div(self):
        ast = builder.string_build('a = 1 / 2.', __name__, __file__)
        self._test_const_infered(ast['a'], 1 / 2.)

    def test_binary_op_str_mul(self):
        ast = builder.string_build('a = "*" * 40', __name__, __file__)
        self._test_const_infered(ast['a'], "*" * 40)

    def test_binary_op_bitand(self):
        ast = builder.string_build('a = 23&20', __name__, __file__)
        self._test_const_infered(ast['a'], 23&20)

    def test_binary_op_bitor(self):
        ast = builder.string_build('a = 23|8', __name__, __file__)
        self._test_const_infered(ast['a'], 23|8)

    def test_binary_op_bitxor(self):
        ast = builder.string_build('a = 23^9', __name__, __file__)
        self._test_const_infered(ast['a'], 23^9)

    def test_binary_op_shiftright(self):
        ast = builder.string_build('a = 23 >>1', __name__, __file__)
        self._test_const_infered(ast['a'], 23>>1)

    def test_binary_op_shiftleft(self):
        ast = builder.string_build('a = 23 <<1', __name__, __file__)
        self._test_const_infered(ast['a'], 23<<1)


    def test_binary_op_list_mul(self):
        for code in ('a = [[]] * 2', 'a = 2 * [[]]'):
            ast = builder.string_build(code, __name__, __file__)
            infered = list(ast['a'].infer())
            self.assertEqual(len(infered), 1)
            self.assertIsInstance(infered[0], nodes.List)
            self.assertEqual(len(infered[0].elts), 2)
            self.assertIsInstance(infered[0].elts[0], nodes.List)
            self.assertIsInstance(infered[0].elts[1], nodes.List)

    def test_binary_op_list_mul_none(self):
        'test correct handling on list multiplied by None'
        ast = builder.string_build('a = [1] * None\nb = [1] * "r"')
        infered = ast['a'].infered()
        self.assertEqual(len(infered), 1)
        self.assertEqual(infered[0], YES)
        infered = ast['b'].infered()
        self.assertEqual(len(infered), 1)
        self.assertEqual(infered[0], YES)


    def test_binary_op_tuple_add(self):
        ast = builder.string_build('a = (1,) + (2,)', __name__, __file__)
        infered = list(ast['a'].infer())
        self.assertEqual(len(infered), 1)
        self.assertIsInstance(infered[0], nodes.Tuple)
        self.assertEqual(len(infered[0].elts), 2)
        self.assertEqual(infered[0].elts[0].value, 1)
        self.assertEqual(infered[0].elts[1].value, 2)

    def test_binary_op_custom_class(self):
        code = '''
        class myarray:
            def __init__(self, array):
                self.array = array
            def __mul__(self, x):
                return myarray([2,4,6])
            def astype(self):
                return "ASTYPE"

        def randint(maximum):
            if maximum is not None:
                return myarray([1,2,3]) * 2
            else:
                return int(5)

        x = randint(1)
        '''
        ast = test_utils.build_module(code, __name__)
        infered = list(ast.igetattr('x'))
        self.assertEqual(len(infered), 2)
        value = [str(v) for v in infered]
        # The __name__ trick here makes it work when invoked directly
        # (__name__ == '__main__') and through pytest (__name__ ==
        # 'unittest_inference')
        self.assertEqual(value, ['Instance of %s.myarray' % __name__,
                                 'Instance of %s.int' % BUILTINS])

    def test_nonregr_lambda_arg(self):
        code = '''
        def f(g = lambda: None):
                __(g()).x
'''
        callfuncnode = test_utils.extract_node(code)
        infered = list(callfuncnode.infer())
        self.assertEqual(len(infered), 2, infered)
        infered.remove(YES)
        self.assertIsInstance(infered[0], nodes.Const)
        self.assertIsNone(infered[0].value)

    def test_nonregr_getitem_empty_tuple(self):
        code = '''
            def f(x):
                a = ()[x]
        '''
        ast = test_utils.build_module(code, __name__)
        infered = list(ast['f'].ilookup('a'))
        self.assertEqual(len(infered), 1)
        self.assertEqual(infered[0], YES)

    def test_nonregr_instance_attrs(self):
        """non regression for instance_attrs infinite loop : pylint / #4"""

        code = """
            class Foo(object):

                def set_42(self):
                    self.attr = 42

            class Bar(Foo):

                def __init__(self):
                    self.attr = 41
        """
        ast = test_utils.build_module(code, __name__)
        foo_class = ast['Foo']
        bar_class = ast['Bar']
        bar_self = ast['Bar']['__init__']['self']
        assattr = bar_class.instance_attrs['attr'][0]
        self.assertEqual(len(foo_class.instance_attrs['attr']), 1)
        self.assertEqual(len(bar_class.instance_attrs['attr']), 1)
        self.assertEqual(bar_class.instance_attrs, {'attr': [assattr]})
        # call 'instance_attr' via 'Instance.getattr' to trigger the bug:
        instance = bar_self.infered()[0]
        instance.getattr('attr')
        self.assertEqual(len(bar_class.instance_attrs['attr']), 1)
        self.assertEqual(len(foo_class.instance_attrs['attr']), 1)
        self.assertEqual(bar_class.instance_attrs, {'attr': [assattr]})

    def test_python25_generator_exit(self):
        sys.stderr = six.StringIO()
        data = "b = {}[str(0)+''].a"
        ast = builder.string_build(data, __name__, __file__)
        list(ast['b'].infer())
        output = sys.stderr.getvalue()
        # I have no idea how to test for this in another way...
        self.assertNotIn("RuntimeError", output, "Exception exceptions.RuntimeError: 'generator ignored GeneratorExit' in <generator object> ignored")
        sys.stderr = sys.__stderr__

    def test_python25_relative_import(self):
        data = "from ...logilab.common import date; print (date)"
        # !! FIXME also this relative import would not work 'in real' (no __init__.py in test/)
        # the test works since we pretend we have a package by passing the full modname
        ast = builder.string_build(data, 'astroid.test.unittest_inference', __file__)
        infered = next(test_utils.get_name_node(ast, 'date').infer())
        self.assertIsInstance(infered, nodes.Module)
        self.assertEqual(infered.name, 'logilab.common.date')

    def test_python25_no_relative_import(self):
        ast = resources.build_file('data/package/absimport.py')
        self.assertTrue(ast.absolute_import_activated(), True)
        infered = next(test_utils.get_name_node(ast, 'import_package_subpackage_module').infer())
        # failed to import since absolute_import is activated
        self.assertIs(infered, YES)

    def test_nonregr_absolute_import(self):
        ast = resources.build_file('data/absimp/string.py', 'data.absimp.string')
        self.assertTrue(ast.absolute_import_activated(), True)
        infered = next(test_utils.get_name_node(ast, 'string').infer())
        self.assertIsInstance(infered, nodes.Module)
        self.assertEqual(infered.name, 'string')
        self.assertIn('ascii_letters', infered.locals)

    def test_mechanize_open(self):
        try:
            import mechanize  # pylint: disable=unused-variable
        except ImportError:
            self.skipTest('require mechanize installed')
        data = '''
            from mechanize import Browser
            print(Browser)
            b = Browser()
        '''
        ast = test_utils.build_module(data, __name__)
        browser = next(test_utils.get_name_node(ast, 'Browser').infer())
        self.assertIsInstance(browser, nodes.Class)
        bopen = list(browser.igetattr('open'))
        self.skipTest('the commit said: "huum, see that later"')
        self.assertEqual(len(bopen), 1)
        self.assertIsInstance(bopen[0], nodes.Function)
        self.assertTrue(bopen[0].callable())
        b = next(test_utils.get_name_node(ast, 'b').infer())
        self.assertIsInstance(b, Instance)
        bopen = list(b.igetattr('open'))
        self.assertEqual(len(bopen), 1)
        self.assertIsInstance(bopen[0], BoundMethod)
        self.assertTrue(bopen[0].callable())

    def test_property(self):
        code = '''
            from smtplib import SMTP
            class SendMailController(object):

                @property
                def smtp(self):
                    return SMTP(mailhost, port)

                @property
                def me(self):
                    return self

            my_smtp = SendMailController().smtp
            my_me = SendMailController().me
            '''
        decorators = set(['%s.property' % BUILTINS])
        ast = test_utils.build_module(code, __name__)
        self.assertEqual(ast['SendMailController']['smtp'].decoratornames(),
                          decorators)
        propinfered = list(ast.body[2].value.infer())
        self.assertEqual(len(propinfered), 1)
        propinfered = propinfered[0]
        self.assertIsInstance(propinfered, Instance)
        self.assertEqual(propinfered.name, 'SMTP')
        self.assertEqual(propinfered.root().name, 'smtplib')
        self.assertEqual(ast['SendMailController']['me'].decoratornames(),
                          decorators)
        propinfered = list(ast.body[3].value.infer())
        self.assertEqual(len(propinfered), 1)
        propinfered = propinfered[0]
        self.assertIsInstance(propinfered, Instance)
        self.assertEqual(propinfered.name, 'SendMailController')
        self.assertEqual(propinfered.root().name, __name__)


    def test_im_func_unwrap(self):
        code = '''
            class EnvBasedTC:
                def pactions(self):
                    pass
            pactions = EnvBasedTC.pactions.im_func
            print (pactions)

            class EnvBasedTC2:
                pactions = EnvBasedTC.pactions.im_func
                print (pactions)
            '''
        ast = test_utils.build_module(code, __name__)
        pactions = test_utils.get_name_node(ast, 'pactions')
        infered = list(pactions.infer())
        self.assertEqual(len(infered), 1)
        self.assertIsInstance(infered[0], nodes.Function)
        pactions = test_utils.get_name_node(ast['EnvBasedTC2'], 'pactions')
        infered = list(pactions.infer())
        self.assertEqual(len(infered), 1)
        self.assertIsInstance(infered[0], nodes.Function)

    def test_augassign(self):
        code = '''
            a = 1
            a += 2
            print (a)
        '''
        ast = test_utils.build_module(code, __name__)
        infered = list(test_utils.get_name_node(ast, 'a').infer())

        self.assertEqual(len(infered), 1)
        self.assertIsInstance(infered[0], nodes.Const)
        self.assertEqual(infered[0].value, 3)

    def test_nonregr_func_arg(self):
        code = '''
            def foo(self, bar):
                def baz():
                    pass
                def qux():
                    return baz
                spam = bar(None, qux)
                print (spam)
            '''
        ast = test_utils.build_module(code, __name__)
        infered = list(test_utils.get_name_node(ast['foo'], 'spam').infer())
        self.assertEqual(len(infered), 1)
        self.assertIs(infered[0], YES)

    def test_nonregr_func_global(self):
        code = '''
            active_application = None

            def get_active_application():
              global active_application
              return active_application

            class Application(object):
              def __init__(self):
                 global active_application
                 active_application = self

            class DataManager(object):
              def __init__(self, app=None):
                 self.app = get_active_application()
              def test(self):
                 p = self.app
                 print (p)
        '''
        ast = test_utils.build_module(code, __name__)
        infered = list(Instance(ast['DataManager']).igetattr('app'))
        self.assertEqual(len(infered), 2, infered) # None / Instance(Application)
        infered = list(test_utils.get_name_node(ast['DataManager']['test'], 'p').infer())
        self.assertEqual(len(infered), 2, infered)
        for node in infered:
            if isinstance(node, Instance) and node.name == 'Application':
                break
        else:
            self.fail('expected to find an instance of Application in %s' % infered)

    def test_list_inference(self):
        """#20464"""
        code = '''
            import optparse

            A = []
            B = []

            def test():
              xyz = [
                "foobar=%s" % options.ca,
              ] + A + B

              if options.bind is not None:
                xyz.append("bind=%s" % options.bind)
              return xyz

            def main():
              global options

              parser = optparse.OptionParser()
              (options, args) = parser.parse_args()

            Z = test()
        '''
        ast = test_utils.build_module(code, __name__)
        infered = list(ast['Z'].infer())
        self.assertEqual(len(infered), 1, infered)
        self.assertIsInstance(infered[0], Instance)
        self.assertIsInstance(infered[0]._proxied, nodes.Class)
        self.assertEqual(infered[0]._proxied.name, 'list')

    def test__new__(self):
        code = '''
            class NewTest(object):
                "doc"
                def __new__(cls, arg):
                    self = object.__new__(cls)
                    self.arg = arg
                    return self

            n = NewTest()
        '''
        ast = test_utils.build_module(code, __name__)
        self.assertRaises(InferenceError, list, ast['NewTest'].igetattr('arg'))
        n = next(ast['n'].infer())
        infered = list(n.igetattr('arg'))
        self.assertEqual(len(infered), 1, infered)


    def test_two_parents_from_same_module(self):
        code = '''
            from data import nonregr
            class Xxx(nonregr.Aaa, nonregr.Ccc):
                "doc"
        '''
        ast = test_utils.build_module(code, __name__)
        parents = list(ast['Xxx'].ancestors())
        self.assertEqual(len(parents), 3, parents) # Aaa, Ccc, object

    def test_pluggable_inference(self):
        code = '''
            from collections import namedtuple
            A = namedtuple('A', ['a', 'b'])
            B = namedtuple('B', 'a b')
        '''
        ast = test_utils.build_module(code, __name__)
        aclass = ast['A'].infered()[0]
        self.assertIsInstance(aclass, nodes.Class)
        self.assertIn('a', aclass.instance_attrs)
        self.assertIn('b', aclass.instance_attrs)
        bclass = ast['B'].infered()[0]
        self.assertIsInstance(bclass, nodes.Class)
        self.assertIn('a', bclass.instance_attrs)
        self.assertIn('b', bclass.instance_attrs)

    def test_infer_arguments(self):
        code = '''
            class A(object):
                def first(self, arg1, arg2):
                    return arg1
                @classmethod
                def method(cls, arg1, arg2):
                    return arg2
                @classmethod
                def empty(cls):
                    return 2
                @staticmethod
                def static(arg1, arg2):
                    return arg1
                def empty_method(self):
                    return []
            x = A().first(1, [])
            y = A.method(1, [])
            z = A.static(1, [])
            empty = A.empty()
            empty_list = A().empty_method()
        '''
        ast = test_utils.build_module(code, __name__)
        int_node = ast['x'].infered()[0]
        self.assertIsInstance(int_node, nodes.Const)
        self.assertEqual(int_node.value, 1)
        list_node = ast['y'].infered()[0]
        self.assertIsInstance(list_node, nodes.List)
        int_node = ast['z'].infered()[0]
        self.assertIsInstance(int_node, nodes.Const)
        self.assertEqual(int_node.value, 1)
        empty = ast['empty'].infered()[0]
        self.assertIsInstance(empty, nodes.Const)
        self.assertEqual(empty.value, 2)
        empty_list = ast['empty_list'].infered()[0]
        self.assertIsInstance(empty_list, nodes.List)

    def test_infer_variable_arguments(self):
        code = '''
            def test(*args, **kwargs):
                vararg = args
                kwarg = kwargs
        '''
        ast = test_utils.build_module(code, __name__)
        func = ast['test']
        vararg = func.body[0].value
        kwarg = func.body[1].value

        kwarg_infered = kwarg.infered()[0]
        self.assertIsInstance(kwarg_infered, nodes.Dict)
        self.assertIs(kwarg_infered.parent, func.args)

        vararg_infered = vararg.infered()[0]
        self.assertIsInstance(vararg_infered, nodes.Tuple)
        self.assertIs(vararg_infered.parent, func.args)

    def test_infer_nested(self):
        code = """
            def nested():
                from threading import Thread

                class NestedThread(Thread):
                    def __init__(self):
                        Thread.__init__(self)
        """
        # Test that inferring Thread.__init__ looks up in
        # the nested scope.
        ast = test_utils.build_module(code, __name__)
        callfunc = next(ast.nodes_of_class(nodes.CallFunc))
        func = callfunc.func
        infered = func.infered()[0]
        self.assertIsInstance(infered, UnboundMethod)

    def test_instance_binary_operations(self):
        code = """
            class A(object):
                def __mul__(self, other):
                    return 42
            a = A()
            b = A()
            sub = a - b
            mul = a * b
        """
        ast = test_utils.build_module(code, __name__)
        sub = ast['sub'].infered()[0]
        mul = ast['mul'].infered()[0]
        self.assertIs(sub, YES)
        self.assertIsInstance(mul, nodes.Const)
        self.assertEqual(mul.value, 42)

    def test_instance_binary_operations_parent(self):
        code = """
            class A(object):
                def __mul__(self, other):
                    return 42
            class B(A):
                pass
            a = B()
            b = B()
            sub = a - b
            mul = a * b
        """
        ast = test_utils.build_module(code, __name__)
        sub = ast['sub'].infered()[0]
        mul = ast['mul'].infered()[0]
        self.assertIs(sub, YES)
        self.assertIsInstance(mul, nodes.Const)
        self.assertEqual(mul.value, 42)

    def test_instance_binary_operations_multiple_methods(self):
        code = """
            class A(object):
                def __mul__(self, other):
                    return 42
            class B(A):
                def __mul__(self, other):
                    return [42]
            a = B()
            b = B()
            sub = a - b
            mul = a * b
        """
        ast = test_utils.build_module(code, __name__)
        sub = ast['sub'].infered()[0]
        mul = ast['mul'].infered()[0]
        self.assertIs(sub, YES)
        self.assertIsInstance(mul, nodes.List)
        self.assertIsInstance(mul.elts[0], nodes.Const)
        self.assertEqual(mul.elts[0].value, 42)

    def test_infer_call_result_crash(self):
        code = """
            class A(object):
                def __mul__(self, other):
                    return type.__new__()

            a = A()
            b = A()
            c = a * b
        """
        ast = test_utils.build_module(code, __name__)
        node = ast['c']
        self.assertEqual(node.infered(), [YES])

    def test_infer_empty_nodes(self):
        # Should not crash when trying to infer EmptyNodes.
        node = nodes.EmptyNode()
        self.assertEqual(node.infered(), [YES])

    def test_infinite_loop_for_decorators(self):
        # Issue https://bitbucket.org/logilab/astroid/issue/50
        # A decorator that returns itself leads to an infinite loop.
        code = """
            def decorator():
                def wrapper():
                    return decorator()
                return wrapper

            @decorator()
            def do_a_thing():
                pass
        """
        ast = test_utils.build_module(code, __name__)
        node = ast['do_a_thing']
        self.assertEqual(node.type, 'function')

    def test_no_infinite_ancestor_loop(self):
        klass = test_utils.extract_node("""
            import datetime

            def method(self):
                datetime.datetime = something()

            class something(datetime.datetime):  #@
                pass
        """)
        self.assertIn(
            'object',
            [base.name for base in klass.ancestors()])

    def test_stop_iteration_leak(self):
         code = """
             class Test:
                 def __init__(self):
                     self.config = {0: self.config[0]}
                     self.config[0].test() #@
         """
         ast = test_utils.extract_node(code, __name__)
         expr = ast.func.expr
         self.assertRaises(InferenceError, next, expr.infer())

    def test_tuple_builtin_inference(self):
         code = """
         var = (1, 2)
         tuple() #@
         tuple([1]) #@
         tuple({2}) #@
         tuple("abc") #@
         tuple({1: 2}) #@
         tuple(var) #@
         tuple(tuple([1])) #@

         tuple(None) #@
         tuple(1) #@
         tuple(1, 2) #@
         """
         ast = test_utils.extract_node(code, __name__)

         self.assertInferTuple(ast[0], [])
         self.assertInferTuple(ast[1], [1])
         self.assertInferTuple(ast[2], [2])
         self.assertInferTuple(ast[3], ["a", "b", "c"])
         self.assertInferTuple(ast[4], [1])
         self.assertInferTuple(ast[5], [1, 2])
         self.assertInferTuple(ast[6], [1])

         for node in ast[7:]:
             infered = next(node.infer())
             self.assertIsInstance(infered, Instance)
             self.assertEqual(infered.qname(), "{}.tuple".format(BUILTINS))

    def test_set_builtin_inference(self):
         code = """
         var = (1, 2)
         set() #@
         set([1, 2, 1]) #@
         set({2, 3, 1}) #@
         set("abcab") #@
         set({1: 2}) #@
         set(var) #@
         set(tuple([1])) #@

         set(set(tuple([4, 5, set([2])]))) #@
         set(None) #@
         set(1) #@
         set(1, 2) #@
         """
         ast = test_utils.extract_node(code, __name__)

         self.assertInferSet(ast[0], [])
         self.assertInferSet(ast[1], [1, 2])
         self.assertInferSet(ast[2], [1, 2, 3])
         self.assertInferSet(ast[3], ["a", "b", "c"])
         self.assertInferSet(ast[4], [1])
         self.assertInferSet(ast[5], [1, 2])
         self.assertInferSet(ast[6], [1])

         for node in ast[7:]:
             infered = next(node.infer())
             self.assertIsInstance(infered, Instance)
             self.assertEqual(infered.qname(), "{}.set".format(BUILTINS))

    def test_list_builtin_inference(self):
         code = """
         var = (1, 2)
         list() #@
         list([1, 2, 1]) #@
         list({2, 3, 1}) #@
         list("abcab") #@
         list({1: 2}) #@
         list(var) #@
         list(tuple([1])) #@

         list(list(tuple([4, 5, list([2])]))) #@
         list(None) #@
         list(1) #@
         list(1, 2) #@
         """
         ast = test_utils.extract_node(code, __name__)
         self.assertInferList(ast[0], [])
         self.assertInferList(ast[1], [1, 1, 2])
         self.assertInferList(ast[2], [1, 2, 3])
         self.assertInferList(ast[3], ["a", "a", "b", "b", "c"])
         self.assertInferList(ast[4], [1])
         self.assertInferList(ast[5], [1, 2])
         self.assertInferList(ast[6], [1])

         for node in ast[7:]:
             infered = next(node.infer())
             self.assertIsInstance(infered, Instance)
             self.assertEqual(infered.qname(), "{}.list".format(BUILTINS))

    @test_utils.require_version('3.0')
    def test_builtin_inference_py3k(self):
         code = """
         list(b"abc") #@
         tuple(b"abc") #@
         set(b"abc") #@
         """
         ast = test_utils.extract_node(code, __name__)
         self.assertInferList(ast[0], [97, 98, 99])
         self.assertInferTuple(ast[1], [97, 98, 99])
         self.assertInferSet(ast[2], [97, 98, 99])

    def test_dict_inference(self):
        code = """
        dict() #@
        dict(a=1, b=2, c=3) #@
        dict([(1, 2), (2, 3)]) #@
        dict([[1, 2], [2, 3]]) #@
        dict([(1, 2), [2, 3]]) #@
        dict([('a', 2)], b=2, c=3) #@
        dict({1: 2}) #@
        dict({'c': 2}, a=4, b=5) #@
        def func():
            return dict(a=1, b=2)
        func() #@
        var = {'x': 2, 'y': 3}
        dict(var, a=1, b=2) #@

        dict([1, 2, 3]) #@
        dict([(1, 2), (1, 2, 3)]) #@
        dict({1: 2}, {1: 2}) #@
        dict({1: 2}, (1, 2)) #@
        dict({1: 2}, (1, 2), a=4) #@
        dict([(1, 2), ([4, 5], 2)]) #@
        dict([None,  None]) #@

        def using_unknown_kwargs(**kwargs):
            return dict(**kwargs)
        using_unknown_kwargs(a=1, b=2) #@
        """
        ast = test_utils.extract_node(code, __name__)
        self.assertInferDict(ast[0], {})
        self.assertInferDict(ast[1], {'a': 1, 'b': 2, 'c': 3})
        for i in range(2, 5):
            self.assertInferDict(ast[i], {1: 2, 2: 3})
        self.assertInferDict(ast[5], {'a': 2, 'b': 2, 'c': 3})
        self.assertInferDict(ast[6], {1: 2})
        self.assertInferDict(ast[7], {'c': 2, 'a': 4, 'b': 5})
        self.assertInferDict(ast[8], {'a': 1, 'b': 2})
        self.assertInferDict(ast[9], {'x': 2, 'y': 3, 'a': 1, 'b': 2})

        for node in ast[10:]:
            infered = next(node.infer())
            self.assertIsInstance(infered, Instance)
            self.assertEqual(infered.qname(), "{}.dict".format(BUILTINS))


    def test_str_methods(self):
         code = """
         ' '.decode() #@

         ' '.encode() #@
         ' '.join('abcd') #@
         ' '.replace('a', 'b') #@
         ' '.format('a') #@
         ' '.capitalize() #@
         ' '.title() #@
         ' '.lower() #@
         ' '.upper() #@
         ' '.swapcase() #@
         ' '.strip() #@
         ' '.rstrip() #@
         ' '.lstrip() #@
         ' '.rjust() #@
         ' '.ljust() #@
         ' '.center() #@

         ' '.index() #@
         ' '.find() #@
         ' '.count() #@
         """
         ast = test_utils.extract_node(code, __name__)
         self.assertInferConst(ast[0], u'')
         for i in range(1, 16):
             self.assertInferConst(ast[i], '')
         for i in range(16, 19):
             self.assertInferConst(ast[i], 0)

    def test_unicode_methods(self):
         code = """
         u' '.encode() #@

         u' '.decode() #@
         u' '.join('abcd') #@
         u' '.replace('a', 'b') #@
         u' '.format('a') #@
         u' '.capitalize() #@
         u' '.title() #@
         u' '.lower() #@
         u' '.upper() #@
         u' '.swapcase() #@
         u' '.strip() #@
         u' '.rstrip() #@
         u' '.lstrip() #@
         u' '.rjust() #@
         u' '.ljust() #@
         u' '.center() #@

         u' '.index() #@
         u' '.find() #@
         u' '.count() #@
         """
         ast = test_utils.extract_node(code, __name__)
         self.assertInferConst(ast[0], '')
         for i in range(1, 16):
             self.assertInferConst(ast[i], u'')
         for i in range(16, 19):
             self.assertInferConst(ast[i], 0)

    def test_scope_lookup_same_attributes(self):
        code = '''
        import collections
        class Second(collections.Counter):
            def collections(self):
                return "second"

        '''
        ast = test_utils.build_module(code, __name__)
        bases = ast['Second'].bases[0]
        inferred = next(bases.infer())
        self.assertTrue(inferred)
        self.assertIsInstance(inferred, nodes.Class)
        self.assertEqual(inferred.qname(), 'collections.Counter')


if __name__ == '__main__':
    unittest.main()
