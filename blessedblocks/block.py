from blessedblocks.line import Line
class Block(object):
    MIDDLE_DOT = u'\u00b7'
    def __init__(self, name,
                 title='',
                 top_border=MIDDLE_DOT,
                 bottom_border=MIDDLE_DOT,
                 left_border=MIDDLE_DOT,
                 right_border=MIDDLE_DOT,
                 hjust='<',
                 vjust='^'):
        self.name = name
        self.title = Line('{t.normal}' + title)  # TODO why do we need this???
        self.top_border = Line(top_border)
        self.bottom_border = Line(bottom_border)
        self.left_border = Line(left_border)
        self.right_border = Line(right_border)
        if hjust not in ('<', '^', '>'):
            raise ValueError("Invalid hjust value, must be '<', '^', or '>'")
        self.hjust = hjust
        if vjust not in ('^', '=', 'v'):
            raise ValueError("Invalid vjust value, must be '^', '=', or 'v'")
        self.vjust = vjust
        self.text = None
        self.dirty = False
        self.prev_seq = ''

    def __repr__(self):
        return ('<Block {{name={0}, title={1}, len(text)={2}, lines={3}}}>'
                .format(self.name,
                        self.title.plain,
                        len(self.text) if self.text else 0,
                        len(self.text.split('\n')) if self.text else 0))
    
    def update(self, text):
        if self.text != text:
            self.dirty = True
            self.text = text

    def _build_horiz_border(self, text, width):
        if not text:
            return None
        out = Line(text.markup * max(width, (width // len(text.markup))))
        out.resize(0, width)
        return out.display
        
    def _build_line(self, text, num_cols, width, tjust='<', padding=0, term=None):
        text_width = max(0, width - len(self.left_border.plain) - len(self.right_border.plain))
        text.resize(0, text_width)
        left_pad = ''
        if self.hjust == '^':
            left_pad = ' ' * (padding // 2)
            text_width = text_width - (padding // 2)
        elif self.hjust == '>':
            left_pad = ' ' * padding
            text_width = text_width - padding

        text_width += len(text.display) - len(text.plain)
        '''
        print("tjust        ", tjust)
        print("width        ", width)
        print("new_text     ", new_text.plain)
        print("len(new_text)", len(new_text.plain))
        print("text_width   ", text_width)
        print("left_pad     ", '*' + left_pad + '*')
        print("len(left_pad)", len(left_pad))
        print("lpad + text_width   ", text_width + len(left_pad))
        '''
        text_width += len(self.prev_seq)
        fmt = '{0}{1}{2:{3}{4}}{5}'.format(self.left_border.display if width > 0 else '',
                                           left_pad,
                                           self.prev_seq + text.display,
                                           tjust,
                                           text_width,
                                           self.right_border.display if width > 1 else '',
                                           t=term)

        self.prev_seq = text.last_seq if text.last_seq else '{t.normal}'

        return fmt
    
    def display(self, height, width, term=None):
        self.dirty = False
        out = []
        if self.text is not None and len(self.text) != 0:
            available_for_text_rows = max(0,(height
                                             - (1 if self.top_border else 0)
                                             - (1 if self.bottom_border else 0)
                                             - (2 if len(self.title.plain) else 0)))
            available_for_text_cols = max(0, (width
                                              - len(self.left_border.plain)
                                              - len(self.right_border.plain)))

            all_btext_rows = []
            for row in self.text.rstrip().split('\n'):
                all_btext_rows.append(Line(row))
            usable_btext_rows = all_btext_rows[:available_for_text_rows]
            
            # Calculate the values for adjusting the text horizonally within the block
            # if there's extra space in the columns for all rows.
            max_col_len = 0
            for brow in all_btext_rows:
                max_col_len = max(max_col_len, len(brow.plain))
            col_pad = max(0, available_for_text_cols - max_col_len)

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
            if self.top_border is not None and remaining_rows:
                line = self._build_horiz_border(self.top_border, width)
                if line:
                    out.append(line)
                    remaining_rows -= 1

            # Titles are always centered. This is not configurable.
            if len(self.title.plain) and remaining_rows:
                line = self._build_line(self.title, width, width, tjust='^', term=term)
                if line:
                    out.append(line)
                    remaining_rows -= 1
                    line = self._build_line(Line('-' * available_for_text_cols), width, width, term=term)
                    if remaining_rows:
                        out.append(line)
                        remaining_rows -= 1

            # By default, empty rows fill out the bottom of the block.
            # Here we move some of them up above the text if we need to.
            ver_pad_count = top_ver_pad
            while ver_pad_count and remaining_rows:
                line = self._build_line(Line(' '), available_for_text_cols, width, term=term)
                out.append(line)
                ver_pad_count -= 1
                remaining_rows -= 1

            # This is the main text of the block
            for i in range(max(0,available_for_text_rows - top_ver_pad)):
                if remaining_rows <= 0:
                    break
                line = ''
                if i >= len(usable_btext_rows):
                    line = self._build_line(Line(' '), width, width, term=term)
                else:
                    line = self._build_line(usable_btext_rows[i], available_for_text_cols, width, padding=col_pad, term=term)
                if line:
                    out.append(line)
                    remaining_rows -= 1

            # Add the bottom border
            if self.bottom_border is not None and remaining_rows:
                line = self._build_horiz_border(self.bottom_border, width)
                if line:
                    out.append(line)
                    remaining_rows -= 1
        if len(out):
            out[0] = '{t.normal}' + out[0]
            out[-1] += '{t.normal}'

        return out

def main():
    import sys
    from blessed import Terminal

    height = int(sys.argv[1]) if len(sys.argv) > 2 else 10    
    width = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    term = Terminal()

    block = Block("me", left_border='*', right_border="x",  top_border='a', bottom_border='z', title="This is it.", hjust='>')
    block.update('hi\nthere\nyou\n01}23{}{4567890\n\n6th\n7th\n8\n9\n10')
    lines = block.display(height,width)
    for line in lines:
        print(line.format(t=term))

    block = Block("you", left_border='*', right_border="x",  top_border='a', bottom_border='z', title="This is it.", hjust='>')
    block.update('hi\nthe{t.yellow}re\nyo}{u\n{t.blue}0123{t.red}4567890\n\n6th\n7th{t.normal}x\n8\n9\n10')
    lines = block.display(height,width,term=term)
    for line in lines:
        print(line.format(t=term))

    term = Terminal()
    block = Block("you", left_border='*', right_border="x",  top_border='a', bottom_border='z', title="This is it.", hjust='>')
    block.update('the{t.yellow}s{}e')
    lines = block.display(height,width,term=term)
    for line in lines:
        print(line.format(t=term))

if __name__ == '__main__':
    main()
