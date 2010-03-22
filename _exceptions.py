# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# this program; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
"""this module contains exceptions used in the astng library

:author:    Sylvain Thenault
:copyright: 2003-2010 LOGILAB S.A. (Paris, FRANCE)
:contact:   http://www.logilab.fr/ -- mailto:python-projects@logilab.org
:copyright: 2003-2010 Sylvain Thenault
:contact:   mailto:thenault@gmail.com
"""

__doctype__ = "restructuredtext en"

class ASTNGError(Exception):
    """base exception class for all astng related exceptions"""

class ASTNGBuildingException(ASTNGError):
    """exception class when we are unable to build an astng representation"""

class ResolveError(ASTNGError):
    """base class of astng resolution/inference error"""

class NotFoundError(ResolveError):
    """raised when we are unable to resolve a name"""

class InferenceError(ResolveError):
    """raised when we are unable to infer a node"""

class UnresolvableName(InferenceError):
    """raised when we are unable to resolve a name"""

class NoDefault(ASTNGError):
    """raised by function's `default_value` method when an argument has
    no default value
    """

class IgnoreChild(Exception):
    """exception that maybe raised by visit methods to avoid children traversal
    """

