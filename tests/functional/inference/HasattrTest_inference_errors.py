from missing import Missing

hasattr(Unknown, 'ala')  # inferred: Uninferable

hasattr(Missing, 'bala')  # inferred: Uninferable
hasattr('portocala', Missing)  # inferred: Uninferable
