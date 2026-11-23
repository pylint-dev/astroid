# Assigned_stmts for MatchStar not yet implemented.
#
# Test the result is 'Uninferable' and no exception is raised.
var = (0, 1, 2)
match var:
    # +3: pattern.patterns[2]: MatchStar(*rest)
    # +2: pattern.patterns[2].name: AssignName(rest)
    # +1: pattern.patterns[2].name.assigned_stmts(): Uninferable
    case (0, 1, *rest):
        pass
