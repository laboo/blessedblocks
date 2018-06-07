from __future__ import print_function
from blessed import Terminal
from block import Block
from math import floor, ceil
from threading import Event, Thread, RLock
from copy import deepcopy
from time import sleep
import signal


class Grid(object):
    def __init__(self, block, stop_event=None):
        self._block = deepcopy(block)
        self._refresh = Event()
        self._done = Event()
        self._term = Terminal()
        self._lock = RLock()
        self._stop_event = stop_event
        self._not_just_dirty = Event()

    def __repr__(self):
        return 'grid'

    def _on_kill(self, *args):
        if self._stop_event:
            self._stop_event.set()
        self.stop()

    def update_all(self):
        self._not_just_dirty.set()
        self._refresh.set()

    def _on_resize(self, *args):
        self.update_all()

    def start(self):

        self._thread = Thread(
            name='grid',
            target=self._run,
            args=()
        )

        self._input = Thread(
            name='input',
            target=self._input,
            args=()
        )

        signal.signal(signal.SIGWINCH, self._on_resize)
        signal.signal(signal.SIGINT, self._on_kill)

        self._thread.start()
        sleep(1)  # let the term update before introducing the command line
        self._input.start()

    def stop(self, *args):
        self._term.clear()
        if not self._done.is_set():
            self._done.set()
            self._refresh.set() # in order to release it from a wait()
            if self._thread and self._thread.isAlive():
                self._thread.join()
            if self._input and self._input.isAlive():
                self._input.join()

    def done(self):
        return not self._thread.isAlive() or self._done.is_set()

    def _run(self):
        self._refresh.set() # show at start once without an event triggering
        with self._term.fullscreen():
            while True:
                if self._done.is_set():
                    break
                if not self._refresh.wait(.5):
                    continue
                with self._lock:
                    if self._not_just_dirty.is_set():
                        just_dirty = False
                        self._not_just_dirty.clear()
                    else:
                        just_dirty = True
                    self._block.display(self._term.width, self._term.height-1, 0, 0, self._term, just_dirty=just_dirty)
                    self._refresh.clear()

    def update(self):
        self._refresh.set()

    def update_block(self, index, block):
        with self._lock:
            self._block.arrangement._slots[index] = deepcopy(block)
        self.update()

    def load(self, arrangement):
        with self._lock:
            self._block.arrangement = deepcopy(arrangement)
        self.update_all()

    def _input(self):
        with self._term.cbreak():
            val = ''
            while val.lower() != 'q':
                print(self._term.move(self._term.height, 2) + '', end='')
                val = self._term.inkey(timeout=.5)
                if self._done.is_set():
                    break
                with self._lock:
                    if not val:
                        # timeout
                        with self._term.location(x=0, y=self._term.height):
                            print('> ' + (' '  * (self._term.width - 2)), end='')
                            continue
                    elif val.is_sequence:
                        with self._term.location(x=2, y=self._term.height-1):
                            print("got sequence: {0}.".format((str(val), val.name, val.code)), end='')
                    elif val:
                        with self._term.location(x=2, y=self._term.height-1):
                            print("got {0}.".format(val), end='')
