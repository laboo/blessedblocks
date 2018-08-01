def get_cmd(term, lock, done, app_refresh_event):
    with term.cbreak():
        cmd = ''
        val = ''
        with term.location(x=0, y=term.height):
            print('> ' + (' ' * (term.width-2)), end='')

        while True:
            if done.is_set():
                return cmd
            print(term.move(term.height, 2 + len(cmd)) + '', end='')
            val = term.inkey(timeout=1)
            if val == '\n':
                with term.location(x=0, y=term.height):
                    print('> ' + (' '  * (term.width - 2)), end='')
                app_refresh_event.set()
                break
            with lock:
                if val.is_sequence:
                    # handle backspace, what else?
                    #print("got sequence: {0}.".format((str(val), val.name, val.code)), end='')
                    continue
                if val:
                    cmd += val
                with term.location(x=0, y=term.height):
                    term.move(term.height, 3 + len(cmd))
                    print('> ' + cmd + (' '  * (term.width - (2 + len(cmd)))), end='')
        return cmd
