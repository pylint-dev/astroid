# Assigned_stmts for MatchMapping not yet implemented.
#
# Test the result is 'Uninferable' and no exception is raised.
var = {1: "Hello", 2: "World"}
match var:
    case {**rest}:  # pattern.rest: AssignName(rest)  # pattern.rest.assigned_stmts(): Uninferable
        pass
