import pytest
from blessedblocks.line import Line
from blessedblocks.block import Grid, SizePref
from blessedblocks.bare_block import BareBlock
from blessedblocks.runner import Runner, Plot
from blessed import Terminal

term = Terminal()

# Function under test:
# def divvy(self, plots, x, y, w, h, horizontal):

def test_divvy():
    layout = [1]
    blocks = {}
    main = BareBlock('abc123', hjust='^',
                     w_sizepref = SizePref(hard_min=1, hard_max=1))
    two = BareBlock('xyz456', hjust='^',
                    w_sizepref = SizePref(hard_min=1, hard_max=1))
    
    blocks[1] = main
    blocks[2] = two
    
    g = Grid(layout, blocks)
    top = BareBlock(grid=g)
    r = Runner(top)
    print(Runner.divvy([r._plot], 0, 0, 10, 10, True))
    
    
    
