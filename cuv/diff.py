from __future__ import print_function, absolute_import, unicode_literals

import sys
import math
import shutil
from os.path import abspath, split

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
    files_a = set(data_a.get_data().measured_files())
    files_b = set(data_b.get_data().measured_files())
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
        term_width = shutil.get_terminal_size()[0]
        modified = []
        measured = [
            abspath(p)
            for p in cov.get_data().measured_files()
        ]
        diff = PatchSet(input_file)
        patched_to_measured = match_coverage_files(measured, diff)

        for thing in diff:
            if thing.is_modified_file or thing.is_added_file:
                target = thing.target_file
                if target.startswith('b/') or target.startswith('a/'):
                    target = target[2:]
                target = abspath(target)
                target = patched_to_measured.get(target, target)
                if target in measured:
                    covdata = cov._analyze(abspath(target))
                    modified.append((thing, covdata))
#                    pager.echo(abspath(target))
                else:
                    msg = "skip: {}".format(target)
                    msg = msg + (' ' * (term_width - len(msg)))
                    pager.echo(colors.color(msg, bg='yellow', fg='black'))

        total_added_lines = 0
        total_covered_lines = 0

        for (patch, covdata) in modified:
            fname = str(patch.target_file) + (' ' * (term_width - len(patch.target_file)))
            pager.echo(colors.color(fname, bg='cyan', fg='black'))
            for hunk in patch:
                for line in hunk:
                    kw = dict()
                    if line.is_added:
                        total_added_lines += 1
                        if line.target_line_no in covdata.missing:
                            pager.echo(colors.color(u'\u258c', fg='red', bg=52), nl=False, color=True)
                            kw['bg'] = 52
                        else:
                            total_covered_lines += 1
                            pager.echo(colors.color(u'\u258f', fg='green'), nl=False, color=True)
                    else:
                        pager.echo(' ', nl=False)
                    out = u"{}".format(line).strip()
                    if line.is_added:
                        kw['fg'] = 'green'
                    elif line.is_removed:
                        kw['fg'] = 'red'
                    pager.echo(colors.color(out, **kw))

        if total_added_lines == 0:
            raise click.ClickException("No covered lines at all")

        percent_covered = (total_covered_lines / float(total_added_lines))
        msg = u"{} covered of {} added lines".format(total_covered_lines, total_added_lines)
        print_banner(msg, percent_covered, pager=pager)
        return

        target_fname = abspath(target_fname)
        for fname in cov.get_data().measured_files():
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

        fill = min(shutil.get_terminal_size()[0], 80)
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



def match_coverage_files(measured, diff):
    """
    :param list measured: absolute paths of files in the coverage data
    :param PatchSet diff: the diff (containing relative paths) we're comparing

    basically trying to reverse-enginner the "base path" of both the
    "measured" and "patched" files, assuming that they're the same
    project (e.g. /home/foo/src/project/src/__init__.py might be your
    checkout's file in the diff (so like "a/src/__init__.py" in the
    diff) while
    /home/foo/src/project/.tox/py3/lib/python3.9/site-packages/project/__init__.py
    might be what's in the coverage file)
    """

    patched = []
    for thing in diff:
        if thing.is_modified_file or thing.is_added_file:
            target = thing.target_file
            if target.startswith('b/') or target.startswith('a/'):
                target = target[2:]
            patched.append(abspath(target))


    patched_to_measured = {}

    for m in measured:
        # XXX FIXME pathlib or something
        m_segs = m.split("/")
        best = None
        for p in patched:
            p_segs = p.split("/")
            end = -1
            while m_segs[end] == p_segs[end] and -end < len(m_segs):
                end = end - 1
            if best is None or end < best[0]:
                best = end, p
        # we demand "< -1" because at least the filename itself must
        # match
        if best is not None and best[0] < -1:
            patched_to_measured[best[1]] = m
    return patched_to_measured


def _diff_coverage_statistics(cov, diff_file):
    """
    :returns: a dict containing statistics about coverage of
    differences in the provided diff. Contains the following items:

     - total_added_lines: number of "+" lines in the diff
     - total_covered_lines: number of "+" lines with test-coverage
    """

    modified = []
    measured = [
        abspath(p)
        for p in cov.get_data().measured_files()
    ]

    diff = PatchSet(diff_file, encoding="utf8")
    patched_to_measured = match_coverage_files(measured, diff)

    # XXX code partially duplicated above, in match_coverage_files
    for thing in diff:
        if thing.is_modified_file or thing.is_added_file:
            target = thing.target_file
            if target.startswith('b/') or target.startswith('a/'):
                target = target[2:]
            target = abspath(target)
            target = patched_to_measured.get(target, target)
            if target in measured:
                covdata = cov._analyze(target)
                modified.append((thing, covdata))

    # this chunk is "pretty" similar to the stuff in diff_cov so
    # it might be worth combining, somehow?
    total_added_lines = 0
    total_covered_lines = 0

    for (patch, covdata) in modified:
        for hunk in patch:
            for line in hunk:
                if line.is_added:
                    total_added_lines += 1
                    if line.target_line_no not in covdata.missing:
                        total_covered_lines += 1
    return {
        "total_added_lines": total_added_lines,
        "total_covered_lines": total_covered_lines,
    }


def diff_report(input_file, cfg):
    """
    produces a summary report about a diff
    """
    cov = cfg.data

    stats = _diff_coverage_statistics(cov, input_file)

    percent_covered = (stats["total_covered_lines"] / float(stats["total_added_lines"])) * 100.0
    click.echo(
        u"{percent:.1f}%: {covered} covered of {added} added lines (leaving {missing} missing)".format(
            percent=percent_covered,
            covered=stats["total_covered_lines"],
            added=stats["total_added_lines"],
            missing=(stats["total_added_lines"] - stats["total_covered_lines"]),
        )
    )
