from __future__ import print_function
from blessed import Terminal
from .block import Block, Grid, SizePref
from math import floor, ceil
from threading import Event, Thread, RLock, current_thread
from time import sleep
import signal
import logging

# A Plot is an object-oriented realization of the information contained in
# the Grid object inside the Runner's Block object (attribute). We don't
# force the Block developer to handle this complexity.
#
# Instead, the Block developer is responsible only for the Grid: a map of numbers
# to blocks, and a layout. The layout is a recursive structure containing only
# Python lists, tuples, and numbers. (for example [1, [(2,3), [4, 5]]]). The
# digits signify leaf blocks (those not containing a Grid of blocks
# embedded within it). _Lists_ inside the layout signify horizontal orientation
# of the blocks it contains, and _tuples_, horizontal orientation. The problem with
# this simple implementation of a layout -- just lists, tuple, and digits for
# the convenience of the Block developer -- is that it's not possible (without
# subclassing, which doesn't work well here) to hang metadata on the lists and
# tuples. We need that metadata to know how to divvy up the space available to
# each of the leaf blocks within the list or tuple, given the space available to
# the list or tuple as a whole. This metadata is the SizePrefs each Block declares.
#
# We use Plots to objectify the Grid as follows. A leaf Block gets wrapped
# in a Plot object together with the block's own SizePrefs. A list or tuple in a
# layout is built into a Plot object using the Blocks it contains, but its
# SizePref's arg is calculated by the merging of the SizePrefs of those blocks.
# This is the metadata referred to above.
#
# So, building a plot requires a recursive procedure. On the way down from the
# outermost block, we build a tree of Plots as we go down. It's _on the way back
# up_, though, that we calcuate SizePrefs for the Plots that represent lists
# or tuples.
#
# Once the plot tree if fully built, the x and y coordinates and width and height
# of each block have been produced, and each block can be passed that information
# so that it can display itself.

# Uncomment to debug deadlock problems
#import stacktracer
#stacktracer.trace_start("/tmp/trace.html",interval=2,auto=True)

class Plot(object):
    def __init__(self,
                 w_sizepref=SizePref(hard_min=[0], hard_max=[float('inf')]),
                 h_sizepref=SizePref(hard_min=[0], hard_max=[float('inf')]),
                 horizontal=True,
                 subplots=None,
                 block = None):
        self.w_sizepref = w_sizepref
        self.h_sizepref = h_sizepref
        self.subplots = subplots
        self.horizontal = horizontal
        self.block = block

    def __repr__(self):
        me ='[ z={} chld={} wsp={}, hsp={}'.format(self.horizontal,
                                                   len(self.subplots) if self.subplots else 0,
                                                   self.w_sizepref,
                                                   self.h_sizepref)

        if self.subplots:
            for subplot in self.subplots:
                me = me + '\n\t' + repr(subplot)
        me = me + ' ]'
        return me

