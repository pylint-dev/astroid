#
from logilab.astng import NotFoundError, NoDefault
from logilab.astng._nodes import *
from logilab.astng.lookup import LookupMixIn, LocalsDictMixIn


class ArgumentsNG(Arguments, NodeNG):
    """class representing an Arguments node"""

    def format_args(self):
        """return arguments formatted as string"""
        result = [_format_args(self.args, self.defaults)]
        if self.vararg:
            result.append('*%s' % self.vararg)
        if self.kwarg:
            result.append('**%s' % self.kwarg)
        return ', '.join(result)

    def default_value(self, argname):
        """return the default value for an argument

        :raise `NoDefault`: if there is no default value defined
        """
        i = _find_arg(argname, self.args)[0]
        if i is not None:
            idx = i - (len(self.args) - len(self.defaults))
            if idx >= 0:
                return self.defaults[idx]
        raise NoDefault()

    def is_argument(self, name):
        """return True if the name is defined in arguments"""
        if name == self.vararg:
            return True
        if name == self.kwarg:
            return True
        return self.find_argname(name, True)[1] is not None

    def find_argname(self, argname, rec=False):
        """return index and Name node with given name"""
        if self.args: # self.args may be None in some cases (builtin function)
            return _find_arg(argname, self.args, rec)
        return None, None

def _find_arg(argname, args, rec=False):
    for i, arg in enumerate(args):
        if isinstance(arg, Tuple):
            if rec:
                found = _find_arg(argname, arg.elts)
                if found[0] is not None:
                    return found
        elif arg.name == argname:
            return i, arg
    return None, None


def _format_args(args, defaults=None):
    values = []
    if args is None:
        return ''
    if defaults is not None:
        default_offset = len(args) - len(defaults)
    for i, arg in enumerate(args):
        if isinstance(arg, Tuple):
            values.append('(%s)' % _format_args(arg.elts))
        else:
            values.append(arg.name)
            if defaults is not None and i >= default_offset:
                values[-1] += '=' + defaults[i-default_offset].as_string()
    return ', '.join(values)


class AssAttrNG(AssAttr, NodeNG):
    """class representing an AssAttr node"""


class AssNameNG(AssName, LookupMixIn, NodeNG):
    """class representing an AssName node"""


class AssertNG(Assert, StmtMixIn, NodeNG):
    """class representing an Assert node"""


class AssignNG(Assign, StmtMixIn, NodeNG):
    """class representing an Assign node"""


class AugAssignNG(AugAssign, StmtMixIn, NodeNG):
    """class representing an AugAssign node"""


class BackquoteNG(Backquote, NodeNG):
    """class representing a Backquote node"""


class BinOpNG(BinOp, NodeNG):
    """class representing a BinOp node"""


class BoolOpNG(BoolOp, NodeNG):
    """class representing a BoolOp node"""


class BreakNG(Break, StmtMixIn, NodeNG):
    """class representing a Break node"""


class CallFuncNG(CallFunc, NodeNG):
    """class representing a CallFunc node"""


class CompareNG(Compare, NodeNG):
    """class representing a Compare node"""

    def get_children(self):
        """override get_children for tuple fields"""
        yield self.left
        for _, comparator in self.ops:
            yield comparator # we don't want the 'op'

class ComprehensionNG(Comprehension, NodeNG):
    """class representing a Comprehension node"""


class ConstNG(Const, NodeNG):
    """class representing a Const node"""

    def getitem(self, index, context=None):
        if isinstance(self.value, basestring):
            return self.value[index]
        raise TypeError()

    def has_dynamic_getattr(self):
        return False

    def itered(self):
        if isinstance(self.value, basestring):
            return self.value
        raise TypeError()

class ContinueNG(Continue, StmtMixIn, NodeNG):
    """class representing a Continue node"""


class DecoratorsNG(Decorators, NodeNG):
    """class representing a Decorators node"""

    def scope(self):
        # skip the function node to go directly to the upper level scope
        return self.parent.parent.scope()

class DelAttrNG(DelAttr, NodeNG):
    """class representing a DelAttr node"""


class DelNameNG(DelName, LookupMixIn, NodeNG):
    """class representing a DelName node"""


class DeleteNG(Delete, StmtMixIn, NodeNG):
    """class representing a Delete node"""


class DictNG(Dict, NodeNG):
    """class representing a Dict node"""

    def pytype(self):
        return '__builtin__.dict'

    def get_children(self):
        """get children of a Dict node"""
        # overrides get_children
        for key, value in self.items:
            yield key
            yield value

    def itered(self):
        return self.items[::2]

    def getitem(self, key, context=None):
        for i in xrange(0, len(self.items), 2):
            for inferedkey in self.items[i].infer(context):
                if inferedkey is YES:
                    continue
                if isinstance(inferedkey, Const) and inferedkey.value == key:
                    return self.items[i+1]
        raise IndexError(key)


class DiscardNG(Discard, StmtMixIn, NodeNG):
    """class representing a Discard node"""


class EllipsisNG(Ellipsis, NodeNG):
    """class representing an Ellipsis node"""


class EmptyNodeNG(EmptyNode, NodeNG):
    """class representing an EmptyNode node"""


class ExceptHandlerNG(ExceptHandler, StmtMixIn, NodeNG):
    """class representing an ExceptHandler node"""

    def _blockstart_toline(self):
        if self.name:
            return self.name.tolineno
        elif self.type:
            return self.type.tolineno
        else:
            return self.lineno

    def set_line_info(self, lastchild):
        self.fromlineno = self.lineno
        self.tolineno = lastchild.tolineno
        self.blockstart_tolineno = self._blockstart_toline()

    def catch(self, exceptions):
        if self.type is None or exceptions is None:
            return True
        for node in self.type.nodes_of_class(Name):
            if node.name in exceptions:
                return True


