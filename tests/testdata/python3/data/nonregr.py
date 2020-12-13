

try:
    enumerate = enumerate
except NameError:

    def enumerate(iterable):
        """emulates the python2.3 enumerate() function"""
        i = 0
        for val in iterable:
            yield i, val
            i += 1

def toto(value):
    for k, v in value:
        print(v.get('yo'))


import optparse as s_opt

class OptionParser(s_opt.OptionParser):

    def parse_args(self, args=None, values=None, real_optparse=False):
        if real_optparse:
            pass
##          return super(OptionParser, self).parse_args()
        else:
            import optcomp
            optcomp.completion(self)


class Aaa(object):
    """docstring"""
    def __init__(self):
        self.__setattr__('a','b')
        pass

    def one_public(self):
        """docstring"""
        pass

    def another_public(self):
        """docstring"""
        pass

class Ccc(Aaa):
    """docstring"""

    class Ddd(Aaa):
        """docstring"""
        pass

    class Eee(Ddd):
        """docstring"""
        pass
