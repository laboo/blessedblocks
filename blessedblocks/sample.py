from block import Block
from grid import Grid
from threading import Event, Thread, Lock
import signal
from tabulate import tabulate
import datetime
from blessed import Terminal
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

# Catch a ^C and shut down gracefully
stop = Event()
def on_kill(*args):
    g.stop()
    stop.set()

# Specify the positioning of the blocks.
# A list is horizontal, a tuple is vertical
arrangement = [(1,2,3), (4,8), (5,[6,7])]

# Build the contents of each of the blocks specified in the arrangement
blocks = {}

blocks[1] = Block('Block1') # all the defaults
blocks[1].update("A block with no title\n" + FILLER)

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
                  hjust='^',
                  vjust='=',
                  title='The Current Time centered') # updated in loop below

blocks[5] = Block('Block5', title='Block #5')
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

# Main logic
g = Grid(arrangement, blocks)
signal.signal(signal.SIGINT, on_kill)
g.start()
g.update_block(4, str(datetime.datetime.now()))
stop.wait(15)
a2 = [2,3,4]
g.load(a2, blocks)

for _ in range(15):
    g.update_block(4, str(datetime.datetime.now()))
    stop.wait(1)
g.stop()


