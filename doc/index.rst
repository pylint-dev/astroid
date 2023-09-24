.. Astroid documentation main file, created by
   sphinx-quickstart on Wed Jun 26 15:00:40 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. Please see the documentation for the Sphinx Python domain :
   http://sphinx-doc.org/domains.html#the-python-domain
   and the autodoc extension
   http://sphinx-doc.org/ext/autodoc.html


Welcome to astroid's documentation!
===================================

**astroid** is a library for AST parsing, static analysis and inference,
currently powering most of **pylint** capabilities.

It offers support for parsing Python source code into ASTs, similar to how
the builtin **ast** module works. On top of that, it can partially infer various
Python constructs, as seen in the following example::

   from astroid import parse
   module = parse('''
   def func(first, second):
       return first + second

   arg_1 = 2
   arg_2 = 3
   func(arg_1, arg_2)
   ''')
   >>> module.body[-1]
   <Expr l.3 at 0x10ab46f28>
   >>> inferred = next(module.body[-1].value.infer())
   >>> inferred
   <Const.int l.None at 0x10ab00588>
   >>> inferred.value
   5


**astroid** also allows the user to write various inference transforms for
enhancing its Python understanding, helping as well **pylint** in the process
of figuring out the dynamic nature of Python.

Support
-------

.. image:: media/Tidelift_Logos_RGB_Tidelift_Shorthand_On-White.png
   :width: 75
   :alt: Tidelift
   :align: left
   :class: tideliftlogo

Professional support for astroid is available as part of the `Tidelift
Subscription`_.  Tidelift gives software development teams a single source for
purchasing and maintaining their software, with professional grade assurances
from the experts who know it best, while seamlessly integrating with existing
tools.

.. _Tidelift Subscription: https://tidelift.com/subscription/pkg/pypi-astroid?utm_source=pypi-astroid&utm_medium=referral&utm_campaign=readme



.. toctree::
   :maxdepth: 2
   :hidden:

   inference

   extending

   api/index

   whatsnew

.. toctree::
   :hidden:
   :caption: Indices

   genindex

   modindex
