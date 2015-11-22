"""Astroid hooks for the Python standard library."""

# Namedtuple template strings
from collections import _class_template, _repr_template, _field_template
import functools
import sys
import textwrap

from astroid import (
    MANAGER, UseInferenceDefault, inference_tip,
    InferenceError, register_module_extender)
from astroid import exceptions
from astroid.interpreter.objects import BoundMethod
from astroid import nodes
from astroid.builder import AstroidBuilder
from astroid import parse
from astroid import util

PY3K = sys.version_info > (3, 0)
PY33 = sys.version_info >= (3, 3)
PY34 = sys.version_info >= (3, 4)

def infer_first(node, context):
    try:
        value = next(node.infer(context=context))
        if value is util.Uninferable:
            raise UseInferenceDefault()
        else:
            return value
    except StopIteration:
        util.reraise(InferenceError())


# module specific transformation functions #####################################

def hashlib_transform():
    template = '''

class %(name)s(object):
  def __init__(self, value=''): pass
  def digest(self):
    return %(digest)s
  def copy(self):
    return self
  def update(self, value): pass
  def hexdigest(self):
    return ''
  @property
  def name(self):
    return %(name)r
  @property
  def block_size(self):
    return 1
  @property
  def digest_size(self):
    return 1
'''
    algorithms = ('md5', 'sha1', 'sha224', 'sha256', 'sha384', 'sha512')
    classes = "".join(
        template % {'name': hashfunc, 'digest': 'b""' if PY3K else '""'}
        for hashfunc in algorithms)
    return AstroidBuilder(MANAGER).string_build(classes)


def collections_transform():
    return AstroidBuilder(MANAGER).string_build('''

class defaultdict(dict):
    default_factory = None
    def __missing__(self, key): pass

class deque(object):
    maxlen = 0
    def __init__(self, iterable=None, maxlen=None):
        self.iterable = iterable
    def append(self, x): pass
    def appendleft(self, x): pass
    def clear(self): pass
    def count(self, x): return 0
    def extend(self, iterable): pass
    def extendleft(self, iterable): pass
    def pop(self): pass
    def popleft(self): pass
    def remove(self, value): pass
    def reverse(self): pass
    def rotate(self, n): pass
    def __iter__(self): return self
    def __reversed__(self): return self.iterable[::-1]
    def __getitem__(self, index): pass
''')


def pkg_resources_transform():
    return AstroidBuilder(MANAGER).string_build('''

def resource_exists(package_or_requirement, resource_name):
    pass

def resource_isdir(package_or_requirement, resource_name):
    pass

def resource_filename(package_or_requirement, resource_name):
    pass

def resource_stream(package_or_requirement, resource_name):
    pass

def resource_string(package_or_requirement, resource_name):
    pass

def resource_listdir(package_or_requirement, resource_name):
    pass

def extraction_error():
    pass

def get_cache_path(archive_name, names=()):
    pass

def postprocess(tempname, filename):
    pass

def set_extraction_path(path):
    pass

def cleanup_resources(force=False):
    pass

''')


def subprocess_transform():
    if PY3K:
        communicate = (bytes('string', 'ascii'), bytes('string', 'ascii'))
        communicate_signature = 'def communicate(self, input=None, timeout=None)'
        init = """
        def __init__(self, args, bufsize=0, executable=None,
                     stdin=None, stdout=None, stderr=None,
                     preexec_fn=None, close_fds=False, shell=False,
                     cwd=None, env=None, universal_newlines=False,
                     startupinfo=None, creationflags=0, restore_signals=True,
                     start_new_session=False, pass_fds=()):
            pass
        """
    else:
        communicate = ('string', 'string')
        communicate_signature = 'def communicate(self, input=None)'
        init = """
        def __init__(self, args, bufsize=0, executable=None,
                     stdin=None, stdout=None, stderr=None,
                     preexec_fn=None, close_fds=False, shell=False,
                     cwd=None, env=None, universal_newlines=False,
                     startupinfo=None, creationflags=0):
            pass
        """
    if PY33:
        wait_signature = 'def wait(self, timeout=None)'
    else:
        wait_signature = 'def wait(self)'
    if PY3K:
        ctx_manager = '''
        def __enter__(self): return self
        def __exit__(self, *args): pass
        '''
    else:
        ctx_manager = ''
    code = textwrap.dedent('''

    class Popen(object):
        returncode = pid = 0
        stdin = stdout = stderr = file()

        %(init)s

        %(communicate_signature)s:
            return %(communicate)r
        %(wait_signature)s:
            return self.returncode
        def poll(self):
            return self.returncode
        def send_signal(self, signal):
            pass
        def terminate(self):
            pass
        def kill(self):
            pass
        %(ctx_manager)s
       ''' % {'init': init,
              'communicate': communicate,
              'communicate_signature': communicate_signature,
              'wait_signature': wait_signature,
              'ctx_manager': ctx_manager})
    return AstroidBuilder(MANAGER).string_build(code)


