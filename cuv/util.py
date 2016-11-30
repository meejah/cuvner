
import time
from os import path
from contextlib import contextmanager

import click
import colors
import math


def timer(name):
    """
    Returns a context-manager that times a block of code, printing out
    the resulting time.
    """

    @contextmanager
    def _timer():
        start = time.time()
        yield
        diff = time.time() - start
        print("{} took {}s".format(name, diff))
    return _timer()


def common_root_path(file_names):
    """
    returns the greatest-length common portion of the path in the
    given collection of file-names
    """
    # I'm sure there's a better way ...
    common = file_names[0]
    for fname in file_names[1:]:
        common = ''.join([x[0] for x in zip(common, fname) if x[0] == x[1]])
    return common


class _PagedEcho(object):
    """
    Interal helper for paged_echo()
    """
    def __init__(self):
        self._lines = []

    def echo(self, message=None, file=None, nl=True, err=False, color=None):
        if nl:
            self._lines.append('{}\n'.format(message))
        else:
            self._lines.append(message)

        if file is not None:
            raise Exception("Unsupported kwarg 'file='")
        if err:
            raise Exception("Unsupported kwarg 'err='")

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        click.echo_via_pager(''.join(self._lines), color=True)


def paged_echo():
    """
    Unfortunately, to use .echo_via_pager() in Click, you have to feed
    it all of the lines at once.

    This returns a context-manager that lets you incrementally call
    '.echo' (same as 'click.echo') incrementally, only outputting (to
    the pager) when the context closes.
    """
    return _PagedEcho()


def find_coverage_data(d):
    """
    Recursively ascends directories looking for a .coverage file,
    unless a .git is encountered first (then fail) or root is reached.
    """

    d = path.abspath(d)
    if d == '/':
        return None

    candidate = path.join(d, '.coverage')
    if path.exists(candidate):
        return candidate

    if path.exists(path.join(d, '.git')):
        return None

    return find_coverage_data(path.split(d)[0])


def print_banner(fname, percent, fill=None):
    """
    Prints out a coloured banner showing coverage percent

    :param fill: the width of the banner; if None, uses 80 or the
        terminal width, whichever is less.
    """

    if fill is None:
        fill = min(click.get_terminal_size()[0], 80)

    click.echo(colors.color('-' * fill, bg=226, fg=236), color=True)
    maxsize = fill - len('coverage: ') - 3
    truncfname = fname[-maxsize:]
    if len(truncfname) != len(fname):
        truncfname = u'...{}'.format(truncfname)
    click.echo(colors.color(u'coverage: {}'.format(truncfname).ljust(fill), bg=226, fg=236), color=True)
    grsize = int(fill * percent)
    if grsize >= 5:
        prcnt_formatted = u'%3d%%' % int(percent * 100.0)
        gr = colors.color(prcnt_formatted + (u' ' * (grsize - 4)), fg=255, bg=22)
    else:
        gr = colors.color(u' ' * grsize, bg=22)
    red = colors.color(u' ' * int(math.ceil(fill * (1.0 - percent))), bg=52)
    click.echo(gr + red, color=True)
    click.echo(colors.color(u'-' * fill, bg=226, fg=236), color=True)
