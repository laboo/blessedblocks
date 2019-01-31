from .block import Block, SizePref, Grid
from .vfill_block import VFillBlock
from .hfill_block import HFillBlock
from .bare_block import BareBlock
from .block import safe_get,safe_set
from .line import Line

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
