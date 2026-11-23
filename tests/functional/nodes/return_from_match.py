def return_from_match(x):
    match x:
        case 10:
            return 10
        case _:
            return -1

return_from_match(10)  # inferred: Const(-1) | Const(10)
