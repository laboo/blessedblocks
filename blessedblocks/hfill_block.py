from .block import Block, SizePref
from .line import Line

class HFillBlock(Block):
    def __init__(self, text):
        maxes = 0 if not text else 1  # Don't take up space if there's no text
        super().__init__(text=text, h_sizepref=SizePref(hard_min=maxes, hard_max='text'))

    def display(self, width, height, x, y, term=None):
        if not self.text:
            if not term:
                return []
            return

        with self.write_lock:
            text = Line.repeat_to_width(self.text, width).display

            if term:
                with term.location(x=x, y=y):
                    print(text.format(t=term), end='')
            else:
                return [text]  # for testing purposes only