class ExecNG(Exec, StmtMixIn, NodeNG):
    """class representing an Exec node"""


class ExtSliceNG(ExtSlice, NodeNG):
    """class representing an ExtSlice node"""


class ForNG(For, BlockRangeMixIn, StmtMixIn, NodeNG):
    """class representing a For node"""

    def _blockstart_toline(self):
        return self.iter.tolineno

class FromNG(From, StmtMixIn, NodeNG):
    """class representing a From node"""

    def real_name(self, asname):
        """get name from 'as' name"""
        for index in range(len(self.names)):
            name, _asname = self.names[index]
            if name == '*':
                return asname
            if not _asname:
                name = name.split('.', 1)[0]
                _asname = name
            if asname == _asname:
                return name
        raise NotFoundError(asname)


class GenExprNG(GenExpr, LocalsDictMixIn, NodeNG):
    """class representing a GenExpr node"""


class GetattrNG(Getattr, NodeNG):
    """class representing a Getattr node"""


class GlobalNG(Global, StmtMixIn, NodeNG):
    """class representing a Global node"""


class IfNG(If, BlockRangeMixIn, StmtMixIn, NodeNG):
    """class representing an If node"""

    def _blockstart_toline(self):
        return self.test.tolineno

    def block_range(self, lineno):
        """handle block line numbers range for if statements"""
        if lineno == self.body[0].fromlineno:
            return lineno, lineno
        if lineno <= self.body[-1].tolineno:
            return lineno, self.body[-1].tolineno
        return self._elsed_block_range(lineno, self.orelse,
                                       self.body[0].fromlineno - 1)


class IfExpNG(IfExp, NodeNG):
    """class representing an IfExp node"""


class ImportNG(Import, StmtMixIn, NodeNG):
    """class representing an Import node"""

    def real_name(self, asname):
        """get name from 'as' name"""
        for index in range(len(self.names)):
            name, _asname = self.names[index]
            if name == '*':
                return asname
            if not _asname:
                name = name.split('.', 1)[0]
                _asname = name
            if asname == _asname:
                return name
        raise NotFoundError(asname)


class IndexNG(Index, NodeNG):
    """class representing an Index node"""


class KeywordNG(Keyword, NodeNG):
    """class representing a Keyword node"""


class ListNG(List, NodeNG):
    """class representing a List node"""

    def pytype(self):
        return '__builtin__.list'

    def getitem(self, index, context=None):
        return self.elts[index]

    def itered(self):
        return self.elts


class ListCompNG(ListComp, NodeNG):
    """class representing a ListComp node"""


class NameNG(Name, LookupMixIn, NodeNG):
    """class representing a Name node"""


class PassNG(Pass, StmtMixIn, NodeNG):
    """class representing a Pass node"""


class PrintNG(Print, StmtMixIn, NodeNG):
    """class representing a Print node"""


class RaiseNG(Raise, StmtMixIn, NodeNG):
    """class representing a Raise node"""


class ReturnNG(Return, StmtMixIn, NodeNG):
    """class representing a Return node"""


class SliceNG(Slice, NodeNG):
    """class representing a Slice node"""


class SubscriptNG(Subscript, NodeNG):
    """class representing a Subscript node"""


class TryExceptNG(TryExcept, BlockRangeMixIn, StmtMixIn, NodeNG):
    """class representing a TryExcept node"""

    def _blockstart_toline(self):
        return self.lineno

    def block_range(self, lineno):
        """handle block line numbers range for try/except statements"""
        last = None
        for exhandler in self.handlers:
            if exhandler.type and lineno == exhandler.type.fromlineno:
                return lineno, lineno
            if exhandler.body[0].fromlineno <= lineno <= exhandler.body[-1].tolineno:
                return lineno, exhandler.body[-1].tolineno
            if last is None:
                last = exhandler.body[0].fromlineno - 1
        return self._elsed_block_range(lineno, self.orelse, last)


class TryFinallyNG(TryFinally, BlockRangeMixIn, StmtMixIn, NodeNG):
    """class representing a TryFinally node"""

    def _blockstart_toline(self):
        return self.lineno

    def block_range(self, lineno):
        """handle block line numbers range for try/finally statements"""
        child = self.body[0]
        # py2.5 try: except: finally:
        if (isinstance(child, TryExcept) and child.fromlineno == self.fromlineno
            and lineno > self.fromlineno and lineno <= child.tolineno):
            return child.block_range(lineno)
        return self._elsed_block_range(lineno, self.finalbody)


class TupleNG(Tuple, NodeNG):
    """class representing a Tuple node"""

    def pytype(self):
        return '__builtin__.tuple'

    def getitem(self, index, context=None):
        return self.elts[index]

    def itered(self):
        return self.elts


class UnaryOpNG(UnaryOp, NodeNG):
    """class representing an UnaryOp node"""


class WhileNG(While, BlockRangeMixIn, StmtMixIn, NodeNG):
    """class representing a While node"""

    def _blockstart_toline(self):
        return self.test.tolineno

    def block_range(self, lineno):
        """handle block line numbers range for for and while statements"""
        return self. _elsed_block_range(lineno, self.orelse)

class WithNG(With, BlockRangeMixIn, StmtMixIn, NodeNG):
    """class representing a With node"""

    def _blockstart_toline(self):
        if self.vars:
            return self.vars.tolineno
        else:
            return self.expr.tolineno


class YieldNG(Yield, NodeNG):
    """class representing a Yield node"""

