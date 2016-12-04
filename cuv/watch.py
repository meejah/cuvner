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
                self._existing_data = new_data

    handler = Handler()
    observer = Observer()
    print("Watching: {}".format(coverage_fname))
    observer.schedule(handler, split(coverage_fname)[0])
    observer.start()
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()
