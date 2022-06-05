# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/PyCQA/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/PyCQA/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for the ssl brain."""

from astroid import bases, nodes, parse


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
