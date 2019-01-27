from .block import Block, SizePref
from .line import Line
import re

class BareBlock(Block):
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
        super().__init__(text=text, hjust=hjust, vjust=vjust,
                         w_sizepref=w_sizepref, h_sizepref=h_sizepref, grid=grid)
        self._prev_seq = '{t.normal}'

    def display(self, width, height, x, y, term=None):
        with self.write_lock:
            out = []
            if self.text is not None and len(self.text) != 0:
                available_for_text_rows = max(0, height)
                available_for_text_cols = max(0, width)

                all_btext_rows = []
                for row in self.text.rstrip().split('\n'):
                    all_btext_rows.append(row)  # TODO all we really need is a count here, right?
                useable_btext_rows = all_btext_rows[:available_for_text_rows]

                # Calculate the values for adjusting the text vertically within the block
                # if there's extra empty rows.
                ver_pad = max(0, (available_for_text_rows - len(all_btext_rows)))
                top_ver_pad = 0
                if self.vjust == '=':
                    top_ver_pad = ver_pad // 2
                elif self.vjust == 'v':
                    top_ver_pad = ver_pad

                # Finally, build the block from top to bottom, adding each next line
                # if there's room for it. The bottom gets cut off if there's not enough room.
                # This behavior (cutting from the bottom) is not configurable.
                line = None
                remaining_rows = height

                # By default, empty rows fill out the bottom of the block.
                # Here we move some of them up above the text if we need to.
                ver_pad_count = top_ver_pad
                while ver_pad_count and remaining_rows:
                    line = Line(' ' * width, width, self.hjust)
                    out.append(line)
                    ver_pad_count -= 1
                    remaining_rows -= 1

                # This is the main text of the block
                prev_seq = '{t.normal}'                
                for i in range(max(0,available_for_text_rows - top_ver_pad)):
                    if remaining_rows <= 0:
                        break
                    line = None
                    if i >= len(useable_btext_rows):
                        line = Line(prev_seq + ' ', width, self.hjust)
                    else:
                        line = Line(prev_seq + useable_btext_rows[i], width, self.hjust)
                    if line:
                        out.append(line)
                        prev_seq = line.last_seq
                        remaining_rows -= 1

            if len(out):
                out[-1].display += '{t.normal}'

            if term:
                for j, line in enumerate(out):
                    with term.location(x=x, y=y+j):
                        # Can debug here by printing to a file
                        #with open('/tmp/bare', 'a') as f:
                        #    f.write(line.display + '\n')
                            
                        try:
                            text = re.sub(r"\r?\n?$", "", line.display, 1)
                            print(text.format(t=term), end='')
                        except ValueError:
                            raise ValueError(line.rstrip())
                term.move(term.height, term.width)  # TODO This doesn't work
            else:
                return [line.display for line in out]  # for testing purposes only


        


