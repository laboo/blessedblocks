from __future__ import print_function
from blessed import Terminal
from block import Block
from math import floor, ceil
from threading import Event, Thread, RLock
import signal

class Grid(object):
    def __init__(self, block, term, stop_event=None):
        self._block = block
        self._refresh = Event()
        self._done = Event()
        self._term = term
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

        signal.signal(signal.SIGWINCH, self._on_resize)
        signal.signal(signal.SIGINT, self._on_kill)

        self._thread.start()

    def stop(self, *args):
        self._term.clear()
        if not self._done.is_set():
            self._done.set()
            self._refresh.set() # in order to release it from a wait()
            if self._thread and self._thread.isAlive():
                self._thread.join()

    def done(self):
        return not self._thread.isAlive() or self._done.is_set()

    def _run(self):
        self._refresh.set() # show at start once without an event triggering
        with self._term.fullscreen():
            while True:
                if self._done.is_set():
                    break
                self._refresh.wait()
                with self._lock:
                    if self._not_just_dirty.is_set():
                        just_dirty = False
                        self._not_just_dirty.clear()
                    else:
                        just_dirty = True
                    self._block.display(self._term.width, self._term.height, 0, 0, self._term, just_dirty=just_dirty)
                    self._term.move(0,0)
                    self._refresh.clear()

    def update(self):
        with self._lock:
            self._refresh.set()

    def load(self, arrangement):
        with self._lock:
            self._block.arrangement = arrangement
        self.update_all()
