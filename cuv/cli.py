import sys
import os
import click
import colors
import coverage
import pkg_resources
import subprocess

from pygments import highlight
from pygments.formatters import TerminalFormatter
from pygments.lexers import get_lexer_by_name

from cuv.util import find_coverage_data, timer
from cuv.spark import spark_coverage
from cuv.less import term_color
from cuv.graph import graph_coverage
from cuv.diff import diff_color, diff_coverage_files
from cuv.watch import watch_coverage
from cuv.analysis import create_analysis


class Config(object):
    '''
    Passed as the Click object (@pass_obj) to all CLI methods.
    '''

    #: a coverage.coveage instance; None if we failed to find coverage data
    data = None

    #: True if user said --branch and wants branch-coverage info.
    branch = False

    #: width to use for banners etc (80, or terminal width)
    nice_width = 80

    def measured_filenames(self, keywords=None):
        """
        returns an iterator that yields filenames, one for each file found
        in the coverage data we've currently loaded.

        This also handles filtering; if any filters were configured,
        you'll only get instances which get past the filter.
        """

        # XXX should probably move to a helper function that takes a
        # Coverage instance?

        # XXX said helper can take a filter-function too

        # FIXME passing keywords is stupid

        def filter(fname):
            if not fname.endswith('.py'):
                return True
            if [x for x in fname.split(os.path.sep) if x.startswith('test')]:
                return True
            if self.exclude:
                for ex in self.exclude:
                    if ex in fname:
                        print("excluding:", fname)
                        return True
            if keywords:
                found = False
                for k in keywords:
                    if k in fname:
                        found = True
                if not found:
                    return True
            return False

        if self.data is None:
            click.echo("No coverage data foud.")
            raise click.Abort

        for fname in self.data.data.measured_files():
            if not filter(fname):
                yield fname


class DefaultCmdGroup(click.Group):
    """
    I make 'lessopen' the default command.
    """
    def get_command(self, ctx, cmd_name):
        cmd = click.Group.get_command(self, ctx, cmd_name)
        if cmd is None:
            if os.path.exists(cmd_name):
                ctx.args.insert(0, cmd_name)
                return click.Group.get_command(self, ctx, 'lessopen')
            return click.Group.get_command(self, ctx, cmd_name)
        return cmd


@click.group(cls=DefaultCmdGroup)
@click.option(
    'coverage_fname',
    '--coverage', '-c',
    help="File to load coverage data from",
    type=click.Path(exists=True),
    default=None,
)
@click.option(
    '--branch/--no-branch', '-b',
    help="Use/show branch coverage if available",
    default=False,
)
@click.option(
    '--exclude', '-e',
    help="Filter out files by keywords",
    multiple=True,
    default=[],
)
@click.pass_context
def cuv(ctx, coverage_fname, exclude, branch):
    """
    Cuv'ner provides ways to visualize your project's coverage data.

    Everything works on the console and assumes a unicode and
    256-color capable terminal. There must be a .coverage file which
    is loaded for coverage data; it is assumed to be in the top level
    of your source code checkout.
    """
    if coverage_fname is None:
        coverage_fname = find_coverage_data('.')
        # coverage_fname still could be None

    cfg = Config()
    ctx.obj = cfg

    cfg.nice_width = min(80, click.get_terminal_size()[0])
    cfg.exclude = exclude

    cfg.branch = branch
    if coverage_fname is not None:
        cfg.data = coverage.Coverage(data_file=coverage_fname)
        cfg.data.load()
    else:
        cfg.data = None


@cuv.command()
def readme():
    """
    View the README
    """
    click.echo_via_pager(
        highlight(
            pkg_resources.resource_string("cuv", "README.rst"),
            get_lexer_by_name('rst'),
            formatter=TerminalFormatter(),
        )
    )


@cuv.command()
@click.argument(
    'keyword',
    nargs=-1,
)
@click.pass_obj
def graph(cfg, keyword):
    """
    Console graph of each file's coverage.
    """
    try:
        graph_coverage(keyword, cfg)
    except IOError:  # broken pipe, for example
        pass


