from .line import Line
from threading import RLock
from collections import namedtuple
import re

SizePref = namedtuple('SizePref', 'hard_min hard_max')

class Arrangement(object):

    def __init__(self, layout=None, blocks=None):
        if (layout or blocks) and not (layout and blocks):
            raise ValueError('Arrangement arguments must both exist or both not exist.')
        self._slots = {}
        self._layout = layout if layout else []
        self._index = 0
        self._load(self._layout, blocks)

    def _load(self, layout, blocks=None):
        for element in layout:
            if type(element) == int:
                if element in self._slots:
                    raise ValueError('numbers embedded in arrangement must not have duplicates')
                self._index = max(self._index, element) + 1
                self._slots[element] = blocks[element] if blocks and element in blocks else None
            elif type(element) in (list, tuple):
                if len(element) == 0:
                    raise ValueError('lists and tuples embedded in arrangement must not be empty')
                self._load(element, blocks)
            else:
                raise ValueError('arrangement must contain only list of numbers and tuples of numbers')

    def add_under(self, block):
        i = self._index
        if type(self._layout) == list:
            self._layout = tuple([self._layout, i])
        elif type(self._layout) == tuple:
            self._layout = self._layout.append(i)
        else:
            raise ValueError(type(self._layout))
        self._index += 1
    def add_right(self, block):
        i = self._index
        if type(self._layout) == list:
            self._layout.append(i)
        elif type(self._layout) == tuple:
            self._layout = [self._layout, i]
        else:
            raise ValueError(type(self._layout))
        self._index += 1

    def __repr__(self):
        return str(self._layout)

