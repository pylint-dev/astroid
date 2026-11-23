class Future:
    attr = 1

class Present(Future):
    pass

class Past(Present):  # getattr(attr): AssignName(attr)
    pass
