import pytest

from blessedblocks.line import Line

def test_simple():
    line = Line('simple line of text')
    assert line.plain == 'simple line of text'
    assert line.markup == line.plain
    # {t.normal} always appended to the end of display
    assert line.display == line.plain + '{t.normal}'
    assert line.last_seq is None

def test_just_tag():
    text = '{t.green}'
    line = Line(text)
    assert line.plain == ''
    assert line.markup == '{t.green}'
    assert line.display == '{t.green}{t.normal}'
    assert line.last_seq == '{t.green}'

def test_two_trailing_tags():
    # green is irrelevant, so dropped from markup and display
    text = '{t.green}{t.blue}'
    line = Line(text)
    assert line.plain == ''
    assert line.markup == '{t.blue}'
    assert line.display == '{t.blue}{t.normal}'
    assert line.last_seq == '{t.blue}'

def test_two_trailing_tags_with_text():
    # green is irrelevant, so dropped from markup and display
    text = 'abc{t.green}{t.blue}'
    line = Line(text)
    assert line.plain == 'abc'
    assert line.markup == 'abc{t.blue}'
    assert line.display == 'abc{t.blue}{t.normal}'
    assert line.last_seq == '{t.blue}'

def test_complex():
    text = '{t.green}{}{}}{blac{t.yellow}k justp{t.cyan}laintext{t.pink}x'
    line = Line(text)
    # tags removed,and { and } doubled when not in tag
    assert line.plain == '{}{}}{black justplaintextx'

    assert line.markup == text
    # { and } doubled when not part of tag, and end with normal
    assert line.display == '{t.green}{{}}{{}}}}{{blac{t.yellow}k justp{t.cyan}laintext{t.pink}x{t.normal}'
    assert line.last_seq == '{t.pink}'

def test_complex_ends_in_non_normal_tag():
    text = '{t.green}{}{}}{blac{t.yellow}k justp{t.cyan}laintext{t.pink}'
    line = Line(text)
    # tags removed,and { and } doubled when not in tag
    assert line.plain == '{}{}}{black justplaintext'
    # Useless tags at end of markup are removed
    assert line.markup == text
    # { and } doubled when not part of tag, and end with normal
    assert line.display == '{t.green}{{}}{{}}}}{{blac{t.yellow}k justp{t.cyan}laintext{t.pink}{t.normal}'
    assert line.last_seq == '{t.pink}'
    
def test_broken_tag_front():
    text = 't.green}xyz'
    line = Line(text)
    assert line.plain == text
    assert line.markup == text
    assert line.display == 't.green}}xyz{t.normal}'  # non-tag brackets doubled in display
    assert line.last_seq is None

def test_last_sequence_normal():
    text = 'hi there, {t.red}Red{t.normal}!'
    line = Line(text)
    assert line.plain == 'hi there, Red!'
    assert line.markup == text
    assert line.display == text  # already ends in normal
    assert line.last_seq == '{t.normal}'
