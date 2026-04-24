import shutil

def term_width():
    """Return terminal width (columns), default 80."""
    try:
        return shutil.get_terminal_size().columns
    except:
        return 80

def print_header_block(lines):
    """
    Print a list of lines, each truncated to terminal width.
    The first line is prefixed with a separator.
    """
    w = term_width()
    for line in lines:
        # truncate to width-2 to leave room for border if needed, but simple truncation
        print(line[:w])
