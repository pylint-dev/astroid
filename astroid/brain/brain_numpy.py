# Copyright (c) 2015-2016 Claudiu Popa <pcmanticore@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER


"""Astroid hooks for numpy."""

import astroid


# TODO(cpopa): drop when understanding augmented assignments

def numpy_core_transform():
    return astroid.parse('''
    from numpy.core.numerictypes import (sctypeDict, sctypeNA, typeDict,
        typeNA, sctypes, ScalarType, obj2sctype, cast, nbytes, sctype2char,
        maximum_sctype, issctype, typecodes, find_common_type, issubdtype,
        datetime_data, datetime_as_string, busday_offset, busday_count,
        is_busday, busdaycalendar, complex_, clongfloat, uintp, intc, int32,
        unsignedinteger, longdouble, bool8, number, object0, single, complex64,
        intp, complexfloating, float128, floating, int16, cfloat, uint0, float16,
        uintc, ulonglong, longcomplex, generic, datetime64, int_, cdouble, character,
        complex128, csingle, uint16, flexible, ubyte, longfloat, uint32, string0,
        unicode_, longlong, complex256, str_, void, inexact, uint8, string_, unicode0,
        uint, int0, half, integer, byte, int8, void0, uint64, short, bool_, float64,
        timedelta64, double, ushort, float32, float_, int64, clongdouble,
        singlecomplex, signedinteger, bytes_, object_)
    ''')

astroid.register_module_extender(astroid.MANAGER, 'numpy.core', numpy_core_transform)
