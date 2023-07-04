# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import unittest
from typing import ClassVar

try:
    import numpy  # pylint: disable=unused-import

    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

from astroid import builder, nodes


@unittest.skipUnless(HAS_NUMPY, "This test requires the numpy library.")
class NumpyBrainRandomMtrandTest(unittest.TestCase):
    """Test of all the functions of numpy.random.mtrand module."""

    # Map between functions names and arguments names and default values
    all_mtrand: ClassVar[dict[str, tuple]] = {
        "beta": (["a", "b", "size"], [None]),
        "binomial": (["n", "p", "size"], [None]),
        "bytes": (["length"], []),
        "chisquare": (["df", "size"], [None]),
        "choice": (["a", "size", "replace", "p"], [None, True, None]),
        "dirichlet": (["alpha", "size"], [None]),
        "exponential": (["scale", "size"], [1.0, None]),
        "f": (["dfnum", "dfden", "size"], [None]),
        "gamma": (["shape", "scale", "size"], [1.0, None]),
        "geometric": (["p", "size"], [None]),
        "get_state": ([], []),
        "gumbel": (["loc", "scale", "size"], [0.0, 1.0, None]),
        "hypergeometric": (["ngood", "nbad", "nsample", "size"], [None]),
        "laplace": (["loc", "scale", "size"], [0.0, 1.0, None]),
        "logistic": (["loc", "scale", "size"], [0.0, 1.0, None]),
        "lognormal": (["mean", "sigma", "size"], [0.0, 1.0, None]),
        "logseries": (["p", "size"], [None]),
        "multinomial": (["n", "pvals", "size"], [None]),
        "multivariate_normal": (["mean", "cov", "size"], [None]),
        "negative_binomial": (["n", "p", "size"], [None]),
        "noncentral_chisquare": (["df", "nonc", "size"], [None]),
        "noncentral_f": (["dfnum", "dfden", "nonc", "size"], [None]),
        "normal": (["loc", "scale", "size"], [0.0, 1.0, None]),
        "pareto": (["a", "size"], [None]),
        "permutation": (["x"], []),
        "poisson": (["lam", "size"], [1.0, None]),
        "power": (["a", "size"], [None]),
        "rand": (["args"], []),
        "randint": (["low", "high", "size", "dtype"], [None, None, "l"]),
        "randn": (["args"], []),
        "random": (["size"], [None]),
        "random_integers": (["low", "high", "size"], [None, None]),
        "random_sample": (["size"], [None]),
        "rayleigh": (["scale", "size"], [1.0, None]),
        "seed": (["seed"], [None]),
        "set_state": (["state"], []),
        "shuffle": (["x"], []),
        "standard_cauchy": (["size"], [None]),
        "standard_exponential": (["size"], [None]),
        "standard_gamma": (["shape", "size"], [None]),
        "standard_normal": (["size"], [None]),
        "standard_t": (["df", "size"], [None]),
        "triangular": (["left", "mode", "right", "size"], [None]),
        "uniform": (["low", "high", "size"], [0.0, 1.0, None]),
        "vonmises": (["mu", "kappa", "size"], [None]),
        "wald": (["mean", "scale", "size"], [None]),
        "weibull": (["a", "size"], [None]),
        "zipf": (["a", "size"], [None]),
    }

    def _inferred_numpy_attribute(self, func_name):
        node = builder.extract_node(
            f"""
        import numpy.random.mtrand as tested_module
        func = tested_module.{func_name:s}
        func"""
        )
        return next(node.infer())

    def test_numpy_random_mtrand_functions(self):
        """Test that all functions have FunctionDef type."""
        for func in self.all_mtrand:
            with self.subTest(func=func):
                inferred = self._inferred_numpy_attribute(func)
                self.assertIsInstance(inferred, nodes.FunctionDef)

    def test_numpy_random_mtrand_functions_signature(self):
        """Test the arguments names and default values."""
        for (
            func,
            (exact_arg_names, exact_kwargs_default_values),
        ) in self.all_mtrand.items():
            with self.subTest(func=func):
                inferred = self._inferred_numpy_attribute(func)
                self.assertEqual(inferred.argnames(), exact_arg_names)
                default_args_values = [
                    default.value for default in inferred.args.defaults
                ]
                self.assertEqual(default_args_values, exact_kwargs_default_values)
