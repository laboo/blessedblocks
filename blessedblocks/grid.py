from __future__ import print_function
from blessed import Terminal
from block import Block
from math import floor, ceil
from threading import Event, Thread, Lock
import signal

class Grid(object):
    def __init__(self, arrangement, blocks=None):
        if type(arrangement) != list:
            raise ValueError('arrangement value must be of type list')
        self._slots = {}
        self._thread = None
        self._event = Event()
        self._mutex = Lock()
        self._done = False
        self.load(arrangement, blocks)

    def load(self, arrangement, blocks=None):
        self._arrangement = arrangement
        with self._mutex:
            self._slots = {}
            self._load(arrangement, blocks)
            for block in self._slots.values():
                block.dirty = True
        self._event.set()

    def _load(self, arrangement, blocks=None):
        for element in arrangement:
            if type(element) == int:
                if element in self._slots:
                    raise ValueError('numbers embedded in arrangement must not have duplicates')
                self._slots[element] = blocks[element] if blocks and element in blocks else None
            elif type(element) in (list, tuple):
                if len(element) == 0:
                    raise ValueError('lists and tuples embedded in arrangement must not be empty')
                self._load(element, blocks)
            else:
                raise ValueError('arrangement must contain only list of numbers and tuples of numbers')

    def __repr__(self):
        return '<Grid(arrangement={0}, slots={1}>'.format(self._arrangement, self._slots)

    def _on_resize(self, *args):
        # TODO I've seen it block here -- deadlock on the mutex, probably because this signal
        # handler gets run in the main thread apparently
        with self._mutex:
            for block in self._slots.values():
                block.dirty = True
        self._event.set()
        
    def start(self):

        self._thread = Thread(
            name='grid',
            target=self._run,
            args=()
        )

        signal.signal(signal.SIGWINCH, self._on_resize)

        self._thread.start()

    def stop(self, *args):
        if not self._done:
            self._done = True
            self._event.set()
            if self._thread and self._thread.isAlive():
                self._thread.join()

    def done(self):
        return not self._thread.isAlive() or self._done

    def _run(self):
        term = Terminal()
        self._event.set() # show at start once without an event triggering
        with term.fullscreen():
            while True:
                if self._done:
                    break
                term.move(0,0)
                self._event.wait()
                with self._mutex:
                    self._display(term, term.width, term.height, 0, 0)
                    self._event.clear()

    def _display(self, term, width, height, x, y):

        def calc_block_size(total_size, num_blocks, block_index):
            rem = total_size % num_blocks
            base = total_size // num_blocks
            return base + int(block_index < rem)

        def calc_block_offset(orig_offset, total_size, num_blocks, block_index):
            offset = orig_offset
            for i in range(0, block_index):
                offset += calc_block_size(total_size, num_blocks, i)
            return offset

        def dfs(term, arrangement, width, height, x, y):
            orig_x = x
            orig_y = y
            h = height
            w = width
            for i, element in enumerate(arrangement):

                if type(arrangement) == list:
                    w = calc_block_size(width, len(arrangement), i)
                elif type(arrangement) == tuple:
                    h = calc_block_size(height, len(arrangement), i)

                if type(arrangement) == list:
                    x = calc_block_offset(orig_x, width, len(arrangement), i)
                elif type(arrangement) == tuple:
                    y = calc_block_offset(orig_y, height, len(arrangement), i)

                if type(element) in (list, tuple):
                    dfs(term, element, w, h, x, y)
                else:
                    block = self._slots[element]
                    if block.dirty:
                        lines = block.display(h, w)
                        if lines:
                            for j, line in enumerate(lines):
                                with term.location(x=x, y=y+j):
                                    # Can debug here by printing to a file
                                    try:
                                        print(line.rstrip().format(t=term), end='')
                                    except ValueError:
                                        raise ValueError(line.rstrip())

        dfs(term, self._arrangement, width, height, x, y)

    def update_block(self, block_num, text):
        with self._mutex:
            self._slots[block_num].update(text)
            self._event.set()

    

