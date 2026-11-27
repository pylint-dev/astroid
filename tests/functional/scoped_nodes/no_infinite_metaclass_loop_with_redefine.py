import datetime

class A(datetime.date):  # metaclass: None
    @classmethod
    def now(cls):
        return cls()

class B(datetime.date):  # metaclass: None
    pass

datetime.date = A
datetime.date = B
