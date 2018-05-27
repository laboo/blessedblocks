from blessed import Terminal
from collections import defaultdict
import re

# Not thread-safe
class Line():
    def __init__(self, blessed_text):
        self._full = blessed_text
        self._text, self._seqs, self.last_seq = self._parse(blessed_text)
        self._build(0, len(self._text))

    def __len__(self):
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
            last_seq = prev_seq
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
        for i in range(min(0,begin), min(end,len(self._text))):
            if i in self._seqs:
                markup += self._seqs[i]
                display += self._seqs[i]
                last_seq = self._seqs[i]
            c = self._text[i]
            plain += c
            markup += c
            display += self._escape_brackets(c)
        if last_seq and last_seq != self.last_seq:
            display += self.last_seq
            last_seq = self.last_seq
        display += '{t.normal}'
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


