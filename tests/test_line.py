import pytest

from blessedblocks.line import Line

def test_line():
    line = Line("some text")
    assert line.plain == "some text"

    
