# -*- coding: Latin-1 -*-
# copyright 2003-2010 LOGILAB S.A. (Paris, FRANCE), all rights reserved.
# contact http://www.logilab.fr/ -- mailto:contact@logilab.fr
# copyright 2003-2010 Sylvain Thenault, all rights reserved.
# contact mailto:thenault@gmail.com
#
# This file is part of logilab-astng.
#
# logilab-astng is free software: you can redistribute it and/or modify it
# under the terms of the GNU Lesser General Public License as published by the
# Free Software Foundation, either version 2.1 of the License, or (at your
# option) any later version.
#
# logilab-astng is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License
# for more details.
#
# You should have received a copy of the GNU Lesser General Public License along
# with logilab-astng. If not, see <http://www.gnu.org/licenses/>.
"""test module for astng
"""

__revision__ = '$Id: module.py,v 1.2 2005-11-02 11:56:54 syt Exp $'

from logilab.common import modutils
from logilab.common.shellutils import Execute as spawn
from logilab.astng.utils import *
import os.path

MY_DICT = {}


def global_access(key, val):
    """function test"""
    local = 1
    MY_DICT[key] = val
    for i in val:
        if i:
            del MY_DICT[i]
            continue
        else:
            break
    else:
        print '!!!'

class YO:
    """hehe"""
    a=1
    def __init__(self):
        try:
            self.yo = 1
        except ValueError, ex:
            pass
        except (NameError, TypeError):
            raise XXXError()
        except:
            raise
        
#print '*****>',YO.__dict__    
class YOUPI(YO):
    class_attr = None
    
    def __init__(self):
        self.member = None

    def method(self):
        """method test"""
        global MY_DICT
        try:
            MY_DICT = {}
            local = None
            autre = [a for a, b in MY_DICT if b]
            if b in autre:
                print 'yo',
            elif a in autre:
                print 'hehe'
            global_access(local, val=autre)
        finally:
            return local

    def static_method():
        """static method test"""
        assert MY_DICT, '???'
    static_method = staticmethod(static_method)
    
    def class_method(cls):
        """class method test"""
        exec a in b
    class_method = classmethod(class_method)
        

def nested_args(a, (b, c, d)):
    """nested arguments test"""
    print a, b, c, d
    while 1:
        if a:
            break
        a += +1
    else:
        b += -2
    if c:
        d = a and b or c
    else:
        c = a and b or d
    map(lambda x, y: (y, x), a)
    
redirect = nested_args

