

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

from cuv.util import print_banner, timer, common_root_path
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

    common = len(common_root_path(file_coverage))

    if True:
        lines_per_col = 8
    else:
        max_statements = max([len(d.statements) for name, d in file_coverage])
        lines_per_col = math.ceil(float(max_statements) / float(graph_width))
        if lines_per_col < 8:
            lines_per_col = 8

    max_fname = max([len(nm) - common for nm in file_coverage])
    width = click.get_terminal_size()[0]
    graph_width = width - 13 - max_fname

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

    format_str = u'{:^%d} percent missing' % (max_fname + len('filename') - 4, )
    click.echo(
        format_str.format(
            click.style('filename', bold=True)
        )
    )

    total_lines = 0
    total_missing = 0

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

        total_lines += len(data.statements)
        total_missing += len(data.missing)

        # compute each glyph's total (i.e. each chunk of ~8 lines)
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

                    # XXX also, all this duplicated code :(
                    if len(data.missing) > 0:
                        nice_missing = u' ({})'.format(click.style(u'{:5d}'.format(-len(data.missing)), fg='red'))
                    else:
                        nice_missing = u' ' * 8
                    # XXX unit-tests!! this only gets hit on really-long files
                    click.echo(
                        u'{}{} {}{} {}'.format(
                            thisname,
                            u' ' * (max_fname - len(short)),
                            click.style(
                                u'{:3d}'.format(int(percent)),
                                fg='red' if percent < 60 else 'magenta' if percent < 80 else 'green',
                            ),
                            nice_missing,
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
            click.echo(u'{} {}'.format(u' ' * (max_fname + 12), graph), color=True)
        else:
            printed_fname = True
            thisname = (u' ' * last_prefix) + short[last_prefix:]
            thisname = click.style(fname[common:common + last_prefix], fg='black') + click.style(short[last_prefix:], bold=True)
            # XXX code nearly identical to this above...
            if len(data.missing) > 0:
                nice_missing = u' ({})'.format(click.style(u'{:5d}'.format(-len(data.missing)), fg='red'))
            else:
                nice_missing = u' ' * 8

            click.echo(
                u'{}{} {}{} {}'.format(
                    thisname,
                    u' ' * (max_fname - len(short)),
                    click.style(
                        u'{:3d}'.format(int(percent)),
                        fg='red' if percent < 60 else 'magenta' if percent < 80 else 'green',
                    ),
                    #click.style(u' ({:5d})'.format(-len(data.missing)), fg='red'),
                    nice_missing,
                    graph,
                ),
                color=True,
            )
        graph = ''
        glyphs = 0

    click.echo(
        u'From {} files: {} total lines, {} missing'.format(
            len(file_coverage),
            click.style(str(total_lines), fg='green'),
            click.style(str(total_missing), fg='red'),
        )
    )
