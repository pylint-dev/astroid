
from logilab.astng import nodes
from logilab.astng import MANAGER, YES, ASTNGError, InferenceError, \
     NotFoundError, Instance, path_wrapper

nodes.Const.__bases__ += (Instance,)
nodes.Const._proxied = None
def Const___getattr__(self, name):
    if self.value is None:
        raise AttributeError(name)
    if self._proxied is None:
        self._proxied = MANAGER.astng_from_class(self.value.__class__)
    return getattr(self._proxied, name)
nodes.Const.__getattr__ = Const___getattr__
def Const_getattr(self, name, context=None, lookupclass=None):
    if self.value is None:
        raise NotFoundError(name)
    if self._proxied is None:
        self._proxied = MANAGER.astng_from_class(self.value.__class__)
    return self._proxied.getattr(name, context)
nodes.Const.getattr = Const_getattr
nodes.Const.has_dynamic_getattr = lambda x: False

def Const_pytype(self):
    if self.value is None:
        return '__builtin__.NoneType'
    if self._proxied is None:
        self._proxied = MANAGER.astng_from_class(self.value.__class__)
    return self._proxied.qname()
nodes.Const.pytype = Const_pytype


nodes.Const.infer = nodes.infer_end

def infer_empty_node(self, context=None):
    if not self.has_underlying_object():
        yield YES
    else:
        try:
            for infered in MANAGER.infer_astng_from_something(self.object,
                                                              context=context):
                yield infered
        except ASTNGError:
            yield YES
nodes.EmptyNode.infer = path_wrapper(infer_empty_node)


def infer_assname(self, context=None):
    """infer a AssName/AssAttr: need to inspect the RHS part of the
    assign node
    """
    stmts = self.assigned_stmts(context=context)
    return nodes._infer_stmts(stmts, context)
nodes.AssName.infer = path_wrapper(infer_assname)


def infer_assattr(self, context=None):
    """infer a AssName/AssAttr: need to inspect the RHS part of the
    assign node
    """
    stmts = self.assigned_stmts(context=context)
    return nodes._infer_stmts(stmts, context)
nodes.AssAttr.infer = path_wrapper(infer_assattr)


def infer_getattr(self, context=None):
    """infer a Getattr node by using getattr on the associated object
    """
    one_infered = False
    # XXX
    #context = context.clone()
    for owner in self.expr.infer(context):
        if owner is YES:
            yield owner
            one_infered = True
            continue
        try:
            context.boundnode = owner
            for obj in owner.igetattr(self.attrname, context):
                yield obj
                one_infered = True
            context.boundnode = None
        except (NotFoundError, InferenceError):
            continue
        except AttributeError:
            # XXX method / function
            continue
    if not one_infered:
        raise InferenceError()
nodes.Getattr.infer = path_wrapper(infer_getattr)


def assend_assigned_stmts(self, context=None):
    # only infer *real* assignments
    if self.flags == 'OP_DELETE':
        raise InferenceError()
    return self.parent.assigned_stmts(self, context=context)    
nodes.AssName.assigned_stmts = assend_assigned_stmts
nodes.AssAttr.assigned_stmts = assend_assigned_stmts


def mulass_assigned_stmts(self, node, context=None, asspath=None):
    if asspath is None:
        asspath = []
    node_idx = self.nodes.index(node)
    asspath.insert(0, node_idx)
    return self.parent.assigned_stmts(self, context, asspath)
nodes.AssTuple.assigned_stmts = mulass_assigned_stmts
nodes.AssList.assigned_stmts = mulass_assigned_stmts


def _resolve_looppart(parts, asspath, context):
    """recursive function to resolve multiple assignments on loops"""
    asspath = asspath[:]
    index = asspath.pop(0)
    for part in parts:
        if part is YES:
            continue
        if not hasattr(part, 'iter_stmts'):
            continue
        for stmt in part.iter_stmts():
            try:
                assigned = stmt.getitem(index)
            except (AttributeError, IndexError):
                continue
            if not asspath:
                # we acheived to resolved the assigment path,
                # don't infer the last part
                found = True
                yield assigned
            elif assigned is YES:
                break
            else:
                # we are not yet on the last part of the path
                # search on each possibly infered value
                try:
                    for infered in _resolve_looppart(assigned.infer(context), asspath, context):
                        yield infered
                except InferenceError:
                    break

def for_assigned_stmts(self, node, context=None, asspath=None):
    found = False
    if asspath is None:
        for lst in self.loop_node().infer(context):
            if isinstance(lst, (nodes.Tuple, nodes.List)):
                for item in lst.nodes:
                    found = True
                    yield item
    else:
        for infered in _resolve_looppart(self.loop_node().infer(context), asspath, context):
            found = True
            yield infered
    if not found:
        raise InferenceError()
nodes.For.assigned_stmts = for_assigned_stmts
nodes.ListCompFor.assigned_stmts = for_assigned_stmts
nodes.GenExprFor.assigned_stmts = for_assigned_stmts

nodes.ListCompFor.ass_type = nodes.end_ass_type
nodes.GenExprFor.ass_type = nodes.end_ass_type
def parent_ass_type(self):
    return self.parent.ass_type()
nodes.AssName.ass_type = parent_ass_type
nodes.AssAttr.ass_type = parent_ass_type
nodes.AssTuple.ass_type = parent_ass_type
nodes.AssList.ass_type = parent_ass_type
def assend_ass_type(self, context=None):
    # only infer *real* assignments
    if self.flags == 'OP_DELETE':
        return self
    return self.parent.ass_type()
nodes.AssName.ass_type = assend_ass_type
nodes.AssAttr.ass_type = assend_ass_type



def for_loop_node(self):
    return self.list
nodes.ListCompFor.loop_node = for_loop_node

def gen_loop_nodes(self):
    return self.iter
nodes.GenExprFor.loop_node = gen_loop_nodes
