import sys
import os
import click
import colors
import coverage
import pkg_resources

from cuv.util import find_coverage_data, timer
from cuv.spark import spark_coverage
from cuv.histogram import histogram_coverage
from cuv.less import term_color
from cuv.graph import graph_coverage
from cuv.pixel import pixel_vis
from cuv.diff import diff_color

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


@click.group()
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

    The console commands (e.g. "cuv graph" and "cuv lessopen")
    generally assume a unicode and 256-color capable terminal.
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
        pkg_resources.resource_string("cuv", "README.rst")
    )


@cuv.command()
@click.argument(
    'keyword',
    nargs=-1,
)
@click.pass_obj
def graph(cfg, keyword):
    """
    Console graph of each file's coverage
    """
    try:
        graph_coverage(keyword, cfg)
    except IOError:  # broken pipe, for example
        pass


@cuv.command()
@click.option(
    '--size', '-s',
    help='size of glyphs: 1x1, 1x2, 2,2',
    type=click.Choice(['small', 'medium', 'large']),
    default='small'
)
@click.option(
    '--height', '-H',
    help='Target height of image',
    type=int,
    default=1800,
)
@click.option(
    '--show/--no-show',
    default=False,
)
@click.pass_obj
def pixel(cfg, size, height, show):
    """
    Minimalist view of all code + coverage
    """
    pixel_size = {
        "small": (1, 1),
        "medium": (1, 2),
        "large": (2, 2),
    }[size]
    pixel_vis(cfg, pixel_size, height, show)


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

    For example, to see if your local changes are covered in a Git
    checkout, you can try commands like:

       git diff | cuv diff -
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
    Draws a simple single-line terminal graph of coverage.
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
def hist(cfg, keyword):
    """
    SVG histogram of all covered lines
    """
    try:
        histogram_coverage(keyword, cfg)
    except IOError:
        # ignore broken pipes
        pass
