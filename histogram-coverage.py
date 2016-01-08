#!/usr/bin/env python

from __future__ import print_function

import sys
import math
import cPickle
from os.path import split

from PIL import Image, ImageDraw, ImageFont

from coverage import coverage
cov = coverage()
cov.load()

total_statements = 0
total_missing = 0
total_files = 0
total_covered = 0
coverage_data = []
biggest_prefix = None

for fname in cov.data.measured_files():
    if fname.startswith('/tmp'): continue # XXX REMOVE
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

    total_statements += lines
    total_missing += covdata.numbers.n_missing
    total_files += 1
    total_covered += (covdata.numbers.n_statements - covdata.numbers.n_missing)
    coverage_data.append((fname, covdata, lines))

line_height = 16
fnt = ImageFont.truetype('/home/mike/dot-files/fonts/SourceCodePro_FontsOnly-1.017/TTF/SourceCodePro-Regular.ttf', line_height - 2)

max_lines = max(map(lambda x: x[1].numbers.n_statements, coverage_data))
max_width = 1920
max_lines_per_row = max_width / line_height

wrapped_lines = 0
for (fname, covdata, lines) in coverage_data:
    rows = max_width / (lines * line_height)
    wrapped_lines += rows

print("WRAPPED", wrapped_lines)
width = max_width # * 3
height = (line_height + 1) * (len(coverage_data) + wrapped_lines)

img = Image.new('RGBA', (width, height), (0, 0, 0))
draw = ImageDraw.Draw(img)

coverage_data.sort(lambda a, b: cmp(a[1].numbers.n_statements, b[1].numbers.n_statements))
coverage_data.sort(lambda a, b: cmp(a[0], b[0]))

depth = 0
for (fname, covdata, lines) in coverage_data:
    percent = float(lines - covdata.numbers.n_missing) / lines
    barmax = min(1024, width)
    pwid = math.ceil(barmax * percent)
    y = depth * (line_height + 1)

    if False:
        draw.rectangle([256, y, 256 + pwid, y + line_height - 1], fill=(32, 96, 32, 255))
        draw.rectangle([256 + pwid, y, width, y + line_height - 1], fill=(96, 32, 32, 255))

    if True:
        if True: # names-at-front
            trunc_fname = fname[len(biggest_prefix):]
            size = fnt.getsize(trunc_fname)
            tx = 256 - size[0]
            text_color = (200, 200, 200, 128)
            # okay if tx is negative? i.e. if string longer than 256px
            draw.text((tx, y - 2), trunc_fname, fill=text_color, font=fnt)

        if True:
            x = 256
        else:
            x = 0

        barwidth = 4
        for line in range(lines):
            color = (32, 32, 32)
            if line in covdata.missing:
                color = (128, 32, 32)
#            elif line in covdata.branch_lines():
#                color = (128, 128, 32)
            elif line in covdata.statements:
                color = (32, 44, 32)
            else:
                continue
            x += barwidth
            if x >= max_width:
                x = 256 + 4
                y += line_height + 1
                depth += 1
            if True and barwidth > 2: # gaps-between-lines
                draw.rectangle((x, y, x + barwidth - 2, y + line_height - 1), fill=color)
            else:
                draw.rectangle((x, y, x + barwidth, y + line_height - 1), fill=color)

    if False:
        draw.rectangle([0, y, pwid, y], fill=(32, 96, 32, 255))
        draw.rectangle([pwid, y, barmax, y], fill=(96, 32, 32, 255))

    if False:
        trunc_fname = fname[len(biggest_prefix):]
        text_color = (200, 200, 200, 128)
        if (float(covdata.numbers.n_missing) / covdata.numbers.n_statements) < 0.10:
            text_color = (128, 255, 128, 255)
        draw.text((x + 6, y - 2), trunc_fname, fill=text_color, font=fnt)
    depth += 1

print("total coverage", float(total_statements - total_missing) / total_statements * 100.0)
img.save('coverage_histogram.png')

