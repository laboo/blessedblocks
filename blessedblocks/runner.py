from __future__ import print_function
from blessed import Terminal
from .block import Block, Grid, SizePref
from math import floor, ceil
from threading import Event, Thread, RLock, current_thread
from time import sleep
import signal
import logging

# A Plot is an object-oriented realization of the information the Grid object
# inside the Runner's Block object (attribute).  We don't force the Block
# developer to handle this complexity.
# The Block developer is responsible only for the Grid: a map of numbers
# to blocks, and a layout. The layout is a recursive structure containing only
# Python lists, tuples, and numbers. (for example [1, [(2,3), [4, 5]]]). The
# digits signify leaf blocks (those not containing a Grid of blocks
# embedded within it). _Lists_ inside the layout signify horizontal orientation
# of the blocks it contains, and _tuples_, horizontal orientation. The problem with
# this simple implementation of a layout -- just lists, tuple, and digits --
# is that it's not possible (without subclassing, which doesn't work
# well here) to hang metadata on the lists and tuples. We need that metadata to
# know how to divvy up the space available to each of the leaf blocks within
# the list or tuple, given the space available to the list or tuple as a whole.
# This metadata is the SizePrefs each Block declares.
#
# We use Plots to objectify the Grid as follows. A leaf Block gets wrapped
# in a Plot object together with the block's own SizePrefs. A list or tuple in a
# layout is built into a Plot object using the Blocks it contains, but its
# SizePref's arg is calculated from the merging of the SizePrefs of those blocks.
# This is the metadata referred to above.

# So, building a plot requires a recursive procedure. On the way down from the
# outermost block, we build up a tree of Plots as we go. It's _on the way back up_,
# though, that we calcuate SizePrefs for the Plots that represent lists or tuples.

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
        #self.update_all()


    # Gets called at Runner creation and at any time the Runner's Block
    # changes. When it does, we need to rebuild the plot tree. Starting
    # from the root Block, we recurse down all its embedded Blocks, creating
    # a Plot to represent each level on the way.
    # As we undo the recursion and travel back up the tree, at each level
    # we merge the SizePrefs of all the blocks at that level and store the
    # result in the Plot containing the blocks. When this completes, we can use the
    # resulting plot tree to display the Runner's Block.
    def build_plot(self, layout, blocks, horizontal=True):
        def merge_sizeprefs(plots):
            w_hard_min, w_hard_max, h_hard_min, h_hard_max = 0, [], 0, []
            # Hard maxes merge only if *all* subplots have a hard_max set
            # because if any subplot will take as much as it can, we want
            # the (super)plot to claim as much space as it can. If all
            # subplots have a hard_max specified, we know exactly the max
            # space needed so we claim that.
            num_w_hard_maxes, num_h_hard_maxes = 0, 0
            for plot in subplots:
                w_hard_min += plot.w_sizepref.hard_min
                if plot.w_sizepref.hard_max: num_w_hard_maxes += 1
                w_hard_max += plot.w_sizepref.hard_max
                h_hard_min += plot.h_sizepref.hard_min
                if plot.h_sizepref.hard_max: num_h_hard_maxes += 1
                h_hard_max += plot.h_sizepref.hard_max
            # TODO max or sum?
            w_hard_max = [sum(w_hard_max)] if num_w_hard_maxes == len(subplots) else []
            h_hard_max = [sum(h_hard_max)] if num_h_hard_maxes == len(subplots) else []
            w_sizepref = SizePref(hard_min=w_hard_min,
                                  hard_max=w_hard_max)
            h_sizepref = SizePref(hard_min=h_hard_min,
                                  hard_max=h_hard_max)
            return w_sizepref, h_sizepref

        subplots = []
        if not layout:
            for _, block in blocks.items():
                # if there's no layout there's only one block.
                # merge its sizeprefs (which contain numbers) into
                # new sizeprefs containing lists. hard_max'es can
                # contain either the string 'text' meaning 'the
                # size of the amount of text you can fit in the
                # plot, or they can contain a float, which is treated
                # as an int, but using float allows for infinity.
                # TODO: how is 'text' different from float('inf')
                # exactly? Don't they both mean use all space avail-
                # able?

                # handle w_sizepref
                hard_max = []
                if block.w_sizepref.hard_max == 'text':
                    hard_max = [block.num_text_cols]
                elif block.w_sizepref.hard_max != float('inf'):
                    hard_max = [block.w_sizepref.hard_max]
                w_sizepref = SizePref(hard_min=block.w_sizepref.hard_min,
                                      hard_max=hard_max)

                # handle h_sizepref
                hard_max = []
                if block.h_sizepref.hard_max == 'text':
                    hard_max = [block.num_text_rows]
                elif block.h_sizepref.hard_max != float('inf'):
                    hard_max = [block.h_sizepref.hard_max]
                h_sizepref = SizePref(hard_min=block.h_sizepref.hard_min,
                                      hard_max=hard_max)

                # This return is purposely *inside* the loop
                # TODO why? because there's no layout?
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

        w_sizepref, h_sizepref = merge_sizeprefs(subplots)
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
                #amount = min(rem, prefs.hard_min)
                amount = min(0, prefs.hard_min)
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

