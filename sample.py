#!/usr/bin/python3
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "blessedblocks"))
# Previous two lines not needed if blessedblocks modules is installed
from blessedblocks.block import Block, Arrangement, SizePref
from blessedblocks.grid import Grid
from threading import Event, Thread, Lock
from tabulate import tabulate
import datetime

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
          '9123{t.blue}456789012345678901234567890123456789\n')

# Specify the positioning of the blocks.
# A list is horizontal, a tuple is vertical
arrangement = [(4, [(1,2,3), (8,9), (5,[6,7])])]

# Build the contents of each of the blocks specified in the arrangement
blocks = {}

blocks[1] = Block('Block1') # all the defaults
blocks[1].update("{t.normal}A block with no title\n" + FILLER)

blocks[2] = Block('Block with colors in title.',
                  title='{t.cyan}Block {t.red}#2{t.normal}',
                  hjust='>') # with a title, right justified
blocks[2].update(FILLER)

blocks[3] = Block('Block3',
                  left_border=None,
                  right_border=None,
                  top_border=None,
                  bottom_border=None,
                  vjust='v',
                  title='Block with no borders')
blocks[3].update(FILLER)

blocks[4] = Block('Block4',
                  left_border=None,
                  right_border=None,
                  top_border=None,
                  bottom_border=None,
                  hjust='^',
                  vjust='=',
                  h_sizepref = SizePref(hard_min=0, hard_max=1),
                  #title='The Current Time centered') # updated in loop below
                  title='')
blocks[4].update(str(datetime.datetime.now()))
blocks[5] = Block('Block5', title='Block #5',
                  h_sizepref = SizePref(hard_min=0, hard_max='text')
                  )
blocks[5].update(FILLER)

blocks[6] = Block("tabulate block hjust=^", # text at bottom of block
                  hjust='^',
                  title='A tabulate block')

blocks[6].update(tabulate([['col1', 'col2'], [1.23, 2.456]]))

blocks[7] = Block('Block7', title='Block #7')
blocks[7].update(FILLER)

headers=["Planet","R (km)", "mass (x 10^29 kg)"]
table = [["Sun",696000,1989100000],["Earth",6371,5973.6],
         ["Moon",1737,73.5],["Mars",3390,641.85]]

blocks[8] = Block('Block8', # text in center of block
                  left_border='{t.blue}# ',
                  right_border='{t.green} #',
                  top_border='{t.magenta}#',
                  bottom_border='{t.green}#',
                  hjust='^',
                  vjust='=',
                  title='Tabulate hjust=^, vjust==')
blocks[8].update(tabulate(table, headers=headers))


# Create an embedded block with its own arrangement
eblocks = {}
eblocks[1] = Block('eblock1', title='eblock1')
eblocks[2] = Block('eblock2', title='eblock2')
eblocks[1].update("some text")
eblocks[2].update("more text")

ea = Arrangement(layout=[(1,2)], blocks=eblocks)
bb = Block("embedded", arrangement=ea)

blocks[9] = bb  # stick it in slot 9

a = Arrangement(layout=arrangement, blocks=blocks)
ba = Block("", arrangement=a)

# Main logic
stop_event = Event()
g = Grid(ba, stop_event=stop_event)

g.start()

for i in range(300):
    if g.app_refresh_event.is_set():
        blocks[2].title = 'got event ' + str(i)
        g.app_refresh_event.clear()
    stop_event.wait(.1)
    blocks[2].top_border = str(i%10)
    import random
    blocks[2].hjust = random.choice(['<', '^', '>'])
    blocks[4].update(str(datetime.datetime.now()))
    eblocks[1].update(str(i))

# Replace the entire arrangement
a2 = Arrangement(layout=[2,3,4,9], blocks=blocks)
g.load(a2)

for i in range(300):
    stop_event.wait(.1)
    blocks[4].update(str(datetime.datetime.now()))

g.stop()


