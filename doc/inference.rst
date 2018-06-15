.. _inference:

Inference Introduction
======================

What/where is 'inference' ?
---------------------------


The inference is a mechanism through which *astroid* tries to interpret
statically your Python code.

How does it work ?
------------------

The magic is handled by :meth:`NodeNG.infer` method.
*astroid* usually provides inference support for various Python primitives,
such as protocols and statements, but it can also be enriched
via `inference transforms`.

In both cases the :meth:`infer` must return a *generator* which iterates
through the various *values* the node could take.

In some case the value yielded will not be a node found in the AST of the node
but an instance of a special inference class such as :class:`Uninferable`,
or :class:`Instance`.

Namely, the special singleton :obj:`Uninferable()` is yielded when the inference reaches
a point where it can't follow the code and is so unable to guess a value; and
instances of the :class:`Instance` class are yielded when the current node is
inferred to be an instance of some known class.


Crash course into astroid's inference
--------------------------------------

Let's see some examples on how the inference might work in in ``astroid``.

First we'll need to do a detour through some of the ``astroid``'s APIs.

``astroid`` offers a relatively similar API to the builtin ``ast`` module,
that is, you can do ``astroid.parse(string)`` to get an AST out of the given
string::

    >>> tree = astroid.parse('a + b')
    >>> tree
    >>> <Module l.0 at 0x10d8a68d0>

    >>> print(tree.repr_tree())
    Module(
       name='',
       doc=None,
       file='<?>',
       path=['<?>'],
       package=False,
       pure_python=True,
       future_imports=set(),
       body=[Expr(value=BinOp(
                op='+',
                left=Name(name='a'),
                right=Name(name='b')))])


The :meth:`repr_tree` is super useful to inspect how a tree actually looks.
Most of the time you can access the same fields as those represented
in the output of :meth:`repr_tree` so you can do ``tree.body[0].value.left``
to get the left hand side operand of the addition operation.

Another useful function that you can use is :func`astroid.extract_node`,
which given a string, tries to extract one or more nodes from the given string::

   >>> node = astroid.extract_node('''
   ... a = 1
   ... b = 2
   ... c
   ''')

In that example, the node that is going to be returned is the last node
from the tree, so it will be the ``Name(c)`` node.
You can also use :func:`astroid.extract_node` to extract multiple nodes::

   >>> nodes = astroid.extract_node('''
   ... a = 1 #@
   ... b = 2 #@
   ... c
   ''')

You can use ``#@`` comment to annotate the lines for which you want the
corresponding nodes to be extracted. In that example, what we're going to
extract is two ``Expr`` nodes, which is in astroid's parlance, two statements,
but you can access their underlying ``Assign`` nodes using the ``.value`` attribute.

Now let's see how can we use ``astroid`` to infer what's going on with your code.

The main method that you can use is :meth:`infer`. It returns a generator
with all the potential values that ``astroid`` can extract for a piece of code::

    >>> name_node = astroid.extract_node('''
    ... a = 1
    ... b = 2
    ... c = a + b
    ... c
    ''')
    >>> inferred = next(name_node.infer())
    >>> inferred
    <Const.int l.None at 0x10d913128>
    >>> inferred.value
    3

From this example you can see that ``astroid`` is capable of *inferring* what ``c``
might hold, which is a constant value with the number 3.
