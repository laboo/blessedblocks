from .line import Line
from threading import RLock
from collections import namedtuple
import re
import abc

'''
A Block represents a rectangular section of a terminal screen. A Block can contain
other Blocks by specifying a Grid, or it can generate display text, but it can't
do both. Thus, Blocks are nodes in a tree, and only terminal nodes can be displayed.

A Grid specifies how its Block is broken up into rectangular slots, each of which
can hold one other Block, and then assigns a Block to the each of the slots.

A SizePref if a declaration of the Block's demands and requests when placed into a
Grid with other Blocks.

Blocks (mutable) and SizePrefs (immutable) are thread-safe, Grids are not.
Grid modifications should be done by replacing a Grid with another.

A Runner (defined in runner.y) is responsible for displaying a Block,
and all the Blocks it contains, recursively, in the terminal. The Runner displays the
Block when started, and again every time any Block changes, or a periodic timer expires.

'''

SizePref = namedtuple('SizePref', 'hard_min hard_max')

class Grid(object):
    def __init__(self, layout=None, blocks=None):
        if (layout or blocks) and not (layout and blocks):
            raise ValueError('Grid arguments must both exist or both not exist.')
        self.write_lock = RLock()
        self._slots = {}
        self._layout = layout if layout else []
        self._index = 0
        self._load(self._layout, blocks)

    def _load(self, layout, blocks=None):
        with self.write_lock:
            for element in layout:
                if type(element) == int:
                    if element in self._slots:
                        raise ValueError('numbers embedded in grid must not have duplicates')
                    self._index = max(self._index, element) + 1
                    self._slots[element] = blocks[element] if blocks and element in blocks else None
                elif type(element) in (list, tuple):
                    if len(element) == 0:
                        raise ValueError('lists and tuples embedded in grid must not be empty')
                    self._load(element, blocks)
                else:
                    raise ValueError('grid must contain only list of numbers and tuples of numbers')

    def replace(self, i, block):
        with self.write_lock:
            slots[i] = block

    def add_under(self, block):
        with self.write_lock:
            i = self._index
            if type(self._layout) == list:
                self._layout = tuple([self._layout, i])
            elif type(self._layout) == tuple:
                self._layout = self._layout.append(i)
            else:
                raise ValueError(type(self._layout))
            self._index += 1

    def add_right(self, block):
        with self.write_lock:
            i = self._index
            if type(self._layout) == list:
                self._layout.append(i)
            elif type(self._layout) == tuple:
                self._layout = [self._layout, i]
            else:
                raise ValueError(type(self._layout))
            self._index += 1

    def __repr__(self):
        return str(self._layout)

'''
These two wrappers add convenience for keeping the Block thread-safe.
The safe_set function notifies the Grid, if the block is contained
within one, that the block has changed.
'''
from functools import wraps
def safe_set(method):
    @wraps(method)
    def _impl(self, *args, **kwargs):
        with self.write_lock:
            method(self, *args, **kwargs)
        try:
            if self.dirty_event:
                self.dirty_event.set()
        except AttributeError:
            pass
    return _impl

def safe_get(method):
    @wraps(method)
    def _impl(self, *args, **kwargs):
        with self.write_lock:
            r = method(self, *args, **kwargs)
        return r
    return _impl

class Block(object, metaclass=abc.ABCMeta):
    #MIDDLE_DOT = u'\u00b7'

    def __init__(self,
                 text=None,
                 hjust='<',  # horizontally left-justified within block
                 vjust='^',  # vertically centered within block
                 # The SizePrefs indicate how much screen real estate (width and height) this
                 # block desires/requires when displayed. Here, we default the block to
                 # as-much-as-you-got-but-none-is-fine.
                 w_sizepref = SizePref(hard_min=0, hard_max=float('inf')),
                 h_sizepref = SizePref(hard_min=0, hard_max=float('inf')),
                 grid=None):
        self.write_lock = RLock()
        self.hjust = hjust
        self.vjust = vjust
        self.text = text if text else None
        self.w_sizepref = w_sizepref
        self.h_sizepref = h_sizepref
        self.grid = grid
        # Below here non-thread safe attrs: TODO (document or make thread-safe)
        self._num_text_rows = 0
        self._num_text_cols = 0
        self.dirty_event = None
        self.prev_seq = ''

    ''' TODO: Figure this out
    def __repr__(self):
        return ('<Block {{name={0}, title={1}, len(text)={2}, lines={3}}}>'
                .format(self.name,
                        self.title.plain,
                        len(self.text) if self.text else 0,
                        len(self.text.split('\n')) if self.text else 0))
    '''

    @abc.abstractmethod
    def display(self, width, height, x, y, term=None):
        raise NotImplementedError('Subclasses must define display() in order to use this base class.')

    @property
    @safe_get
    def text(self): return self._text

    @text.setter
    @safe_set
    def text(self, val):
        if val and (not hasattr(self, '_text') or self._text != val):
            self._text = val
            rows = val.split('\n')
            clean_rows = []
            for row in rows:
                clean_rows.append(re.sub(r'{t\..*?}', '', row))
            self._num_text_cols = max(map(len, clean_rows))
            self._num_text_rows = len(clean_rows)
            try:
                if self.dirty_event:
                    self.dirty_event.set()
            except AttributeError:
                pass
        else:
            self._text = ''

    @property
    @safe_get
    def dirty_event(self): return self._dirty_event

    @dirty_event.setter
    @safe_set
    def dirty_event(self, val): self._dirty_event = val

    @property
    @safe_get
    def hjust(self): return self._hjust

    @hjust.setter
    @safe_set
    def hjust(self, val):
        if val not in ('<', '^', '>'):
            raise ValueError("Invalid hjust value, must be '<', '^', or '>'")
        self._hjust = val

    @property
    @safe_get
    def vjust(self): return self._vjust

    @vjust.setter
    @safe_set
    def vjust(self, val):
        if val not in ('^', '=', 'v'):
            raise ValueError("Invalid vjust value, must be '^', '=', or 'v'")
        self._vjust = val

    @property
    @safe_get
    def h_sizepref(self): return self._h_sizepref

    @h_sizepref.setter
    @safe_set
    def h_sizepref(self, val): self._h_sizepref = val

    @property
    @safe_get
    def w_sizepref(self): return self._w_sizepref

    @w_sizepref.setter
    @safe_set
    def w_sizepref(self, val):
        self._w_sizepref = val

    @property
    @safe_get
    def grid(self): return self._grid

    @grid.setter
    @safe_set
    def grid(self, val): self._grid = val

