

from __future__ import print_function, absolute_import

import time
import math
from os.path import abspath

import colors
import click
import six

from pygments import highlight
from pygments.formatters import Terminal256Formatter, TerminalFormatter
from pygments.lexers import get_lexer_by_name

from cuv.util import print_banner, timer
from cuv.analysis import CoverageAnalysis, create_analysis

# XXX FIXME TODO
# - the Coverage API seems .. awkward.
# - be "nice" to access Analysis instances, as I did before?
#    (via cov._analyze() which is what Coverage.analyze2() calls anyway)
# - can we make it more-lazy?
# - be nice to have a streaming interface/API to Click's pager support
#    (e.g. a mode that makes all click.echo()'s go through pager, or
#     make click.echo_to_pager() accept progressive statements etc)

# XXX FIXME: why do I have to do .encode('utf8') to get "less" to
# show colors etc properly (and *not* with click.echo() where I can't
# make less work properly, even with 'less -r'). I'd rather not use
# click.echo_to_pager() because then I have to produce all the output
# up front, which e.g. takes 5 seconds (to do all the .analysis2()
# calls) in Twisted codebase.


def graph_coverage(keywords, cfg):
    file_coverage = []

    start_time = time.time()
    file_coverage = list(cfg.measured_filenames(keywords))
    file_coverage.sort()
    diff = time.time() - start_time

    common = file_coverage[0]
    for fname in file_coverage[1:]:
        common = ''.join([x[0] for x in zip(common, fname) if x[0] == x[1]])

    click.echo("Coverage in: {}".format(common))

    common = len(common)

    if True:
        lines_per_col = 8
    else:
        max_statements = max([len(d.statements) for name, d in file_coverage])
        lines_per_col = math.ceil(float(max_statements) / float(graph_width))
        if lines_per_col < 8:
            lines_per_col = 8

    max_fname = max([len(nm) - common for nm in file_coverage])
    width = click.get_terminal_size()[0]
    graph_width = width - 5 - max_fname

    def percent_to_bar(prct):
        # 0x2581 is _ like bar
        # 0x2588 is completely solid
        if prct < 0.125:
            return click.style(u' ', fg='red', bg='green')
        return click.style(
            six.unichr(0x2580 + int(prct / 0.125)), fg='red', bg='green'
        )

    last_fname = None
    last_prefix = 0
    for fname in file_coverage:
        try:
            data = create_analysis(cfg.data, fname)
        except Exception as e:
            click.echo(u"error: {}: {}".format(fname, e))
        short = fname[common:]
        graph = ''
        glyphs = 0
        printed_fname = False
        bad = total = 0
        percent = 100.0  # if no statements, it's all covered, right?
        if data.statements:
            percent = (1.0 - (len(data.missing) / float(len(data.statements)))) * 100.0
        if last_fname is not None:
            last_prefix = 0
            for (a, b) in zip(last_fname.split('/'), short.split('/')):
                if a != b:
                    break
                last_prefix += len(a) + 1
            if last_prefix > 0:
                last_prefix -= 1
        last_fname = short

        for statement in data.statements:
            total += 1
            if statement in data.missing:
                bad += 1
            if total == lines_per_col:
                graph += percent_to_bar(float(bad) / float(total))
                glyphs += 1
                bad = total = 0

            if glyphs >= graph_width:
                if printed_fname:
                    click.echo(u'{} {}'.format(u' ' * max_fname, graph), color=True)
                else:
                    printed_fname = True
                    thisname = (u' ' * last_prefix) + short[last_prefix:]
                    thisname = click.style(fname[common:common + last_prefix], fg='black') + click.style(short[last_prefix:], bold=True)
                    click.echo(
                        u'{}{} {} {}'.format(
                            thisname,
                            u' ' * (max_fname - len(short)),
                            click.style(
                                u'{:3d}'.format(int(percent)),
                                fg='red' if percent < 60 else 'magenta' if percent < 80 else 'green',
                            ),
                            graph,
                        ),
                        color=True,
                    )
                    last_prefix = 0
                graph = ''
                glyphs = 0

        if total > 0:
            graph += percent_to_bar(float(bad) / float(total))
            glyphs += 1

        if glyphs == 0:
            graph = click.style('no statements', dim=True, fg='black')

        if printed_fname:
            click.echo(u'{} {}'.format(u' ' * max_fname, graph), color=True)
        else:
            printed_fname = True
            thisname = (u' ' * last_prefix) + short[last_prefix:]
            thisname = click.style(fname[common:common + last_prefix], fg='black') + click.style(short[last_prefix:], bold=True)
            click.echo(
                u'{}{} {} {}'.format(
                    thisname,
                    u' ' * (max_fname - len(short)),
                    click.style(
                        u'{:3d}'.format(int(percent)),
                        fg='red' if percent < 60 else 'magenta' if percent < 80 else 'green',
                    ),
                    graph,
                ),
                color=True,
            )
        graph = ''
        glyphs = 0
