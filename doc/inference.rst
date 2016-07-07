.. _inference:

===================================
  Inference on the AST in Astroid
===================================

Introduction
============

What/where is 'inference' ?
---------------------------

Well, not *inference* in general, but inference within *astroid* in
particular... Basically this is extracting information about a node of
the AST from the node's context so as to make its description
richer. For example it can be most useful to know that this
identifier node *toto* can have values among 1, 2.0, and "yesterday".

The inference process entry-point is the :meth:`NodeNG.infer` method
of the AST nodes which is defined in :class:`NodeNG` the base class
for AST nodes. This method return a generator which yields the
successive inference for the node when going through the possible
execution branches.

How does it work ?
------------------

.. todo :: double check this :func:`infer` is monkey-patched point

The :meth:`NodeNG.infer` method either delegates the actual inference
to the instance specific method :meth:`NodeNG._explicit_inference`
when not `None` or to the overloaded :meth:`_infer` method. The
important point to note is that the :meth:`_infer` is *not* defined in
the nodes classes but is instead *monkey-patched* in the
:file:`inference.py` so that the inference implementation is not
scattered to the multiple node classes.

.. note:: The inference method are to be wrapped in decorators like
          :func:`path_wrapper` which update the inference context.

In both cases the :meth:`infer` returns a *generator* which iterates
through the various *values* the node could take.

.. todo:: introduce the :func:`inference.infer_end` method and
   	  terminal nodes along with the recursive call

In some case the value yielded will not be a node found in the AST of the node
but an instance of a special inference class such as :class:`_Yes`,
:class:`Instance`,etc. Those classes are defined in :file:`bases.py`.

Namely, the special singleton :obj:`YES()` is yielded when the inference reaches
a point where t can't follow the code and is so unable to guess a value ; and
instances of the :class:`Instance` class are yielded when the current node is
infered to be an instance of some known class.

What does it rely upon ?
------------------------

In order to perform such an inference the :meth:`infer` methods rely
on several more global objects, mainly :

:obj:`MANAGER`
    is a unique global instance of the class :class:`AstroidManager`,
    it helps managing and reusing inference needed / done somewhere
    else than the current invocation node.

:class:`InferenceContext`
    Instances of this class can be passed to the :meth:`infer` methods
    to convey additional information on the context of the current
    node, and especially the current scope.

.. todo:: Write something about :class:`Scope` objects and
          :meth:`NodeNG.lookup` method.

