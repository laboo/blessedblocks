from blessed import Terminal
from collections import defaultdict
import re

# Not thread-safe
class Line():
    '''A iine of formatted text in a blessed block. Most notably, this line
    does not wrap. Instead, it truncates at the block width value. It supports
    colored text using the blessed color tags, eg, ${blue}blue text{$normal}.
    Three different views of the text of the line are available, and they
    are adjusted dynamically as the width of the block changes: (1) plain,
    which is the text minus any color tabs, (2) display, which when printed
    shows the plain text with colors, and (3) markup, which the text with
    color tags, but not necessarily fit for printing.
    '''
    def __init__(self, blessed_text):
        '''Create a Line object

        Args:
            blessed_text (str): Text of any length which may contain blessed color tags.

        Returns:
            nothing, but the plain, display and markup attributes are made available.
        '''
        self._full = blessed_text
        self._text, self._seqs, self.last_seq = self._parse(blessed_text)
        self._build(0, len(self._text))

    def __len__(self):
        '''Returns:
               the length of the text when viewed in a blessed terminal
        '''
        return len(self.plain)

    def __repr__(self):
        return self.plain  # TODO what should this be?
    
    def _parse(self, full):
        seqs = defaultdict(list)
        text = ''
        loc = 0
        prev_end = 0
        prev_seq = None
        if full:
            for match in re.finditer(r'{t\..+?}', full):
                loc += match.start() - prev_end
                curr_seq = full[match.start():match.end()]
                t = full[prev_end:match.start()] # text before/after/between sequences
                text += t
                if curr_seq != prev_seq:
                    seqs[loc] = curr_seq
                prev_seq = curr_seq
                prev_end = match.end()
            #self.last_seq = prev_seq
            text += full[prev_end:]
        return text, seqs, prev_seq

    def _escape_brackets(self, text):
        out = []
        for c in text:
            if c in '{}':
                out.append(c)
            out.append(c)
        return ''.join(out)

    def _build(self, begin, end):
        plain = ''
        markup = ''
        display = ''
        last_seq = ''
        start = min(0,begin)
        stop = min(end,len(self._text))
        for i in range(start, stop):
            if i in self._seqs:
                markup += self._seqs[i]
                display += self._seqs[i]
                last_seq = self._seqs[i]
            c = self._text[i]
            plain += c
            markup += c
            display += self._escape_brackets(c)
        # handle trailing sequences by grabbing just the last one of
        # any past the end
        i = stop  # where it would have exited the loop if it entered
        j = len(self._full) if self._full else 0
        while j >= i:
            if j in self._seqs:
                markup += self._seqs[j]
                display += self._seqs[j]
                last_seq = self._seqs[j]
                # if there are multiple tags passed the last text char,
                # only the last one is relevant, so we break after finding one
                break
            j -= 1
        if last_seq and last_seq != self.last_seq:
            display += self.last_seq
            last_seq = self.last_seq
        display += '{t.normal}' if not last_seq or last_seq != '{t.normal}' else ''
        self.plain = plain
        self.markup = markup
        self.display = display

    def resize(self, begin, end):
        self._build(begin, end)

if __name__ == '__main__':
    term = Terminal()
    line = Line("{t.green}{}{}}{blac{t.yellow}k justp{t.cyan}laintext{t.pink}")
    for i in range(len(line.plain) + 2):
        line.resize(0,i)
        print(line.plain)
        print(line.display.format(t=term) + '*')

    line.resize(0,len(line.plain))
    print(line._full)
    print(line.plain)
    print(line.markup)
    print(line.display)
    print(line.display.format(t=term) + '*')


