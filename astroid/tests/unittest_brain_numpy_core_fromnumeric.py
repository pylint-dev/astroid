# -*- encoding=utf-8 -*-
# Copyright (c) 2017-2018 hippo91 <guillaume.peillex@gmail.com>

# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/master/COPYING.LESSER
import unittest
import contextlib

try:
    import numpy  # pylint: disable=unused-import

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from astroid import builder


class SubTestWrapper(unittest.TestCase):
    """
    A class for supporting all unittest version wether or not subTest is available
    """

    def subTest(self, msg=None, **params):
        try:
            # For python versions above 3.5 this should be ok
            return super(SubTestWrapper, self).subTest(msg, **params)
        except AttributeError:
            #  For python versions below 3.5
            return subTestMock(msg)


@contextlib.contextmanager
def subTestMock(msg=None):
    """
    A mock for subTest which do nothing
    """
    yield msg


@unittest.skipUnless(HAS_NUMPY, "This test requires the numpy library.")
class BrainNumpyCoreFromNumericTest(SubTestWrapper):
    """
    Test the numpy core fromnumeric brain module
    """

    numpy_functions = (("sum", "[1, 2]"),)

    def _inferred_numpy_func_call(self, func_name, *func_args):
        node = builder.extract_node(
            """
        import numpy as np
        func = np.{:s}
        func({:s})
        """.format(
                func_name, ",".join(func_args)
            )
        )
        return node.infer()

    def test_numpy_function_calls_inferred_as_ndarray(self):
        """
        Test that calls to numpy functions are inferred as numpy.ndarray
        """
        licit_array_types = (".ndarray",)
        for func_ in self.numpy_functions:
            with self.subTest(typ=func_):
                inferred_values = list(self._inferred_numpy_func_call(*func_))
                self.assertTrue(
                    len(inferred_values) == 1,
                    msg="Too much inferred value for {:s}".format(func_[0]),
                )
                self.assertTrue(
                    inferred_values[-1].pytype() in licit_array_types,
                    msg="Illicit type for {:s} ({})".format(
                        func_[0], inferred_values[-1].pytype()
                    ),
                )


if __name__ == "__main__":
    unittest.main()