# namedtuple and Enum support

def _looks_like(node, name):
    func = node.func
    if isinstance(func, nodes.Attribute):
        return func.attrname == name
    if isinstance(func, nodes.Name):
        return func.name == name
    return False

_looks_like_namedtuple = functools.partial(_looks_like, name='namedtuple')
_looks_like_enum = functools.partial(_looks_like, name='Enum')


def infer_namedtuple_enum_fields(call_node, context):
    # node is a Call node, class name as first argument and generated class
    # attributes as second argument
    if len(call_node.args) != 2:
        # something weird here, go back to class implementation
        raise UseInferenceDefault()
    # namedtuple or enums list of attributes can be a list of strings or a
    # whitespace-separate string
    try:
        type_name = infer_first(call_node.args[0], context).value
        fields = infer_first(call_node.args[1], context)
        return type_name, fields
    except (AttributeError, exceptions.InferenceError):
        raise UseInferenceDefault()


def infer_namedtuple(namedtuple_call, context=None):
    """Specific inference function for namedtuple Call node"""

    type_name, fields = infer_namedtuple_enum_fields(namedtuple_call, context)
    if isinstance(fields, nodes.Const) and isinstance(fields.value, str):
        field_names = tuple(fields.value.replace(',', ' ').split())
    elif isinstance(fields, (nodes.Tuple, nodes.List)):
        field_names = tuple(infer_first(const, context).value for const in fields.elts)
    else:
        raise UseInferenceDefault()

    class_definition = _class_template.format(
        typename = type_name,
        field_names = field_names,
        num_fields = len(field_names),
        arg_list = repr(field_names).replace("'", "")[1:-1],
        repr_fmt = ', '.join(_repr_template.format(name=name)
                             for name in field_names),
        field_defs = '\n'.join(_field_template.format(index=index, name=name)
                               for index, name in enumerate(field_names))
    )

    namedtuple_node = parse(class_definition).getattr(type_name)[0]
    init_template = '''def __init__(self, {args}):
{assignments}'''
    init_definition = init_template.format(
        args=', '.join(field_names),
        assignments='\n'.join((' '*4 + 'self.{f} = {f}').format(f=f) for f in field_names))
    init_node = parse(init_definition).getattr('__init__')[0]
    init_node.parent = namedtuple_node
    namedtuple_node.body.append(init_node)
    # This is an ugly hack to work around the normal process for
    # assigning to instance_attrs relying on inference and thus being
    # affected by instance_attrs already present.
    for assignment in init_node.body:
        namedtuple_node.instance_attrs[assignment.targets[0].attrname].append(assignment.targets[0])
    return iter([namedtuple_node])


def infer_enum(enum_call, context=None):
    """ Specific inference function for enum Call node. """
    type_name, fields = infer_namedtuple_enum_fields(enum_call, context)
    try:
         attributes = tuple(fields.value.replace(',', ' ').split())
    except AttributeError as exception:
        # Enums supports either iterator of (name, value) pairs
        # or mappings.
        # TODO: support only list, tuples and mappings.
        if hasattr(fields, 'items') and isinstance(fields.items, list):
            attributes = [infer_first(const[0], context).value
                          for const in fields.items
                          if isinstance(const[0], nodes.Const)]
        elif hasattr(fields, 'elts'):
            # Enums can support either ["a", "b", "c"]
            # or [("a", 1), ("b", 2), ...], but they can't
            # be mixed.
            if all(isinstance(const, nodes.Tuple)
                   for const in fields.elts):
                attributes = [infer_first(const.elts[0], context).value
                              for const in fields.elts
                              if isinstance(const, nodes.Tuple)]
            else:
                attributes = [infer_first(const, context).value
                              for const in fields.elts]
        else:
            util.reraise(exception)
        if not attributes:
            util.reraise(exception)
    
    template = textwrap.dedent('''
    """Mock module to hold enum classes"""
    class EnumMeta(object):
        """Mock Enum metaclass"""

    class {name}(EnumMeta):
        """Mock Enum class"""
        def __init__(self, {attributes}):
            """Fake __init__ for enums"""
    ''')
    code = template.format(name=type_name, attributes=', '.join(attributes))
    assignment_lines = [(' '*8 + 'self.{a} = {a}'.format(a=a))
                        for a in attributes]
    code += '\n'.join(assignment_lines)
    module = AstroidBuilder(MANAGER).string_build(code)
    return iter([module.body[1]])