@cuv.command()
@click.argument(
    'input_file',
    type=click.File('r'),
    nargs=1,
    required=False,
)
@click.pass_context
def lessopen(ctx, input_file):
    """
    Syntax + coverage highlighting in console.

    Set 'less' up to use this via the LESSOPEN var:

       export LESSOPEN='| cuv lessopen %s'

    or if you prefer:

       export LESSOPEN='| python -m cuv lessopen %s'

    You may need to provide the full path to 'cuv'. Now, whenever you
    'less' a file within a project that has coverage data, it will be
    syntax-highlighted and coloured according to coverage.
    """

    if input_file is None:
        # okay, we go through some contortions here to allow "cuv
        # lessopen foo/bar.py" to also work if you just do "cuv
        # foo/bar.py" (i.e. make 'lessopen' the default
        # subcommand). See DefaultCmdGroup which does the lookup.
        if ctx.parent is not None and len(ctx.parent.args):
            try:
                input_file = open(ctx.parent.args[0], 'r')
            except IOError as e:
                click.echo(str(e), file=sys.stderr)
                return
        else:
            click.echo(lessopen.get_help(ctx))
            return

    filename = input_file.name

    # act nicely if we just couldn't find any coverage data at all, by
    # printing a warning banner and echoing all the lines (so your
    # "less" still works).
    if ctx.obj.data is None:
        msg = ("cuv: WARNING: couldn't find"
               " any coverage data!").ljust(ctx.obj.nice_width)
        sys.stdout.write(colors.color(msg, bg=226, fg=236) + '\n')
        try:
            for line in open(filename, 'r').readlines():
                sys.stdout.write(line)
        except IOError:
            pass
        return

    # dispatch to the color-izer
    try:
        term_color(filename, ctx.obj)
    except IOError:
        # ignore broken pipes
        pass


@cuv.command()
@click.option(
    "--ignore",
    multiple=True,
)
@click.option(
    "--line-numbers", "-N",
    is_flag=True,
)
@click.pass_context
def next(ctx, ignore, line_numbers):
    """
    Display the next uncovered chunk.

    This finds the next file that has some uncovered lines and then
    runs:

       cuv lessopen <filename> | less -p \u258c -j 4
    """
    cfg = ctx.obj
    for fname in sorted(cfg.measured_filenames()):
        if any([ign in fname for ign in ignore]):
            continue
        data = create_analysis(cfg.data, fname)
        if data.missing:
            subprocess.call(
                u'cuv lessopen {} | less {} -p \u258c -j 4'.format(fname, '-N' if line_numbers else ''),
                shell=True,
            )
            return


@cuv.command()
@click.argument(
    "input_files",
    type=click.File('r'),
    nargs=2,
    required=True,
)
@click.pass_context
def diffcuv(ctx, input_files):
    """
    Difference between two given .coverage files.

    This will show you which lines are covered by one of the coverage
    files but not the other (or vice-versa).
    """
    assert len(input_files) == 2
    diff_coverage_files(input_files[0].name, input_files[1].name, ctx.obj)


@cuv.command()
@click.argument(
    'input_file',
    type=click.File('r'),
    nargs=1,
    required=False,
)
@click.pass_context
def diff(ctx, input_file):
    """
    Color a diff by its coverage.

    This prints out the whole diff as you would expect, but any added
    ("+") lines in the diff get a red background if they are not
    covered.

    For example, to see if your local changes are covered in a Git
    checkout:

       git diff | cuv diff -

    To see if your whole branch is covered:

       git diff master...HEAD | cuv diff -
    """
    if input_file is None:
        click.echo(diff.get_help(ctx))
        return

    diff_color(input_file, ctx.obj)


@cuv.command()
@click.argument(
    'keyword',
    nargs=-1,
)
@click.option(
    '--sort/--no-sort',
    default=True,
)
@click.pass_obj
def spark(cfg, keyword, sort):
    """
    Single-line terminal graph of coverage.
    """
    try:
        spark_coverage(keyword, cfg, sort=sort)
    except IOError:
        # ignore broken pipes
        pass


@cuv.command()
@click.argument(
    'keyword',
    nargs=-1,
)
@click.pass_obj
def watch(cfg, keyword):
    """
    Console graph of each file's coverage.
    """
    try:
        watch_coverage(keyword, cfg)
    except IOError:  # broken pipe, for example
        pass
