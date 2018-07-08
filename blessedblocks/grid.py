from __future__ import print_function
from blessed import Terminal
from .block import Block, Arrangement, SizePref
from math import floor, ceil
from threading import Event, Thread, RLock
from time import sleep
import signal

# A Plot is an object-oriented realization of the information Arrangement
# object contains. We don't force the block developer to handle this complexity.
# The block developer is responsible only for the Arrangement: a map of numbers
# to blocks, and a layout. The layout is an recursive structure containing only
# Python lists, tuples, and numbers. (for example [1, [(2,3), [4, 5]]]). The
# digits signify leaf blocks (those not containing an Arrangement of blocks
# embedded with it. Lists in the layout signify horizontal orientation of the
# blocks it contains, and the tuple, horizontal orientation. The problem with
# the layout is that it's not possible (without subclassing, which doesn't work
# well here) to hang metadata on the lists and tuples. We need that metadata to
# know how to divvy up the space available to leaf blocks in the list or tuple,
# given the space available to the list or tuple as a whole. This metadata is the
# SizePrefs each block declares.
#
# We use Plots to objectify the Arrangement as follows. A leaf block gets wrapped
# in Plot object together with the block's own SizePrefs. A list or tuple in a
# layout is  built into a Plot object using the blocks it contains, but its
# SizePref's arg calculated from the merging of the SizePrefs of those blocks.
# This is the metadata referred to above.

# So, building a plot requires a recursive procedure. On the way down from the
# outermost block, we build up a tree of Plots as we go. It's *on the way back up*,
# though, that we calcuate SizePrefs for the Plots that represent sequences.

class Plot(object):
    def __init__(self,
                 w_sizepref=SizePref(hard_min=0, hard_max=[]),
                 h_sizepref=SizePref(hard_min=0, hard_max=[]),
                 horizontal=True,
                 subplots=None,
                 block = None):
        self.w_sizepref = w_sizepref
        self.h_sizepref = h_sizepref
        self.subplots = subplots
        self.horizontal = horizontal
        self.block = block

    def __repr__(self):
        me ='[ z={} chld={} name={}'.format(self.horizontal,
                                            len(self.subplots) if self.subplots else 0,
                                            self.block.name if self.block else '')
        if self.subplots:
            for subplot in self.subplots:
                me = me + '\n\t' + repr(subplot)
        me = me + ' ]'
        return me