def infer_enum_class(enum_node):
    """ Specific inference for enums. """
    names = {'Enum', 'IntEnum', 'enum.Enum', 'enum.IntEnum'}
    for basename in enum_node.basenames:
        # TODO: doesn't handle subclasses yet. This implementation
        # is a hack to support enums.
        if basename not in names:
            continue
        if enum_node.root().name == 'enum':
            # Skip if the class is directly from enum module.
            break
        for local, values in enum_node.locals.items():
            if any(not isinstance(value, nodes.AssignName)
                   for value in values):
                continue

            stmt = values[0].statement()
            if isinstance(stmt.targets[0], nodes.Tuple):
                targets = stmt.targets[0].itered()
            else:
                targets = stmt.targets

            # new_targets = []
            for target in targets:
                # Replace all the assignments with our mocked class.
                classdef = textwrap.dedent('''
                class %(name)s(%(types)s):
                    @property
                    def value(self):
                        # Not the best return.
                        return None
                    @property
                    def name(self):
                        return %(name)r
                ''' % {'name': target.name, 'types': ', '.join(enum_node.basenames)})
                class_node = parse(classdef)[target.name]
                class_node.parent = target.parent
                for method in enum_node.mymethods():
                    class_node.body.append(method)
                    method.parent = class_node
                instance_node = nodes.InterpreterObject(name=local, object_=class_node.instantiate_class(), parent=enum_node.parent)
                # Replace the Assign node with the Enum instance
                enum_node.body[enum_node.body.index(target.parent)] = instance_node
        break
    return enum_node

def multiprocessing_transform():
    module = AstroidBuilder(MANAGER).string_build(textwrap.dedent('''
    from multiprocessing.managers import SyncManager
    def Manager():
        return SyncManager()
    '''))
    if not PY34:
        return module

    # On Python 3.4, multiprocessing uses a getattr lookup inside contexts,
    # in order to get the attributes they need. Since it's extremely
    # dynamic, we use this approach to fake it.
    node = AstroidBuilder(MANAGER).string_build(textwrap.dedent('''
    from multiprocessing.context import DefaultContext, BaseContext
    default = DefaultContext()
    base = BaseContext()
    '''))
    try:
        context = next(node['default'].infer())
        base = next(node['base'].infer())
    except InferenceError:
        return module

    for node in (context, base):
        for key, value in node.locals.items():
            if key.startswith("_"):
                continue

            value = value[0]
            if isinstance(value, nodes.FunctionDef):
                # We need to rebind this, since otherwise
                # it will have an extra argument (self).
                value = BoundMethod(value, node)
            module.body.append(nodes.InterpreterObject(object_=value, name=key,
                                               parent=module))
    return module

def multiprocessing_managers_transform():
    return AstroidBuilder(MANAGER).string_build(textwrap.dedent('''
    import array
    import threading
    import multiprocessing.pool as pool

    import six

    class Namespace(object):
        pass

    class Value(object):
        def __init__(self, typecode, value, lock=True):
            self._typecode = typecode
            self._value = value
        def get(self):
            return self._value
        def set(self, value):
            self._value = value
        def __repr__(self):
            return '%s(%r, %r)'%(type(self).__name__, self._typecode, self._value)
        value = property(get, set)

    def Array(typecode, sequence, lock=True):
        return array.array(typecode, sequence)

    class SyncManager(object):
        Queue = JoinableQueue = six.moves.queue.Queue
        Event = threading.Event
        RLock = threading.RLock
        BoundedSemaphore = threading.BoundedSemaphore
        Condition = threading.Condition
        Barrier = threading.Barrier
        Pool = pool.Pool
        list = list
        dict = dict
        Value = Value
        Array = Array
        Namespace = Namespace
        __enter__ = lambda self: self
        __exit__ = lambda *args: args
        
        def start(self, initializer=None, initargs=None):
            pass
        def shutdown(self):
            pass
    '''))


MANAGER.register_transform(nodes.Call, inference_tip(infer_namedtuple),
                           _looks_like_namedtuple)
MANAGER.register_transform(nodes.Call, inference_tip(infer_enum),
                           _looks_like_enum)
MANAGER.register_transform(nodes.ClassDef, infer_enum_class)
register_module_extender(MANAGER, 'hashlib', hashlib_transform)
register_module_extender(MANAGER, 'collections', collections_transform)
register_module_extender(MANAGER, 'pkg_resources', pkg_resources_transform)
register_module_extender(MANAGER, 'subprocess', subprocess_transform)
register_module_extender(MANAGER, 'multiprocessing.managers',
                         multiprocessing_managers_transform)
register_module_extender(MANAGER, 'multiprocessing', multiprocessing_transform)
