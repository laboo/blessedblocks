from .block import Block, SizePref
from .line import Line

class HFillBlock(Block):
    def __init__(self, text):
        super().__init__(text=text, h_sizepref=SizePref(hard_min=1, hard_max=1))

    def display(self, width, height, x, y, term=None):
        with self.write_lock:
            text = Line.repeat_to_width(self.text, width).display
            if term:
                with term.location(x=x, y=y):
                    print(text.format(t=term), end='')
            else:
                return [text]  # for testing purposes only
