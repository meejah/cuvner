# great kurt-idea: make "lessopen" shit work with this, so "if less a
# file, and a .coverae 'up there somewhere' then highlight it"

# prints out annotated coverage to the terminal, with a
# banner-per-file showing coverage, and a total at the end.

from __future__ import print_function, absolute_import

import sys
import math
from os.path import realpath, join, split
from time import sleep

import coverage
import colors
import click
import six

from pygments import highlight
from pygments.formatters import Terminal256Formatter, TerminalFormatter
from pygments.lexers import get_lexer_by_name

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from . import util
from .analysis import CoverageAnalysis, create_analysis
from .diff import diff_coverage_data


def show_missing(data, file_coverage, common):
    max_fname = max([len(nm) - common for nm in file_coverage])
    format_str = u'{:>%d}: {}' % (max_fname,)
    width = click.get_terminal_size()[0]

    for fname in file_coverage:
        analysis = create_analysis(data, fname)
        if len(analysis.missing):
            print(format_str.format(fname[common:], analysis._missing_formatted))

def _new_covered_lines(data_a, data_b, cfg):
    """
    """
    files_a = set(data_a.data.measured_files())
    files_b = set(data_b.data.measured_files())
    common_files = files_a.intersection(files_b)

    new_coverage = {}
    for fname in common_files:
        a = create_analysis(data_a, fname)
        b = create_analysis(data_b, fname)
        new_covered_lines = []
        if a.statements == b.statements:
            for x in a.statements:
                if x in a.missing:
                    if x not in b.missing:
                        new_covered_lines.append(x)
            if new_covered_lines:
                new_coverage[fname] = new_covered_lines
    return new_coverage


def watch_coverage(keywords, cfg):
    file_coverage = []

    file_coverage = list(cfg.measured_filenames(keywords))
    file_coverage.sort()

    common = util.common_root_path(file_coverage)

    existing_data = cfg.data
    coverage_fname = cfg.data.data_files.filename

    # ugh
    class Handler(FileSystemEventHandler):
        def __init__(self):
            # a real closure!
            self._existing_data = existing_data

        def on_modified(self, event):
            if event.src_path == coverage_fname:
                click.echo("New coverage data:")
                new_data = coverage.Coverage(data_file=coverage_fname)
                new_data.load()
                diff_coverage_data(self._existing_data, new_data, cfg)
                newly_covered = _new_covered_lines(self._existing_data, new_data, cfg)
                self._existing_data = new_data
                click.echo('----')
                click.echo("newly covered:")
                for k, v in newly_covered.items():
                    click.echo("  {}: {}".format(k, v))
                click.echo('----')
                show_missing(self._existing_data, file_coverage, len(common))

    handler = Handler()
    observer = Observer()
    print("Watching: {}".format(coverage_fname))
    observer.schedule(handler, split(coverage_fname)[0])
    observer.start()
    show_missing(existing_data, file_coverage, len(common))
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
