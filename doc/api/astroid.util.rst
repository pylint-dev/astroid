Inference results
=================

Inference does not always end on a node. These are the other values it can
yield, and the messages it produces for operations that cannot work.

The singleton itself is :obj:`astroid.Uninferable`.

.. autosummary::
   :toctree: util
   :template: autosummary_class.rst

   astroid.util.UninferableBase
   astroid.util.BadOperationMessage
   astroid.util.BadUnaryOperationMessage
   astroid.util.BadBinaryOperationMessage