class Block(object):
    MIDDLE_DOT = u'\u00b7'
    write_lock = RLock()
    def __init__(self, name,
                 title='',
                 top_border=MIDDLE_DOT,
                 bottom_border=MIDDLE_DOT,
                 left_border=MIDDLE_DOT,
                 right_border=MIDDLE_DOT,
                 hjust='<',  # horizontoall left-justified with in block
                 vjust='^',  # vertically centered with in block
                 # The SizePrefs indicate how much screen real estate (width and height) this
                 # block desires/requires when displayed. Here, we default the block to
                 # as-much-as-you-got-but-none-is-fine.
                 w_sizepref = SizePref(hard_min=0, hard_max=float('inf')),
                 h_sizepref = SizePref(hard_min=0, hard_max=float('inf')),
                 arrangement=None):
        self.name = name
        self.title = Line('{t.normal}' + title)  # TODO why do we need this???
        self.top_border = Line(top_border)
        self.bottom_border = Line(bottom_border)
        self.left_border = Line(left_border)
        self.right_border = Line(right_border)
        if hjust not in ('<', '^', '>'):
            raise ValueError("Invalid hjust value, must be '<', '^', or '>'")
        self.hjust = hjust
        if vjust not in ('^', '=', 'v'):
            raise ValueError("Invalid vjust value, must be '^', '=', or 'v'")
        self.vjust = vjust
        self.text = None
        self.text_rows = 0
        self.text_cols = 0
        self.dirty = True
        self.dirty_event = None
        self.prev_seq = ''
        self.w_sizepref = w_sizepref
        self.h_sizepref = h_sizepref
        self.arrangement = arrangement

    def __repr__(self):
        return ('<Block {{name={0}, title={1}, len(text)={2}, lines={3}}}>'
                .format(self.name,
                        self.title.plain,
                        len(self.text) if self.text else 0,
                        len(self.text.split('\n')) if self.text else 0))

    def set_dirty_event(self, event):
        self.dirty_event = event

    def update(self, text):
        with Block.write_lock:
            if self.text != text:
                self.text = text
                rows = text.split('\n')
                clean_rows = []
                for row in rows:
                    clean_rows.append(re.sub(r'{t\..*?}', '', row))
                self.text_cols = max(map(len, clean_rows))
                if self.left_border:
                    self.text_cols += 1
                if self.right_border:
                    self.text_cols += 1
                self.text_rows = len(clean_rows)
                if self.title:
                    self.text_rows += 2
                if self.top_border:
                    self.text_rows += 1
                if self.bottom_border:
                    self.text_rows += 1
                self.dirty = True
                if self.dirty_event:
                    self.dirty_event.set()

    def _build_horiz_border(self, text, width):
        if not text:
            return None
        out = Line(text.markup * max(width, (width // len(text.markup))))
        out.resize(0, width)
        return out.display
        
    def _build_line(self, text, num_cols, width, tjust='<', padding=0, term=None):
        text_width = max(0, width - len(self.left_border.plain) - len(self.right_border.plain))
        text.resize(0, text_width)
        left_pad = ''
        if self.hjust == '^':
            left_pad = ' ' * (padding // 2)
            text_width = text_width - (padding // 2)
        elif self.hjust == '>':
            left_pad = ' ' * padding
            text_width = text_width - padding

        text_width += len(text.display) - len(text.plain)
        '''
        print("tjust        ", tjust)
        print("width        ", width)
        print("new_text     ", new_text.plain)
        print("len(new_text)", len(new_text.plain))
        print("text_width   ", text_width)
        print("left_pad     ", '*' + left_pad + '*')
        print("len(left_pad)", len(left_pad))
        print("lpad + text_width   ", text_width + len(left_pad))
        '''
        text_width += len(self.prev_seq)
        fmt = '{0}{1}{2:{3}{4}}{5}'.format(self.left_border.display if width > 0 else '',
                                           left_pad,
                                           self.prev_seq + text.display,
                                           tjust,
                                           text_width,
                                           self.right_border.display if width > 1 else '',
                                           t=term)

        self.prev_seq = text.last_seq if text.last_seq else '{t.normal}'

        return fmt

    def display(self, width, height, x, y, term=None, just_dirty=True):
        with Block.write_lock:
            self.dirty = False
            out = []
            if self.text is not None and len(self.text) != 0:
                available_for_text_rows = max(0,(height
                                                 - (1 if self.top_border else 0)
                                                 - (1 if self.bottom_border else 0)
                                                 - (2 if len(self.title.plain) else 0)))
                available_for_text_cols = max(0, (width
                                                  - len(self.left_border.plain)
                                                  - len(self.right_border.plain)))

                all_btext_rows = []
                for row in self.text.rstrip().split('\n'):
                    all_btext_rows.append(Line(row))
                usable_btext_rows = all_btext_rows[:available_for_text_rows]
            
                # Calculate the values for adjusting the text horizonally within the block
                # if there's extra space in the columns for all rows.
                max_col_len = 0
                for brow in all_btext_rows:
                    max_col_len = max(max_col_len, len(brow.plain))
                col_pad = max(0, available_for_text_cols - max_col_len)

                # Calculate the values for adjusting the text vertically within the block
                # if there's extra empty rows.
                ver_pad = max(0, (available_for_text_rows - len(all_btext_rows)))
                top_ver_pad = 0
                if self.vjust == '=':
                    top_ver_pad = ver_pad // 2
                elif self.vjust == 'v':
                    top_ver_pad = ver_pad

                # Finally, build the block from top to bottom, adding each next line
                # if there's room for it. The bottom gets cut off if there's not enough room.
                # This behavior (cutting from the bottom) is not configurable.
                line = None
                remaining_rows = height
                if self.top_border is not None and remaining_rows:
                    line = self._build_horiz_border(self.top_border, width)
                    if line:
                        out.append(line)
                        remaining_rows -= 1

                # Titles are always centered. This is not configurable.

                if len(self.title._text) and remaining_rows:
                    line = self._build_line(self.title, width, width, tjust='^', term=term)
                    if line:
                        out.append(line)
                        remaining_rows -= 1
                        line = self._build_line(Line('-' * available_for_text_cols), width, width, term=term)
                        if remaining_rows:
                            out.append(line)
                            remaining_rows -= 1

                # By default, empty rows fill out the bottom of the block.
                # Here we move some of them up above the text if we need to.
                ver_pad_count = top_ver_pad
                while ver_pad_count and remaining_rows:
                    line = self._build_line(Line(' '), available_for_text_cols, width, term=term)
                    out.append(line)
                    ver_pad_count -= 1
                    remaining_rows -= 1

                # This is the main text of the block
                for i in range(max(0,available_for_text_rows - top_ver_pad)):
                    if remaining_rows <= 0:
                        break
                    line = ''
                    if i >= len(usable_btext_rows):
                        line = self._build_line(Line(' '), width, width, term=term)
                    else:
                        line = self._build_line(usable_btext_rows[i], available_for_text_cols, width, padding=col_pad, term=term)
                    if line:
                        out.append(line)
                        remaining_rows -= 1

                # Add the bottom border
                if self.bottom_border is not None and remaining_rows:
                    line = self._build_horiz_border(self.bottom_border, width)
                    if line:
                        out.append(line)
                        remaining_rows -= 1
            if len(out):
                out[0] = '{t.normal}' + out[0]
                out[-1] += '{t.normal}'

            if term:
                for j, line in enumerate(out):
                    with term.location(x=x, y=y+j):
                        # Can debug here by printing to a file
                        try:
                            print(line.rstrip().format(t=term), end='')
                        except ValueError:
                            raise ValueError(line.rstrip())
            else:
                return out  # for testing purposes mostly

def main():
    blocks = [Block('b1'), Block('b2'), Block('b3')]
    layout = [(0,1), 2]
    arr = Arrangement(layout,blocks)
    print(arr)
    arr.add_right(Block('b4'))
    print(arr)
    arr.add_under(Block('b5'))
    print(arr)
    b1 = Block("hi", arrangement=arr)
    print(b1.arrangement)
    exit()
    import sys
    from blessed import Terminal
    
    height = int(sys.argv[1]) if len(sys.argv) > 2 else 10    
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    term = Terminal()
    
    block = Block("me", left_border='*', right_border="x",  top_border='a', bottom_border='z', title="This is it.", hjust='>')
    block.update('hi\nthere\nyou\n01}23{}{4567890\n\n6th\n7th\n8\n9\n10')
    lines = block.display(width,height,0,0)
    for line in lines:
        print(line.format(t=term))

    block = Block("you", left_border='*', right_border="x",  top_border='a', bottom_border='z', title="This is it.", hjust='>')
    block.update('hi\nthe{t.yellow}re\nyo}{u\n{t.blue}0123{t.red}4567890\n\n6th\n7th{t.normal}x\n8\n9\n10')
    lines = block.display(width,height,0,0,term=None)
    for line in lines:
        print(line.format(t=term))

    block = Block("you", left_border='*', right_border="x",  top_border='a', bottom_border='z', title="This is it.", hjust='>')
    block.update('the{t.yellow}s{}e')
    lines = block.display(width,height,0,0)
    for line in lines:
        print(line.format(t=term))

if __name__ == '__main__':
    main()
