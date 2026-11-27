class Super(object):
    def __init__(self):
        # +3: inferred: Super
        # +2: inferred._proxied: ClassDef(builtins.super)
        # +1: inferred._proxied.qname(): 'builtins.super'
        super(Super, self)
