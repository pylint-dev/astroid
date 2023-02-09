# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

from __future__ import annotations

import unittest

from astroid import builder

try:
    import dateutil  # pylint: disable=unused-import

    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


@unittest.skipUnless(HAS_DATEUTIL, "This test requires the dateutil library.")
class DateutilBrainTest(unittest.TestCase):
    def test_parser(self):
        module = builder.parse(
            """
        from dateutil.parser import parse
        d = parse('2000-01-01')
        """
        )
        d_type = next(module["d"].infer())
        self.assertEqual(d_type.qname(), "datetime.datetime")
