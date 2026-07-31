# Licensed under the LGPL: https://www.gnu.org/licenses/old-licenses/lgpl-2.1.en.html
# For details: https://github.com/pylint-dev/astroid/blob/main/LICENSE
# Copyright (c) https://github.com/pylint-dev/astroid/blob/main/CONTRIBUTORS.txt

"""Tests for the wave module brain."""

from astroid import builder, nodes
from astroid.bases import Instance


class TestWaveBrain:
    def test_wave_open_write_mode(self) -> None:
        """wave.open with a write mode returns a Wave_write instance."""
        node = builder.extract_node("""
        import wave
        f = wave.open("blank.wav", "wb")
        f #@
        """)
        inferred = next(node.infer())
        assert isinstance(inferred, Instance)
        assert inferred.qname() == "wave.Wave_write"
        assert "writeframes" in inferred.locals

    def test_wave_open_read_mode(self) -> None:
        """wave.open with a read mode returns a Wave_read instance."""
        node = builder.extract_node("""
        import wave
        f = wave.open("blank.wav", "rb")
        f #@
        """)
        inferred = next(node.infer())
        assert isinstance(inferred, Instance)
        assert inferred.qname() == "wave.Wave_read"

    def test_wave_open_mode_keyword(self) -> None:
        """wave.open accepts the mode as a keyword argument."""
        node = builder.extract_node("""
        import wave
        f = wave.open("blank.wav", mode="w")
        f #@
        """)
        inferred = next(node.infer())
        assert isinstance(inferred, Instance)
        assert inferred.qname() == "wave.Wave_write"

    def test_wave_open_write_attributes(self) -> None:
        """Wave_write methods are available on the inferred instance."""
        node = builder.extract_node("""
        import wave
        f = wave.open("blank.wav", "wb")
        f.setnchannels(1)
        f.writeframes(b"data") #@
        """)
        inferred = next(node.infer())
        assert isinstance(inferred, nodes.Const)

    def test_wave_open_inferred_mode(self) -> None:
        """The mode is propagated through function arguments."""
        node = builder.extract_node("""
        import wave
        def write(mode):
            f = wave.open("blank.wav", mode)
            return f
        write("wb") #@
        """)
        inferred = next(node.infer())
        assert isinstance(inferred, Instance)
        assert inferred.qname() == "wave.Wave_write"
