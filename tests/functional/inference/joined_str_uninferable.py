# `thing` is not known, therefore the joinedstring should be
# Uninferable
def hey(thing):
    return thing

# +3: inferred: Uninferable
# +2: values[0].value: 'Hello '
# +1: values[1].value.as_string(): hey()
f"Hello {hey()}"
