#!/usr/bin/env python

from __future__ import print_function

import sys
import math
import cPickle
from os.path import split

import svgwrite

from coverage import coverage
cov = coverage()
cov.load()

total_statements = 0
total_lines = 0
total_missing = 0
total_files = 0
total_covered = 0
coverage_data = []
biggest_prefix = None

for fname in cov.data.measured_files():
#    if fname.startswith('/tmp'): continue # XXX REMOVE
    if len(sys.argv) > 1:
        match = False
        for arg in sys.argv[1:]:
            if arg in fname:
                match = True
                break
        if not match:
#            print("skip:", fname)
            continue

    print("doing:", fname)
    try:
        covdata = cov._analyze(fname)
    except Exception:
        print("failed:", fname)
        continue

    if biggest_prefix is None:
        biggest_prefix = fname
    else:
        for (i, ch) in enumerate(fname[:len(biggest_prefix)]):
            if ch != biggest_prefix[i]:
                biggest_prefix = biggest_prefix[:i]
                print("PREFIX", biggest_prefix, fname)
                break

    if covdata.numbers.n_statements == 0:
        print('no statements, ignoring:', fname)
        continue

    # can't we derive this info. from stuff in coverage?
    # "statements"/n_statements isn't every line
    if True:
        lines = len(open(covdata.filename).readlines())
    else:
        # actually, ignoring comments etc seems more-sane sometimes
        # ...but then the code doesn't "look" right :/
        lines = covdata.numbers.n_statements

    total_statements += covdata.numbers.n_statements
    total_lines += lines
    total_missing += covdata.numbers.n_missing
    total_files += 1
    total_covered += (covdata.numbers.n_statements - covdata.numbers.n_missing)
    coverage_data.append((fname, covdata, lines))

coverage_data.sort(lambda a, b: -cmp(a[1].numbers.n_statements, b[1].numbers.n_statements))
#coverage_data.sort(lambda a, b: cmp(a[0], b[0]))


longest_file = coverage_data[0][1].numbers.n_statements
total_lines = sum(map(lambda x: x[1].numbers.n_statements, coverage_data))
columns = max(total_lines / longest_file, 12)
print("biggest", longest_file, total_lines, columns, coverage_data[0][0])
header_size = 40
#header_size = columns * 8.0
header_size = longest_file / 20

aspect = 1.0
line_height = 5
height = (longest_file * line_height) + header_size
width = columns * 64 * line_height


column_width = width / columns
column_y = [0] * columns
col = 0

def shortest_column(cols):
    short = None
    for (i, height) in enumerate(cols):
        if short is None or height < cols[short]:
            short = i
    return short


for (fname, covdata, lines) in coverage_data:
    file_height = lines * line_height
    file_height = (covdata.numbers.n_statements * line_height) + header_size
    col = shortest_column(column_y)
    column_y[col] += file_height
height = max(column_y)
print("columns:", ' '.join(map(str, column_y)))

svgdoc = svgwrite.Drawing(
    filename="vertical-coverage.svg",
#    size=(str(width) + "px", str(height) + "px"),
    size=("100%", "100%"),
    viewBox="0 0 %d %d" % (width, height),
    style="background-color: #073642;",
#    extra=dict(
#    )
)

column_y = [0] * columns
col = 0

show_code = False
for (fname, covdata, lines) in coverage_data:
    percent = float(lines - covdata.numbers.n_missing) / lines
    percent = float(covdata.numbers.n_statements - covdata.numbers.n_missing) / covdata.numbers.n_statements
    barmax = min(1024, width)
    pwid = math.ceil(barmax * percent)
    names_at_front = False
    col = shortest_column(column_y)
    if show_code:
        filedata = open(fname).readlines()

    x = col * column_width
    y = column_y[col]

    file_height = lines * line_height
    file_height = (covdata.numbers.n_statements * line_height) + header_size

    tx = x
    trunc_fname = fname[len(biggest_prefix):]
    svgdoc.add(
        svgdoc.text(
            trunc_fname, insert=(tx, y + 15),
            #fill="#586e75",
            fill="#aaa",
            opacity=0.8,
            style="font: {}px monospace;".format(header_size/4),
        )
    )
    y += 20

    current_color = None
    start_line = None
    for line in range(lines):
        color = (32, 32, 32)
        if line in covdata.missing:
            color = (128, 32, 32)
        elif line in covdata.branch_lines():
            if False: # do-branches
                #color = (128, 128, 32)
                color = (128, 80, 32)
            else:
                color = (32, 44, 32)
        elif line in covdata.statements:
            color = (32, 44, 32)
        else:
            continue
        if current_color != color:
            current_color = color
            if start_line is None:
                start_line = y
            else:
                svgdoc.add(
                    svgdoc.rect(
                        insert=(x, start_line),
                        size=(column_width - 2, (y - start_line) + 1),
                        fill="rgb({},{},{})".format(*current_color),
                        color="rgb(0, 0, 0)",
                    )
                )
                start_line = None
        y += line_height
        if y > height:
            print("OVERRUN!")

        if show_code:
            linedata = filedata[line]
            svgdoc.add(
                svgdoc.text(
                    linedata,
                    insert=(x, y + line_height - 1),
                    fill="rgb(200, 200, 200)",
                    opacity="0.20",
                    style="font: {}px monospace;".format(line_height),
                )
            )

    column_y[col] += file_height



svgdoc.save()
print("total coverage", float(total_statements - total_missing) / total_statements * 100.0)
print("missing {} of {} lines".format(total_missing, total_statements))

