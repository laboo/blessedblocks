from __future__ import print_function
from blessed import Terminal
from block import Block
from math import floor, ceil
from threading import Event, Thread, Lock
import signal

class Grid(object):
    def __init__(self, block):
        self._block = block
        self._event = Event()
        self._mutex = Lock()
        self._done = False
        self._term = Terminal()
        
    def __repr__(self):
        return 'grid'

    def _on_resize(self, *args):
        # TODO I've seen it block here -- deadlock on the mutex, probably because this signal
        # handler gets run in the main thread apparently
        with self._mutex:
            # set dirty
            self._block.display(self._term.width, self._term.height, 0, 0, self._term, just_dirty=False)
            self._term.move(0,0)
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
                print('joining')
                self._thread.join()

    def done(self):
        return not self._thread.isAlive() or self._done

    def _run(self):

        self._event.set() # show at start once without an event triggering
        with self._term.fullscreen():
            while True:
                if self._done:
                    break
                self._term.move(0,0)
                self._event.wait()
                with self._mutex:
                    self._block.display(self._term.width, self._term.height, 0, 0, self._term)
                    self._term.move(0,0)
                    self._event.clear()


