#!/usr/bin/python3
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), "blessedblocks"))
# Previous two lines not needed if blessedblocks modules is installed
from blessedblocks.bare_block import BareBlock
from blessedblocks.block import Grid, SizePref
from blessedblocks.runner import Runner
from threading import Event, Thread, Lock
from tabulate import tabulate
import datetime
from blessed import Terminal

term = Terminal()
layout = [(0,1,[2,3,4],5)]
blocks = {}

blocks[0] = BareBlock()
blocks[0].update(" ")
blocks[1] = BareBlock(vjust='^', hjust='^')
blocks[1].update("My Title!\n--------------")
blocks[2] = BareBlock(hjust='<')
blocks[2].update((('x' * 50) + '\n') * 15 + 'x')
blocks[3] = BareBlock(vjust='=', hjust='^')
blocks[3].update('This is some centered text!')
blocks[4] = BareBlock(hjust='>')
blocks[4].update((('x' * 50) + '\n') * 15 + 'x')
blocks[5] = BareBlock()
blocks[5].update((('z' * 200) + '\n') * 15 + 'x')


g = Grid(layout, blocks)
top = BareBlock(grid=g)

r = Runner(top)
r.start()


