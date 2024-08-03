# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for the ssl brain."""

import pytest

from astroid import bases, nodes, parse
from astroid.const import PY312_PLUS


def test_ssl_brain() -> None:
    """Test ssl brain transform."""
    module = parse(
        """
    import ssl
    ssl.PROTOCOL_TLSv1
    ssl.VerifyMode
    ssl.TLSVersion
    ssl.VerifyMode.CERT_REQUIRED
    """
    )
    inferred_protocol = next(module.body[1].value.infer())
    assert isinstance(inferred_protocol, nodes.Const)

    inferred_verifymode = next(module.body[2].value.infer())
    assert isinstance(inferred_verifymode, nodes.ClassDef)
    assert inferred_verifymode.name == "VerifyMode"
    assert len(inferred_verifymode.bases) == 1

    # Check that VerifyMode correctly inherits from enum.IntEnum
    int_enum = next(inferred_verifymode.bases[0].infer())
    assert isinstance(int_enum, nodes.ClassDef)
    assert int_enum.name == "IntEnum"
    assert int_enum.parent.name == "enum"

    # TLSVersion is inferred from the main module, not from the brain
    inferred_tlsversion = next(module.body[3].value.infer())
    assert isinstance(inferred_tlsversion, nodes.ClassDef)
    assert inferred_tlsversion.name == "TLSVersion"

    # TLSVersion is inferred from the main module, not from the brain
    inferred_cert_required = next(module.body[4].value.infer())
    assert isinstance(inferred_cert_required, bases.Instance)
    assert inferred_cert_required._proxied.name == "CERT_REQUIRED"


@pytest.mark.skipif(not PY312_PLUS, reason="Uses new 3.12 constant")
def test_ssl_brain_py312() -> None:
    """Test ssl brain transform."""
    module = parse(
        """
    import ssl
    ssl.OP_LEGACY_SERVER_CONNECT
    ssl.Options.OP_LEGACY_SERVER_CONNECT
    """
    )

    inferred_constant = next(module.body[1].value.infer())
    assert isinstance(inferred_constant, nodes.Const)

    inferred_instance = next(module.body[2].value.infer())
    assert isinstance(inferred_instance, bases.Instance)
