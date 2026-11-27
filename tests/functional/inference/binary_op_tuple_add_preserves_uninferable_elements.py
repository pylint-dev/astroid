from missing import Unknown

# +1: inferred: Tuple(Unknown(Unknown.Unknown()), Const(1), Const(2), Unknown(Unknown.Unknown()))
(Unknown, 1) + (2, Unknown)
