from .line import Line
from .block import Block, SizePref, Grid, safe_get,safe_set
import re

class VFillBlock(Block):
    def __init__(self, text):
        border_text, seqs, last_seq = Line.parse(text)
        super().__init__(text=text, w_sizepref=SizePref(hard_min=len(border_text),
                                                        hard_max=len(border_text)))

    def display(self, width, height, x, y, term=None):
        with self.write_lock:
            border_text, seqs, last_seq = Line.parse(self.text)
            out = []
            line = Line(self.text, width, '<')
            for h in range(height):
                if term:
                    with term.location(x=x, y=y+h):
                        print(line.display.format(t=term), end='')
                else:
                    out.append(line.display)
            if not term:
                return out

class HFillBlock(Block):
    def __init__(self, text):
        maxes = 0 if not text else 1  # Don't take up space if there's no text
        super().__init__(text=text, h_sizepref=SizePref(hard_min=maxes, hard_max='text'))

    def display(self, width, height, x, y, term=None):
        if not self.text:
            if not term:
                return []
            return

        with self.write_lock:
            text = Line.repeat_to_width(self.text, width).display

            if term:
                with term.location(x=x, y=y):
                    print(text.format(t=term), end='')
            else:
                return [text]  # for testing purposes only

class BareBlock(Block):
    def __init__(self,
                 text=None,
                 hjust='<',  # horizontally left-justified within block
                 vjust='^',  # vertically centered within block
                 block_just=True,  # justify block as a whole vs line-by-line
                 # The SizePrefs indicate how much screen real estate (width and height) this
                 # block desires/requires when displayed. Here, we default the block to
                 # as-much-as-you-got-but-none-is-fine.
                 w_sizepref = SizePref(hard_min=0, hard_max=float('inf')),
                 h_sizepref = SizePref(hard_min=0, hard_max=float('inf')),
                 grid=None):
        super().__init__(text=text, hjust=hjust, vjust=vjust, block_just=block_just,
                         w_sizepref=w_sizepref, h_sizepref=h_sizepref, grid=grid)
        self._prev_seq = '{t.normal}'

    def display(self, width, height, x, y, term=None):
        with self.write_lock:
            out = []
            if self.text is not None and len(self.text) != 0:
                available_for_text_rows = max(0, height)
                available_for_text_cols = max(0, width)

                all_btext_rows = []
                for row in self.text.split('\n'):
                    all_btext_rows.append(row)  # TODO all we really need is a count here, right?
                useable_btext_rows = all_btext_rows[:available_for_text_rows]

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

                # By default, empty rows fill out the bottom of the block.
                # Here we move some of them up above the text if we need to.
                ver_pad_count = top_ver_pad
                while ver_pad_count and remaining_rows:
                    line = Line(' ' * width, width, self.hjust)
                    out.append(line)
                    ver_pad_count -= 1
                    remaining_rows -= 1

                # This is the main text of the block
                prev_seq = '{t.normal}'                
                for i in range(max(0,available_for_text_rows - top_ver_pad)):
                    if remaining_rows <= 0:
                        break
                    line = None
                    if i >= len(useable_btext_rows):
                        line = Line(prev_seq + ' ', width, self.hjust)
                    else:
                        line = Line(prev_seq + useable_btext_rows[i], width, self.hjust)
                    if line:
                        out.append(line)
                        prev_seq = line.last_seq
                        remaining_rows -= 1

            if len(out):
                out[-1].display += '{t.normal}'

            if term:
                for j, line in enumerate(out):
                    with term.location(x=x, y=y+j):
                        # Can debug here by printing to a file
                        #with open('/tmp/bare', 'a') as f:
                        #    f.write(line.display + '\n')
                            
                        try:
                            text = re.sub(r"\r?\n?$", "", line.display, 1)
                            print(text.format(t=term), end='')
                        except ValueError:
                            raise ValueError(line.rstrip())
                term.move(term.height, term.width)  # TODO This doesn't work
            else:
                return [line.display for line in out]  # for testing purposes only

class FramedBlock(Block):
    LEFT_BORDER = 1
    TOP_BORDER = 2
    TITLE = 3
    TITLE_SEP = 4
    TEXT = 5
    BOTTOM_BORDER = 6
    RIGHT_BORDER = 7
    def __init__(self,
                 block,
                 no_borders=False,
                 top_border=Block.MIDDLE_DOT,
                 bottom_border=Block.MIDDLE_DOT,
                 left_border=Block.MIDDLE_DOT,
                 right_border=Block.MIDDLE_DOT,
                 title = '',
                 title_sep = ''):

        top_border = '' if no_borders and top_border == Block.MIDDLE_DOT else top_border
        bottom_border = None if no_borders and bottom_border == Block.MIDDLE_DOT else bottom_border
        left_border = '' if no_borders and left_border == Block.MIDDLE_DOT else left_border
        right_border = '' if no_borders and right_border == Block.MIDDLE_DOT else right_border

        layout = [1,(2,3,4,5,6),7]

        blocks = {}
        blocks[1] = VFillBlock(left_border)
        blocks[2] = HFillBlock(top_border)
        blocks[3] = BareBlock(text=title, hjust='^', vjust='^',
                              h_sizepref = SizePref(hard_min=1, hard_max=1))
        blocks[4] = HFillBlock(title_sep)
        # Use the block's sizepref's for our own (we're just framing it),
        # and assign the block the default size prefs, so the frame dominates.
        w_sizepref = block.w_sizepref
        h_sizepref = block.h_sizepref
        block.w_sizepref = SizePref(hard_min=0, hard_max=float('inf'))
        block.h_sizepref = SizePref(hard_min=0, hard_max=float('inf'))
        blocks[5] = block
        blocks[6] = HFillBlock(bottom_border)
        blocks[7] = VFillBlock(right_border)

        super().__init__(None,
                         hjust='^',
                         vjust='^',
                         block_just=True,
                         w_sizepref=w_sizepref,
                         h_sizepref=h_sizepref,
                         grid = Grid(layout, blocks))
        self.no_borders = no_borders
        self.top_border = top_border
        self.bottom_border = bottom_border
        self.left_border = left_border
        self.right_border = right_border

    @property
    @safe_get
    def no_borders(self): return self._no_borders

    @no_borders.setter
    @safe_set
    def no_borders(self, val):
        self._no_borders = val

    @property
    @safe_get
    def top_border(self): return self._top_border

    @top_border.setter
    @safe_set
    def top_border(self, val):
        self._top_border = val

    @property
    @safe_get
    def bottom_border(self): return self._bottom_border

    @bottom_border.setter
    @safe_set
    def bottom_border(self, val):
        self._bottom_border = val

    @property
    @safe_get
    def left_border(self): return self._left_border

    @left_border.setter
    @safe_set
    def left_border(self, val):
        self._left_border = val

    @property
    @safe_get
    def right_border(self): return self._right_border

    @right_border.setter
    @safe_set
    def right_border(self, val):
        self._right_border = val

    def display(self, width, height, x, y, term=None):
        raise NotImplementedError("Blocks with grids don't implement display method")
