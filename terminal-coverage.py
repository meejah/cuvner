#!/usr/bin/env python

# great kurt-idea: make "lessopen" shit work with this, so "if less a
# file, and a .coverae 'up there somewhere' then highlight it"

# prints out annotated coverage to the terminal, with a
# banner-per-file showing coverage, and a total at the end.

from __future__ import print_function

import sys
import math
import cPickle
from os.path import split

import colors

from pygments import highlight
from pygments.formatters import Terminal256Formatter, TerminalFormatter
from pygments.lexers import get_lexer_by_name

if True:
    for i in range(16):
        print('%03d' % (i*16), end='')
        for j in range(16):
            print(colors.color(' ', bg=(i*16+j)), end='')
        print()
#    import os
#    os.exit(0)

from coverage import coverage
cov = coverage()
cov.load()

if False:
    a = cov._analyze(cov.data.measured_files()[3])
    print(a)
    print(dir(a))
    print(cov.data.measured_files())
    print(a.statements)
    print(a.missing)

def print_banner(fname, percent, fill):
    print(colors.color('-' * fill, bg=226, fg=236))
    maxsize = fill - len('coverage: ') - 3
    truncfname = fname[-maxsize:]
    if len(truncfname) != len(fname):
        truncfname = '...' + truncfname
    print(colors.color(('coverage: ' + truncfname).ljust(fill), bg=226, fg=236))
    grsize = int(fill * percent)
    if grsize >= 5:
        prcnt_formatted = '%3d%%' % int(percent * 100.0)
        gr = colors.color(prcnt_formatted + (' ' * (grsize - 4)), fg=255, bg=22)
    else:
        gr = colors.color(' ' * grsize, bg=22)
    red = colors.color(' ' * int(math.ceil(fill * (1.0 - percent))), bg=52)
    #print(colors.color('{}%'.format(int(percent * 100.0)).ljust(fill), bg=226, fg=236))
    print(gr + red)
    print(colors.color('-' * fill, bg=226, fg=236))

total_statements = 0
total_missing = 0
total_files = 0
for fname in cov.data.measured_files():
    if len(sys.argv) > 1:
        match = False
        for arg in sys.argv[1:]:
            if arg in fname:
                match = True
                break
        if not match:
            continue

    try:
        covdata = cov._analyze(fname)
    except Exception:
        print("failed:", fname)
        continue
    percent = 1.0  # if no statements, it's all covered, right?
    if covdata.numbers.n_statements:
        percent = float(covdata.numbers.n_statements - covdata.numbers.n_missing) / covdata.numbers.n_statements
    total_statements += covdata.numbers.n_statements
    total_missing += covdata.numbers.n_missing
    total_files += 1

    fill = 100

    print_banner(fname, percent, fill)

    lines = highlight(
        open(fname).read(), get_lexer_by_name('python'),
        #formatter=Terminal256Formatter(style='paraiso_dark')
        formatter=Terminal256Formatter(style='monokai')
        #formatter=Terminal256Formatter(style='igor')
        #formatter=TerminalFormatter(bg='dark', colorscheme='solarized')
    )
    lines = lines.split('\n')
    if False:
        print(dir(covdata.numbers))
        print(dir(covdata))
        print(covdata.statements)
        assert len(lines) == covdata.numbers.n_statements
        print(dir(covdata))
        print(covdata.branch_lines())

    cfg = dict(
        branch_bg = 52,
    )
    #formatter=Terminal256Formatter(style='solarized-dark')))
    import string
    for (i, line) in enumerate(lines):
        spaces = fill - len(colors.strip_color(line))
        spaces = ' ' * spaces
        if (i + 1) not in covdata.missing:
            if False:#(i + 1) in covdata.statements:
                print((colors.color(unichr(0x258f), fg=46, bg=22) + colors.color(line + spaces, bg=22)).encode('utf8'))
            else:
                if (i + 1) in covdata.excluded:
                    line = colors.strip_color(line)
                    print((colors.color(unichr(0x258f), fg=46, bg=236) + colors.color(line + spaces, bg=236, fg=242)).encode('utf8'))
                elif (i + 1) in covdata.branch_lines():
                    line = colors.strip_color(line)
                    print((colors.color(unichr(0x258a), bg=cfg['branch_bg'], fg=160) + colors.color(line + spaces, bg=cfg['branch_bg'])).encode('utf8'))
                else:
                    print((colors.color(unichr(0x258f), fg=46) + line + spaces).encode('utf8'))
        else:
            #print((colors.color(unichr(0x258f), fg=160, bg=236) + colors.color(line + spaces, bg=236)).encode('utf8'))
            print((colors.color(unichr(0x258f), fg=160, bg=52) + colors.color(line + spaces, bg=52)).encode('utf8'))

if total_statements == 0:
    print("Didn't find any coverage information.")
else:
    covr = total_statements - total_missing
    percent = float(covr) / total_statements
    msg = "%d of %d statements in %d files" % (covr, total_statements, total_files)
    print_banner(msg, percent, 100)
