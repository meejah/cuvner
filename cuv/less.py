# great kurt-idea: make "lessopen" shit work with this, so "if less a
# file, and a .coverae 'up there somewhere' then highlight it"

# prints out annotated coverage to the terminal, with a
# banner-per-file showing coverage, and a total at the end.

from __future__ import print_function, absolute_import

import math
from os.path import abspath

import colors
import click
import six

from pygments import highlight
from pygments.formatters import Terminal256Formatter, TerminalFormatter
from pygments.lexers import get_lexer_by_name

from cuv.util import print_banner


def term_color(target_fname, cfg, style='monokai'):
    cov = cfg.data
    match = []

    target_fname = abspath(target_fname)
    for fname in cov.data.measured_files():
        if target_fname == abspath(fname):
            match.append(fname)

    if len(match) != 1:
        if len(match) == 0:
            raise RuntimeError(
                "Can't find any files matching '%s'." % target_fname
            )
        else:
            raise RuntimeError("Multiple matches: %s" % ', '.join(match))

    fname = match[0]
    covdata = cov._analyze(fname)

    percent = 1.0  # if no statements, it's all covered, right?
    if covdata.numbers.n_statements:
        percent = float(covdata.numbers.n_statements - covdata.numbers.n_missing) / covdata.numbers.n_statements
    total_statements = covdata.numbers.n_statements
    total_missing = covdata.numbers.n_missing

    fill = min(click.get_terminal_size()[0], 80)
    print_banner(fname, percent, fill)

    # it was tempting to write/override/wrap this Formatter and mess
    # with the background color based on our coverage data -- and
    # that's not a terrible idea, but the way TerminalFormatter is
    # written, it's not very nice. Basically, we'd have to wrap the
    # output stream, look for ANSI reset codes, and re-do the
    # background color after each reset (for "uncovered" lines)...
    # so I didn't do that. Instead we just hack it by clearing *all*
    # formatting from the "uncovered" lines and make them all "grey on
    # red"

    formatter = TerminalFormatter(style=style)
    lines = highlight(
        open(fname).read(), get_lexer_by_name('python'),
        formatter=formatter,
    )
    lines = lines.split('\n')

    for (i, line) in enumerate(lines):
        spaces = fill - len(colors.strip_color(line))
        spaces = ' ' * spaces
        if (i + 1) not in covdata.missing:
            if (i + 1) in covdata.excluded:
                line = colors.strip_color(line)
                print((colors.color(six.unichr(0x258f), fg=46, bg=236) + colors.color(line + spaces, bg=236, fg=242)).encode('utf8'))
            elif cfg.branch and (i + 1) in covdata.branch_lines():
                line = colors.strip_color(line)
                print((colors.color(six.unichr(0x258a), bg=52, fg=160) + colors.color(line + spaces, bg=52)).encode('utf8'))
            else:
                print((colors.color(six.unichr(0x258f), fg=46) + line + spaces).encode('utf8'))
        else:
            # HACK-O-MATIC, uhm. Yeah, so what we're doing here is
            # splitting the output from the formatter on the ANSI
            # "reset" code, and the re-assembling it with the "52"
            # (dark red) background color. I appoligize in advance;
            # PRs with improvements encouraged!
            reset_code = "\x1b[39;49;00m"
            segments = (line + spaces).split(reset_code)
            reset_plus_bg = "\x1b[39;49;00m\x1b[39;49;48;5;52m"
            out = "\x1b[39;49;48;5;52m" + reset_plus_bg.join(segments)
            print((colors.color(six.unichr(0x258f), fg=160, bg=52) + out).encode('utf8'))
            # (on the plus side: this preserves syntax-highlighting
            # while also getting a backgroundc color on the whole
            # line)
