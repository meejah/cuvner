from __future__ import print_function, absolute_import

import sys
import math
from os.path import abspath

import colors
import click
import six

from pygments import highlight
from pygments.formatters import Terminal256Formatter, TerminalFormatter
from pygments.lexers import get_lexer_by_name

import coverage

from cuv.analysis import CoverageAnalysis, create_analysis
from cuv.util import print_banner, paged_echo
from unidiff import PatchSet


def diff_coverage_files(file_a, file_b, cfg):
    """
    This shows the difference in lines covered between two coverage files
    """

    data_a = coverage.Coverage(data_file=file_a)
    data_a.load()

    data_b = coverage.Coverage(data_file=file_b)
    data_b.load()

    click.echo(
        "Comparing {} vs {}".format(
            click.style(file_a, fg='red'),
            click.style(file_b, fg='green'),
        )
    )

    diff_coverage_data(data_a, data_b, cfg)


def diff_coverage_data(data_a, data_b, cfg):
    """
    """
    files_a = set(data_a.data.measured_files())
    files_b = set(data_b.data.measured_files())
    common_files = files_a.intersection(files_b)

    for fname in common_files:
        a = create_analysis(data_a, fname)
        b = create_analysis(data_b, fname)
        a_has = []
        b_has = []

        if a.statements != b.statements:
            click.echo("{}: statement mismatch".format(fname))
        else:
            for x in a.statements:
                if x in a.missing:
                    if x not in b.missing:
                        b_has.append(x)
                else:
                    if x in b.missing:
                        a_has.append(x)
            if a_has != [] or b_has != []:
                click.echo(
                    "{}: {} vs. {}".format(
                        fname,
                        click.style(','.join([str(s) for s in a_has]), fg='red'),
                        click.style(','.join([str(s) for s in b_has]), fg='green'),
                    )
                )


def diff_color(input_file, cfg):
    """
    colorizes a diff file
    """
    cov = cfg.data

    with paged_echo() as pager:
        term_width = click.get_terminal_size()[0]
        modified = []
        measured = cov.data.measured_files()
        diff = PatchSet(input_file)
        for thing in diff:
            if thing.is_modified_file or thing.is_added_file:
                target = thing.target_file
                if target.startswith('b/') or target.startswith('a/'):
                    target = target[2:]
                if abspath(target) in measured:
                    covdata = cov._analyze(abspath(target))
                    modified.append((thing, covdata))
#                    pager.echo(abspath(target))
                else:
                    msg = "skip: {}".format(target)
                    msg = msg + (' ' * (term_width - len(msg)))
                    pager.echo(colors.color(msg, bg='yellow', fg='black'))

        for (patch, covdata) in modified:
            fname = str(patch.target_file) + (' ' * (term_width - len(patch.target_file)))
            pager.echo(colors.color(fname, bg='cyan', fg='black'))
            for hunk in patch:
                for line in hunk:
                    kw = dict()
                    if line.is_added:
                        if line.target_line_no in covdata.missing:
                            pager.echo(colors.color(u'\u258f', fg='red', bg=52), nl=False, color=True)
                            kw['bg'] = 52
                        else:
                            pager.echo(colors.color(u'\u258f', fg='green'), nl=False, color=True)
                    else:
                        pager.echo(' ', nl=False)
                    out = str(line)
                    if line.is_added:
                        kw['fg'] = 'green'
                    elif line.is_removed:
                        kw['fg'] = 'red'
                    pager.echo(colors.color(out, **kw))
        return

        target_fname = abspath(target_fname)
        for fname in cov.data.measured_files():
            if target_fname == abspath(fname):
                match.append(fname)

        if len(match) != 1:
            if len(match) == 0:
                # this file wasn't in the coverage data, so we just dump
                # it to stdout as-is. (FIXME: ideally, also
                # syntax-highlighted anyway)
                with open(target_fname, 'r') as f:
                    for line in f.readlines():
                        sys.stdout.write(line)
                return
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
        # background color after each reset (for "uncovered" lines)...  so
        # I didn't do that. Instead we just hack it by splitting on the
        # reset codes (see below)

        formatter = TerminalFormatter(style=style)
        lines = highlight(
            open(fname).read(), get_lexer_by_name('python'),
            formatter=formatter,
        )
        lines = lines.split(u'\n')

        for (i, line) in enumerate(lines):
    #        assert type(line) is unicode
            spaces = fill - len(colors.strip_color(line))
            spaces = u' ' * spaces
            if (i + 1) not in covdata.missing:
                if (i + 1) in covdata.excluded:
                    line = colors.strip_color(line)
                    pager.echo(colors.color(u'\u258f', fg=46, bg=236) + colors.color(line + spaces, bg=236, fg=242), color=True)
                elif cfg.branch and (i + 1) in covdata.branch_lines():
                    line = colors.strip_color(line)
                    pager.echo(colors.color(u'\u258f', bg=52, fg=160) + colors.color(line + spaces, bg=52), color=True)
                else:
                    pager.echo(u'{}{}{}'.format(colors.color(u'\u258f', fg=46), line, spaces), color=True)
            else:
                # HACK-O-MATIC, uhm. Yeah, so what we're doing here is
                # splitting the output from the formatter on the ANSI
                # "reset" code, and the re-assembling it with the "52"
                # (dark red) background color. I appoligize in advance;
                # PRs with improvements encouraged!
                reset_code = u"\x1b[39;49;00m"
                segments = (line + spaces).split(reset_code)
                reset_plus_bg = u"\x1b[39;49;00m\x1b[39;49;48;5;52m"
                out = u"\x1b[39;49;48;5;52m" + reset_plus_bg.join(segments)
                pager.echo(colors.color(u'\u258f', bg=52, fg=160) + out, color=True)
                # (on the plus side: this preserves syntax-highlighting
                # while also getting a background color on the whole
                # line)