class Grid(object):
    def __init__(self, block, stop_event=None):
        self._block = block
        self._plot = Plot()
        self._refresh = Event()
        self._done = Event()
        self._term = Terminal()
        self._lock = RLock()
        self._stop_event = stop_event
        self._not_just_dirty = Event()
        self._root_plot = None
        self.load(self._block.arrangement)

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
                    self.load(self._block.arrangement)
                    self.display_plot(self._root_plot,
                                      0, 0,                                   # x, y
                                      self._term.width, self._term.height-1,  # w, h
                                      self._term, just_dirty)
                    self._refresh.clear()

    def update(self):
        self._refresh.set()

    def update_block(self, index, block):
        with self._lock:
            self._block.arrangement._slots[index] = block
            block.set_dirty_event(self._refresh)
        self.update()

    def load(self, arrangement):
        with self._lock:
            self._block.arrangement = arrangement
            for _, block in self._block.arrangement._slots.items():
                block.set_dirty_event(self._refresh)
            layout = self._block.arrangement._layout
            blocks = self._block.arrangement._slots
            self._root_plot = self.build_plot(layout, blocks)
        #self.update_all()

    def _input(self):
        with self._term.cbreak():
            val = ''
            while val.lower() != 'q':
                print(self._term.move(self._term.height, 2) + '', end='')
                val = self._term.inkey(timeout=.1)
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

    # Gets called at Grid creation any time the configuration (not display)
    # of a block in the Grid gets changes. When it does, we need to rebuild
    # the plot tree. Starting from the root block, we recurse down all its
    # embedded blocks, creating a Plot to represent each level on the way.
    # As we undo the recursion and travel back up the tree, at each level
    # we merge the SizePrefs of all the blocks at that level and store the
    # result in the Plot containing the blocks. When this completes, we can use the
    # resulting plot tree to display the Grid.
    def build_plot(self, layout, blocks, horizontal=True):
        def merge_sizeprefs(plots):
            w_hard_min, w_hard_max, h_hard_min, h_hard_max = 0, [], 0, []
            # Hard maxes merge only if *all* subplots have a hard_max set
            num_w_hard_maxes, num_h_hard_maxes = 0, 0
            for plot in subplots:
                w_hard_min += plot.w_sizepref.hard_min
                if plot.w_sizepref.hard_max: num_w_hard_maxes += 1
                w_hard_max += plot.w_sizepref.hard_max
                h_hard_min += plot.h_sizepref.hard_min
                if plot.h_sizepref.hard_max: num_h_hard_maxes += 1
                h_hard_max += plot.h_sizepref.hard_max
            w_hard_max = [max(w_hard_max)] if num_w_hard_maxes == len(subplots) else []
            h_hard_max = [max(h_hard_max)] if num_h_hard_maxes == len(subplots) else []
            w_sizepref = SizePref(hard_min=w_hard_min,
                                  hard_max=w_hard_max)
            h_sizepref = SizePref(hard_min=h_hard_min,
                                  hard_max=h_hard_max)
            return w_sizepref, h_sizepref

        subplots = []
        if not layout:
            for _, block in blocks.items():
                # if there's no arrangement there's only one block.
                # merge its sizeprefs (which contain numbers) into
                # new sizeprefs containing lists.
                hard_max = []
                if block.w_sizepref.hard_max == 'text':
                    hard_max = [block.text_cols]
                elif block.w_sizepref.hard_max != float('inf'):
                    hard_max = [block.w_sizepref.hard_max]
                w_sizepref = SizePref(hard_min=block.w_sizepref.hard_min,
                                      hard_max=hard_max)

                hard_max = []
                if block.h_sizepref.hard_max == 'text':
                    hard_max = [block.text_rows]
                elif block.h_sizepref.hard_max != float('inf'):
                    hard_max = [block.h_sizepref.hard_max]
                h_sizepref = SizePref(hard_min=block.h_sizepref.hard_min,
                                      hard_max=hard_max)

                # This return is purposely *inside* the loop
                return Plot(w_sizepref, h_sizepref, block=block)
        for element in layout:
            if type(element) == int:
                block = blocks[element]
                if block.arrangement:
                    subplot = self.build_plot(block.arrangement._layout,
                                              block.arrangement._slots)
                else:  # it's a leaf block
                    subplot = self.build_plot(None, {element: block})
            else:  # it's list or tuple
               orientation = type(element) == list
               subplot = self.build_plot(element, blocks, orientation)
            subplots.append(subplot)

        w_sizepref, h_sizepref = merge_sizeprefs(subplots)
        return Plot(w_sizepref, h_sizepref, horizontal=horizontal, subplots=subplots)

    # Display the plot by recursing down the plot tree built by
    # build_plot() and determine the coordinates for the plots embedded in
    # each plot by using the SizePrefs of the plots
    def display_plot(self, plot, x, y, w, h, term=None, just_dirty=True):
        if plot.block:
            plot.block.display(w, h, x, y, term, just_dirty)
        else:
            for subplot, new_x, new_y, new_w, new_h in self.divvy(plot.subplots, x, y, w, h, plot.horizontal):
                self.display_plot(subplot, new_x, new_y, new_w, new_h, term, just_dirty)

    # Divvy up the space available to a series of plots among them
    # by referring to SizePrefs for each.
    def divvy(self, plots, x, y, w, h, horizontal):
        def calc_block_size(total_size, num_blocks, block_index):
            rem = total_size % num_blocks
            base = total_size // num_blocks
            return base + int(block_index < rem)

        n = len(plots)
        memo = [[]] * n
        for i in range(n):
            memo[i] = {'x':0, 'y':0, 'w':0, 'h':0}

        # handle hard_min first, but save off hard_maxes
        rem = w if horizontal else h  # remaining space to divvy
        hard_maxes = []
        unmet_hard_maxes_indexes = set()
        free_indexes = set()
        for i, plot in enumerate(plots):
            if horizontal:
                prefs, xy, wh = plot.w_sizepref, 'x', 'w'
            else:
                prefs, xy, wh = plot.h_sizepref, 'y', 'h'

            if rem > 0:
                amount = min(rem, prefs.hard_min)
                rem -= amount
                memo[i][wh] += amount
            if prefs.hard_max:
                total_hard_max = sum(prefs.hard_max)
                # hard_maxes is a tuple: (remaining_required, plot_index)
                hard_maxes.append((max(0, (total_hard_max - memo[i][wh])), i))
                if memo[i][wh] < total_hard_max:
                    #hard_maxes.append((total_hard_max,i))
                    unmet_hard_maxes_indexes.add(i)
            else:
                free_indexes.add(i)

        if rem > 0:  # if rem == 0, we're done
            # Now deal with hard_max
            watermark = 0
            for num, index in sorted(hard_maxes):
                # if this hard max has been satisfied already, move passed it
                if num <= watermark:
                    continue
                unsatisfied_hard_maxes = len(hard_maxes) - index
                satisfied_hard_maxes = len(hard_maxes) - unsatisfied_hard_maxes
                new_amount = num - watermark
                # Is rem large enough that everyone can take on the new amount?
                if (rem // (n - satisfied_hard_maxes)) < new_amount:
                    # no. we're done. just split the remaining space fairly
                    break
                else:
                    watermark = num

            # All max(watermark/hard_max) to every plot.
            for i, plot in enumerate(plots):
                if horizontal:
                    prefs, xy, wh = plot.w_sizepref, 'x', 'w'
                else:
                    prefs, xy, wh = plot.h_sizepref, 'y', 'h'
                if not prefs.hard_max:
                    alloc = watermark
                else:
                    hard_max_target = sum(prefs.hard_max) - memo[i][wh]
                    alloc = min(watermark, hard_max_target)
                    if alloc > 0:
                        if alloc == hard_max_target:
                            unmet_hard_maxes_indexes.remove(i)  # hard_max has been met for this plot
                memo[i][wh] += max(0, alloc)
                rem -= alloc
            if rem:  # rem can't be < 0
                # mins and maxes have all been accounted for
                rem_copy = rem
                total_unmet = n - (len(hard_maxes) - len(unmet_hard_maxes_indexes))
                for i in range(n):
                    if i not in unmet_hard_maxes_indexes and i not in free_indexes:
                        continue
                    add = calc_block_size(rem_copy, total_unmet, i)
                    memo[i]['w' if horizontal else 'h'] += add
                    rem -= add
            #assert(rem == 0), rem

        # Calculate x,y and bundle for return
        out = []
        count_x, count_y = x, y
        for i, plot in enumerate(plots):
            m = memo[i]
            if horizontal:
                m['x'] = count_x
                count_x += m['w']
                m['y'] = y
                m['h'] = h
            else:
                m['y'] = count_y
                count_y += m['h']
                m['x'] = x
                m['w'] = w
            out.append((plot, m['x'], m['y'], m['w'], m['h']))
        return out

if __name__ == '__main__':
    blocks = {}
    blocks[1] = Block('blx')
    blocks[2] = Block('bly')
    blocks[3] = Block('blz')
    a = Arrangement([1, (2,3)], blocks)
    top = Block('top', arrangement=a)
    grid = Grid(top)
    plot = grid.build_plot(a._layout, a._slots)
    print(plot)

