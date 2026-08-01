Object models
=============

Every Python object carries attributes that no source code declares: a module
has ``__name__``, a function has ``__defaults__``, a class has ``__mro__``. An
object model supplies those attributes for one kind of object, so that looking
them up infers a value instead of failing.

.. autosummary::
   :toctree: objectmodel
   :template: autosummary_class.rst

   astroid.interpreter.objectmodel.ObjectModel
   astroid.interpreter.objectmodel.ModuleModel
   astroid.interpreter.objectmodel.FunctionModel
   astroid.interpreter.objectmodel.ClassModel
   astroid.interpreter.objectmodel.SuperModel
   astroid.interpreter.objectmodel.UnboundMethodModel
   astroid.interpreter.objectmodel.BoundMethodModel
   astroid.interpreter.objectmodel.ContextManagerModel
   astroid.interpreter.objectmodel.GeneratorBaseModel
   astroid.interpreter.objectmodel.GeneratorModel
   astroid.interpreter.objectmodel.AsyncGeneratorModel
   astroid.interpreter.objectmodel.InstanceModel
   astroid.interpreter.objectmodel.ExceptionInstanceModel
   astroid.interpreter.objectmodel.DictModel
   astroid.interpreter.objectmodel.PropertyModel
