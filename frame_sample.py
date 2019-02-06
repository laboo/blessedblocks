#!/usr/bin/python3
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "blessedblocks"))
# Previous two lines not needed if blessedblocks modules is installed
from blessedblocks.block import Grid, SizePref
from blessedblocks.blocks import BareBlock, FramedBlock
from blessedblocks.runner import Runner

# Create an embedded block with its own grid
eblocks = {}
eblocks[1] = FramedBlock(BareBlock('eblock1',hjust='>', vjust='='),
                         top_border='{t.green}x',
                         bottom_border='{t.blue}y',
                         #left_border='{t.yellow}z',
                         #right_border='{t.magenta}a',
                         title='InnerTop',
                         title_sep='{t.yellow}-')
eblocks[2] = BareBlock('eblock2', hjust='<', vjust='v')
eg = Grid(layout=[(1,2)], blocks=eblocks)

# These 3 lines will show just the embedded grid
#top = BareBlock(grid=eg)
#r = Runner(top)
#r.start()

# This will embed the embedded grid into an outer block with just a title
outer = BareBlock("", grid=eg)

# Put the outer block into a grid by itself
layout = [1]
blocks = {}
blocks[1] = FramedBlock(outer,
                        no_borders=True,
                        title='My Title',
                        title_sep='{t.red}-')
g = Grid(layout, blocks)

# Now put that in one final top block for running
top = BareBlock(grid=g)
r = Runner(top)
r.start()


