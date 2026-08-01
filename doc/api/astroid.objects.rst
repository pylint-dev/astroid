Objects
=======

Objects that exist while Python runs but have no node of their own, so astroid
cannot represent them with the nodes it built from the source.

.. autosummary::
   :toctree: objects
   :template: autosummary_class.rst

   astroid.objects.FrozenSet
   astroid.objects.Super
   astroid.objects.DictInstance
   astroid.objects.DictItems
   astroid.objects.DictKeys
   astroid.objects.DictValues
   astroid.objects.PartialFunction
   astroid.objects.Property