class Runner(object):
    def __init__(self, block, stop_event=None):

        self._block = block
        self._plot = Plot()
        self._refresh = Event()
        self.app_refresh_event = Event()
        self._done = Event()
        self._term = Terminal()
        self._lock = RLock()
        self._stop_event = stop_event
        self._not_just_dirty = Event()
        self._root_plot = None
        self.load(self._block.grid)

    def __repr__(self):
        return 'runner'

    def term_width(self):
        return self._term.width

    def term_height(self):
        return self._term.height

    def _on_kill(self, *args):
        if self._stop_event:
            self._stop_event.set()
        self.stop()

    def update_all(self):
        self._not_just_dirty.set()
        if not self._refresh.is_set():
            self._refresh.set()

    def _on_resize(self, *args):
        self.update_all()

    def start(self):

        self._thread = Thread(
            name='runner',
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

            if (self._thread and self._thread.isAlive() and
                self._thread.name != current_thread().name):
                self._thread.join()

    def done(self):
        return not self._thread.isAlive() or self._done.is_set()

    def _run(self):
        self._refresh.set() # show at start once without an event triggering
        with self._term.fullscreen():
            with self._term.hidden_cursor():
                try:
                    while True:
                        if self._done.is_set():
                            break
                        if not self._refresh.wait(.5):
                            continue
                        with self._lock:
                            if self._not_just_dirty.is_set():
                                #just_dirty = False
                                self._not_just_dirty.clear()
                                #else:
                                #just_dirty = True
                            self.load(self._block.grid)
                            self.display_plot(self._root_plot,
                                              0, 0,                                   # x, y
                                              self._term.width, self._term.height,  # w, h
                                              self._term)
                            self._refresh.clear()
                except Exception as e:
                    debug = True
                    if debug:
                        logging.exception("10 seconds to view exception")
                        sleep(10)
                    self.stop()
                    # TODO. This doesn't successfully stop the application

    def update(self):
        if not self._refresh.is_set():
            self._refresh.set()

    def update_block(self, index, block):
        with self._lock:
            self._block.grid._slots[index] = block
            block.dirty_event = self._refresh
        self.update()

    def load(self, grid):
        with self._lock:
            self._block.grid = grid
            for _, block in self._block.grid._slots.items():
                block.dirty_event = self._refresh
            layout = self._block.grid._layout
            blocks = self._block.grid._slots
            self._root_plot = self.build_plot(layout, blocks)


    # Gets called at Runner creation, when the terminal is resized, or any
    # part of any block is changed. When any of those happen, we need to rebuild
    # the plot tree. Starting from the root Block, we recurse down all its
    # embedded Blocks, creating a Plot to represent each level on the way.
    # As we undo the recursion and travel back up the tree, at each level
    # we merge the SizePrefs of all the blocks at that level and store the
    # result in the Plot containing the blocks. When this completes, we can use the
    # resulting plot tree to display the top-most block, the Runner's Block.
    def build_plot(self, layout, blocks, horizontal=True):
        def merge_sizeprefs(plots, horizontal):
            # m_ stands for "main", s_ stands for "secondary"
            # main is the width sizepref is the plot is horizontal, and
            # the height size pref if it's vertical.
            # The main sizepref is summed, the secondary maxed
            # TODO document hard_max and the infinities values
            m_hard_min, m_hard_max, s_hard_min, s_hard_max = [0], [], [0], []
            for plot in subplots:
                # Just combine arrays
                m_sizepref = plot.w_sizepref if horizontal else plot.h_sizepref
                m_hard_min += m_sizepref.hard_min
                if m_sizepref.hard_max != float('-inf'):
                    m_hard_max += m_sizepref.hard_max

                s_sizepref = plot.h_sizepref if horizontal else plot.w_sizepref
                s_hard_min += s_sizepref.hard_min
                if s_sizepref.hard_max != float('-inf'):
                    s_hard_max += s_sizepref.hard_max

            # sum the main sizeprefs
            m_hard_max = [sum(m_hard_max) if m_hard_max else None]
            m_hard_min = [sum(m_hard_min)]
            # max the secondary sizeprefs
            s_hard_max = [max(s_hard_max) if s_hard_max else None]
            s_hard_min = [max(s_hard_min)]

            m_sizepref = SizePref(hard_min=m_hard_min, hard_max=m_hard_max) if m_hard_max else None
            s_sizepref = SizePref(hard_min=s_hard_min, hard_max=s_hard_max) if s_hard_max else None

            return (m_sizepref, s_sizepref) if horizontal else (s_sizepref, m_sizepref)

        subplots = []
        if not layout:
            for _, block in blocks.items():
                # If there's no layout there's only one block.
                # merge its sizeprefs (which contain numbers) into
                # new sizeprefs containing lists. hard_max'es can
                # contain either the string 'text' meaning 'the
                # size of the amount of text you can fit in the
                # plot', or they can contain a float, which is treated
                # as an int, but using float allows for infinity.

                # handle w_sizepref
                if block.w_sizepref.hard_max == 'text':
                    hard_max = [block.num_text_cols]
                else:
                    hard_max = [block.w_sizepref.hard_max]
                w_sizepref = SizePref(hard_min=[block.w_sizepref.hard_min],
                                      hard_max=hard_max)

                # handle h_sizepref
                if block.h_sizepref.hard_max == 'text':
                    hard_max = [block.num_text_rows]
                else:
                    hard_max = [block.h_sizepref.hard_max]
                h_sizepref = SizePref(hard_min=[block.h_sizepref.hard_min],
                                      hard_max=hard_max)

                # This return is purposely *inside* the loop because
                # there's only one block, so we have all we need to
                # build the plot.
                return Plot(w_sizepref, h_sizepref, block=block)
        for element in layout:
            if type(element) == int:
                block = blocks[element]
                if block.grid:
                    subplot = self.build_plot(block.grid._layout,
                                              block.grid._slots)
                else:  # it's a leaf block
                    subplot = self.build_plot(None, {element: block})
            else:  # it's list or tuple
               orientation = type(element) == list
               subplot = self.build_plot(element, blocks, orientation)
            subplots.append(subplot)

        w_sizepref, h_sizepref = merge_sizeprefs(subplots, horizontal)
        return Plot(w_sizepref, h_sizepref, horizontal=horizontal, subplots=subplots)

    # Display the plot by recursing down the plot tree built by
    # build_plot() and determine the coordinates for the plots embedded in
    # each plot by using the SizePrefs of the plots
    def display_plot(self, plot, x, y, w, h, term=None, just_dirty=True):
        if plot.block:
            plot.block.display(w, h, x, y, term)
        else:
            for subplot, new_x, new_y, new_w, new_h in Runner.divvy(plot.subplots, x, y, w, h, plot.horizontal):
                self.display_plot(subplot, new_x, new_y, new_w, new_h, term, just_dirty)

    # Divvy up the space available to a series of plots among them
    # by referring to SizePrefs for each.
    def divvy(plots, x, y, w, h, horizontal):
        def calc_block_size(total_size, num_blocks, block_index):
            rem = total_size % num_blocks
            base = total_size // num_blocks
            return base + int(block_index < rem)

        n = len(plots)
        memo = [[]] * n
        for i in range(n):
            memo[i] = {'x':0, 'y':0, 'w':0, 'h':0}

        # The main complications in divvying up the available space for the
        # plots are in satisfying the hard_min and hard_max preferences for
        # each plot.
        # - hard_mins are relatively easy. A hard_min is a single value -- the
        # sum of all min for all this plot's subplots. We just reserve the
        # hard_min if it's available, and that's it.
        # - hard_maxes are harder. A hard_max value is an array of all hard_max
        # values for this plot's subplots.

        # handle hard_min first, but save off hard_maxes
        rem = w if horizontal else h  # remaining space to divvy
        hard_maxes = []  # tuple: (remaining_allowed, plot_index)
        unmet_hard_maxes_indexes = set()  # ??? TODO
        free_indexes = set()  # we can assign unlimited space to these blocks
        for i, plot in enumerate(plots):
            if horizontal:
                prefs, xy, wh = plot.w_sizepref, 'x', 'w'
            else:
                prefs, xy, wh = plot.h_sizepref, 'y', 'h'

            if rem > 0:
                # Reserve only the minimum space required
                #amount = min(rem, prefs.hard_min)  # TODO use 0 instead of rem?
                amount = min(rem, max(prefs.hard_min))
                rem -= amount
                memo[i][wh] += amount
            if prefs.hard_max:
                total_hard_max = sum(prefs.hard_max)
                # hard_maxes is a tuple: (remaining_allowed, plot_index)
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
    g = Grid([1, (2,3)], blocks)
    top = BareBlock(grid=g)
    runner = Runner(top)
    plot = runner.build_plot(a._layout, a._slots)
    print(plot)

