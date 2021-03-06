#!/usr/bin/python3
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "blessedblocks"))
# Previous two lines not needed if blessedblocks modules is installed
from blessedblocks.bare_block import BareBlock
from blessedblocks.block import Grid, SizePref
from blessedblocks.runner import Runner
from blessedblocks.line import Line
from threading import Event, Thread, Lock
from tabulate import tabulate
import datetime
from blessed import Terminal

term = Terminal()
layout = [(0,1,[2,3,4],5)]
blocks = {}

blocks[0] = BareBlock(text=" ")  # TODO, why is a space needed?
rwb = ('{t.red}My {t.white}American {t.blue}Title!\n' +
       Line.repeat_to_width('{t.red}-{t.white}-{t.blue}-', 18).display)
blocks[1] = BareBlock(vjust='^', hjust='^', text=rwb)
blocks[2] = BareBlock(hjust='<',text=((('x' * 50) + '\n') * 15 + 'x'))
blocks[3] = BareBlock(vjust='=', hjust='^', text='This is some centered text!')
blocks[4] = BareBlock(hjust='>', text=((('x' * 50) + '\n') * 15 + 'x'))
blocks[5] = BareBlock(text=((('z' * 200) + '\n') * 15 + 'x'))


g = Grid(layout, blocks)
top = BareBlock(grid=g)

r = Runner(top)
r.start()


