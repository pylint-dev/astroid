
# from lookup import NodeNG, StmtMixIn, LocalsDictMixIn


class ArgumentsNG(object):# (Arguments, StmtMixIn, NodeNG)
    """class representing an Arguments node"""


class AssAttrNG(object):# (AssAttr, StmtMixIn, NodeNG)
    """class representing an AssAttr node"""


class AssNameNG(object):# (AssName, StmtMixIn, NodeNG)
    """class representing an AssName node"""


class AssertNG(object):# (Assert, NodeNG)
    """class representing an Assert node"""


class AssignNG(object):# (Assign, NodeNG)
    """class representing an Assign node"""


class AugAssignNG(object):# (AugAssign, NodeNG)
    """class representing an AugAssign node"""


class BackquoteNG(object):# (Backquote, StmtMixIn, NodeNG)
    """class representing a Backquote node"""


class BinOpNG(object):# (BinOp, StmtMixIn, NodeNG)
    """class representing a BinOp node"""


class BoolOpNG(object):# (BoolOp, StmtMixIn, NodeNG)
    """class representing a BoolOp node"""


class BreakNG(object):# (Break, NodeNG)
    """class representing a Break node"""


class CallFuncNG(object):# (CallFunc, StmtMixIn, NodeNG)
    """class representing a CallFunc node"""


class ClassNG(object):# (Class, NodeNG)
    """class representing a Class node"""


class CompareNG(object):# (Compare, StmtMixIn, NodeNG)
    """class representing a Compare node"""

    def get_children(self):
        """override get_children for tuple fields"""
        yield self.left
        for _, comparator in self.ops:
            yield comparator # we don't want the 'op'

class ComprehensionNG(object):# (Comprehension, StmtMixIn, NodeNG)
    """class representing a Comprehension node"""


class ConstNG(object):# (Const, StmtMixIn, NodeNG)
    """class representing a Const node"""


class ContinueNG(object):# (Continue, NodeNG)
    """class representing a Continue node"""


class DecoratorsNG(object):# (Decorators, StmtMixIn, NodeNG)
    """class representing a Decorators node"""

    def scope(self):
        # skip the function node to go directly to the upper level scope
        return self.parent.parent.scope()

class DelAttrNG(object):# (DelAttr, StmtMixIn, NodeNG)
    """class representing a DelAttr node"""


class DelNameNG(object):# (DelName, StmtMixIn, NodeNG)
    """class representing a DelName node"""


class DeleteNG(object):# (Delete, NodeNG)
    """class representing a Delete node"""


class DictNG(object):# (Dict, StmtMixIn, NodeNG)
    """class representing a Dict node"""

    def get_children(self):
        """get children of a Dict node"""
        # overrides get_children
        for key, value in self.items:
            yield key
            yield value


class DiscardNG(object):# (Discard, NodeNG)
    """class representing a Discard node"""


class EllipsisNG(object):# (Ellipsis, StmtMixIn, NodeNG)
    """class representing an Ellipsis node"""


class EmptyNodeNG(object):# (EmptyNode, StmtMixIn, NodeNG)
    """class representing an EmptyNode node"""


class ExceptHandlerNG(object):# (ExceptHandler, NodeNG)
    """class representing an ExceptHandler node"""

    def _blockstart_toline(self):
        if self.name:
            return self.name.tolineno
        elif self.type:
            return self.type.tolineno
        else:
            return self.lineno


class ExecNG(object):# (Exec, NodeNG)
    """class representing an Exec node"""


class ExtSliceNG(object):# (ExtSlice, StmtMixIn, NodeNG)
    """class representing an ExtSlice node"""


class ForNG(object):# (For, NodeNG)
    """class representing a For node"""

    def _blockstart_toline(self):
        return self.iter.tolineno


class FromNG(object):# (From, NodeNG)
    """class representing a From node"""


class FunctionNG(object):# (Function, NodeNG)
    """class representing a Function node"""


class GenExprNG(object):# (GenExpr, LocalsDictMixIn, StmtMixIn, NodeNG)
    """class representing a GenExpr node"""


class GetattrNG(object):# (Getattr, StmtMixIn, NodeNG)
    """class representing a Getattr node"""


class GlobalNG(object):# (Global, NodeNG)
    """class representing a Global node"""


class IfNG(object):# (If, NodeNG)
    """class representing an If node"""

    def _blockstart_toline(self):
        return self.test.tolineno



class IfExpNG(object):# (IfExp, StmtMixIn, NodeNG)
    """class representing an IfExp node"""


class ImportNG(object):# (Import, NodeNG)
    """class representing an Import node"""


class IndexNG(object):# (Index, StmtMixIn, NodeNG)
    """class representing an Index node"""


class KeywordNG(object):# (Keyword, StmtMixIn, NodeNG)
    """class representing a Keyword node"""


class LambdaNG(object):# (Lambda, LocalsDictMixIn, StmtMixIn, NodeNG)
    """class representing a Lambda node"""


class ListNG(object):# (List, StmtMixIn, NodeNG)
    """class representing a List node"""


class ListCompNG(object):# (ListComp, StmtMixIn, NodeNG)
    """class representing a ListComp node"""


class ModuleNG(object):# (Module, StmtMixIn, NodeNG)
    """class representing a Module node"""

    is_statement = False # override StatementMixin


class NameNG(object):# (Name, StmtMixIn, NodeNG)
    """class representing a Name node"""


class PassNG(object):# (Pass, NodeNG)
    """class representing a Pass node"""


class PrintNG(object):# (Print, NodeNG)
    """class representing a Print node"""


class RaiseNG(object):# (Raise, NodeNG)
    """class representing a Raise node"""


class ReturnNG(object):# (Return, NodeNG)
    """class representing a Return node"""


class SliceNG(object):# (Slice, StmtMixIn, NodeNG)
    """class representing a Slice node"""


class SubscriptNG(object):# (Subscript, StmtMixIn, NodeNG)
    """class representing a Subscript node"""


class TryExceptNG(object):# (TryExcept, NodeNG)
    """class representing a TryExcept node"""

    def _blockstart_toline(self):
        return self.lineno


class TryFinallyNG(object):# (TryFinally, NodeNG)
    """class representing a TryFinally node"""

    def _blockstart_toline(self):
        return self.lineno


class TupleNG(object):# (Tuple, StmtMixIn, NodeNG)
    """class representing a Tuple node"""


class UnaryOpNG(object):# (UnaryOp, StmtMixIn, NodeNG)
    """class representing an UnaryOp node"""


class WhileNG(object):# (While, NodeNG)
    """class representing a While node"""

    def _blockstart_toline(self):
        return self.test.tolineno


class WithNG(object):# (With, NodeNG)
    """class representing a With node"""

    def _blockstart_toline(self):
        if self.vars:
            return self.vars.tolineno
        else:
            return self.expr.tolineno


class YieldNG(object):# (Yield, NodeNG)
    """class representing a Yield node"""

