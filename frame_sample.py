#!/usr/bin/python3
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "blessedblocks"))
# Previous two lines not needed if blessedblocks modules is installed
from blessedblocks.bare_block import BareBlock
from blessedblocks.framed_block import FramedBlock
from blessedblocks.block import Grid, SizePref
from blessedblocks.runner import Runner
from blessedblocks.line import Line
from threading import Event, Thread, Lock
from tabulate import tabulate
import datetime
from blessed import Terminal

term = Terminal()
layout = [1]
blocks = {}
main = BareBlock('abc123', hjust='^', vjust='=',
                 w_sizepref = SizePref(hard_min=1, hard_max=1),
                 h_sizepref = SizePref(hard_min=1, hard_max=1))

blocks[1] = FramedBlock(main,
                        top_border='{t.blue}x',
                        bottom_border='{t.blue}y',
                        left_border='{t.red}z',
                        right_border='{t.green}a',
                        title='My Title',
                        title_sep='{t.cyan}-')

g = Grid(layout, blocks)
top = BareBlock(grid=g)
r = Runner(top)
r.start()


