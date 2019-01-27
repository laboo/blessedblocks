from .block import Block, SizePref
from .line import Line

class VFillBlock(Block):
    def __init__(self, text):
        border_text, seqs, last_seq = Line.parse(text)
        super().__init__(text=text, w_sizepref=SizePref(hard_min=len(border_text),
                                                        hard_max=len(border_text)))

    def display(self, width, height, x, y, term=None):
        with self.write_lock:
            border_text, seqs, last_seq = Line.parse(self.text)
            out = []
            line = Line(self.text, width, '<')

            for h in range(height):
                if term:
                    with term.location(x=x, y=y+h):
                        print(line.display.format(t=term), end='')
                        #print(line.display, end='')
                else:
                    out.append(line.display)
            if not term:
                return out
'''                    
            n = height * len(border_text)
            out = []
            while n > 0:
                out.append('{t.normal}' + border_text[:min(n,len(border_text))])
                #text = Line.repeat_to_width(border, height * len(border_text)).display
                n -= len(border_text)
            if term:
                with term.location(x=x, y=y):
                    print('\n'.join(out).format(t=term), end='')
            else:
                return out  # for testing purposes only
'''
