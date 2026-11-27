def run2():  # lookup('Frobbel')[1]: []
    f = Frobble()

class Frobble:
    pass
Frobble.mumble = True

del Frobble

def run1():  # lookup('Frobbel')[1]: []
    f = Frobble()
