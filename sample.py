#!/usr/bin/python3
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "blessedblocks"))
# Previous two lines not needed if blessedblocks modules is installed
from blessedblocks.block import Block, Grid, SizePref
from blessedblocks.blocks import BareBlock, FramedBlock
from blessedblocks.line import Line
from blessedblocks.runner import Runner
from threading import Event, Thread, Lock
from tabulate import tabulate
import datetime
import shlex
from subprocess import check_output

# Some constants
POUND = '#'
FILLER = ('01234}6789012345678901234567890123456789\n'
          '1123{567890123{t.cyan}45678901234567890{t.red}123456789\n'
          '212345678901234567890123456789012345678{t.yellow}9\n'
          '3123456789012345678901234567890123456789\n'
          '4123456789012345678901234567890123456789\n'
          '5123456789012345678901234567890123456789\n'
          '6123456789012345678901234567890123456789\n'
          '7123456789012345678901234567890123456789\n'
          '8123456789012345678901234567890123456789\n'
          '9123{t.blue}456789012345678901234567890123456789')

def run_cmd_in_block(cmd, block, refresh=3.0):
    while True:
        data = check_output(shlex.split(cmd))
        block.text = data.decode()
        if stop_event.wait(refresh):
            return

# Specify the positioning of the blocks.
# A list is horizontal, a tuple is vertical
grid = [(4, [(1,2,3), (8,9), (5,[6,7])], 10)]

# Build the contents of each of the blocks specified in the grid
blocks = {}

blocks[1] = BareBlock(None)

blocks[2] = FramedBlock(BareBlock(FILLER, hjust='>'), # with a title, right justified
                        title='{t.cyan}Block {t.red}#2{t.normal}',
                        title_sep='-',
                        top_border='x')

blocks[3] = FramedBlock(BareBlock(FILLER, vjust='v'),
                        no_borders=True,
                        title='FramedBlock with no borders',
                        title_sep='-')

blocks[4] = BareBlock(str(datetime.datetime.now()), hjust='^', vjust='=',
                      h_sizepref = SizePref(hard_min=0, hard_max=1))

blocks[5] = FramedBlock(BareBlock(FILLER,
                                  h_sizepref = SizePref(hard_min=0, hard_max='text')),
                        title='Block #5',
                        title_sep='-')

blocks[6] = FramedBlock(BareBlock(tabulate([['col1', 'col2'], [1.23, 2.456]]), # text at bottom of block
                                  hjust='^'),
                        title="tabulate block hjust=^",
                        title_sep='-')

blocks[7] = FramedBlock(BareBlock(FILLER),title='Block #7',title_sep='-')

headers=["Planet","R (km)", "mass (x 10^29 kg)"]
table = [["Sun",696000,1989100000],["Earth",6371,5973.6],
         ["Moon",1737,73.5],["Mars",3390,641.85]]

blocks[8] = FramedBlock(BareBlock(tabulate(table, headers=headers),
                                  hjust='^',
                                  vjust='=',
                                  h_sizepref=SizePref(hard_min=0, hard_max='text')),
                        left_border='{t.blue}#',
                        right_border='{t.green}#',
                        top_border='{t.magenta}# ',
                        bottom_border='{t.green}#',
                        title='hjust=^, vjust==, vhard_max="text"', title_sep='-')



# Create an embedded block with its own grid
eblocks = {}

triangle = '*\n***\n*****\n*******\n*********'
block_just_block = BareBlock(triangle, block_just=True)
line_just_block = BareBlock(triangle, block_just=False)
eblocks[1] = FramedBlock(block_just_block, title='block_just=True', title_sep='-')
eblocks[2] = FramedBlock(line_just_block, title='block_just=False', title_sep='-')

eg = Grid(layout=[(1,2)], blocks=eblocks)
bb = BareBlock(None, grid=eg)

blocks[9] = bb  # stick it in slot 9

blocks[10] = BareBlock(text='top output', hjust='^', vjust='^',
                       h_sizepref = SizePref(hard_min=1, hard_max=10))

g = Grid(layout=grid, blocks=blocks)
ba = BareBlock(None, grid=g)


# Main logic
stop_event = Event()
r = Runner(ba, stop_event=stop_event)
r.start()

blocks[1].text = ("{t.normal}A bare block with just a rg&b horizontal line\n" +
                  Line.repeat_to_width('{t.red}-{t.green}-{t.blue}-', r.term_width()).display)

# Start the top output in block 10
top_thread = Thread(target=run_cmd_in_block,
                    args=('top -b -n 1 -w 512', blocks[10], 1))
top_thread.start()

# Refresh some of the blocks in a tight loop
for i in range(100):
    stop_event.wait(0.1)
    blocks[2].top_border = str(i%10)
    import random
    just = random.choice(['<', '^', '>'])
    block_just_block.hjust = just
    line_just_block.hjust = just
    blocks[4].text = 'bare block ' + str(datetime.datetime.now())

# Replace the entire grid with a new one using some of the original blocks
g2 = Grid(layout=[2,3,4,9], blocks=blocks)
r.load(g2)

# Loop again changing just the block with the time
for i in range(100):
    stop_event.wait(.1)
    blocks[4].text = 'bare_block ' + str(datetime.datetime.now())

stop_event.set()
top_thread.join()
r.stop()
