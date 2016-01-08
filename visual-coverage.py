#!/usr/bin/env python

from __future__ import print_function

import sys
import math
import cPickle
from os.path import split

from PIL import Image, ImageDraw, ImageFont

from pygments import highlight
from pygments.formatters import Terminal256Formatter, TerminalFormatter
from pygments.lexers import get_lexer_by_name

if False:
    for i in range(16):
        print('%03d' % (i*16), end='')
        for j in range(16):
            print(colors.color(' ', bg=(i*16+j)), end='')
        print()
#    import os
#    os.exit(0)

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

    if biggest_prefix is None:
        biggest_prefix = fname
    else:
        for (i, ch) in enumerate(fname[:len(biggest_prefix)]):
            if ch != biggest_prefix[i]:
                biggest_prefix = biggest_prefix[:i]
                print("PREFIX", biggest_prefix, fname)
                break

    total_statements += lines
    total_missing += covdata.numbers.n_missing
    total_files += 1
    total_covered += (covdata.numbers.n_statements - covdata.numbers.n_missing)
    coverage_data.append((fname, covdata, lines))

line_height = 4
fnt = ImageFont.truetype('/home/mike/dot-files/fonts/SourceCodePro_FontsOnly-1.017/TTF/SourceCodePro-Regular.ttf',
                         min(20, max(6, 4 * line_height)))
fnt_height = fnt.getsize(' ')[1]

tinyfnt = ImageFont.truetype('/home/mike/dot-files/fonts/SourceCodePro_FontsOnly-1.017/TTF/SourceCodePro-Regular.ttf', line_height)

max_height = 256 * line_height
pixels = (total_statements * line_height) + (len(coverage_data) * fnt_height)
cols = int(math.ceil(float(pixels) / max_height))

height = max_height + (fnt_height * 2)
width = cols * 64 * line_height

img = Image.new('RGBA', (width, height), (0, 0, 0))
draw = ImageDraw.Draw(img)

chop_prefix = len(biggest_prefix)
depth = 0
for (fname, covdata, lines) in coverage_data:
    biggest = max_height / line_height
    x = (depth / biggest) * 64 * line_height
    y = (depth % biggest) * line_height
    percent = float(lines - covdata.numbers.n_missing) / lines
    pwid = math.ceil((64 * line_height) * percent)
    draw.rectangle([x, y, x + pwid, y + fnt_height], fill=(32, 96, 32, 255))
    draw.rectangle([x + pwid, y, x + (64 * line_height), y + fnt_height], fill=(96, 32, 32, 255))
    # -2 because "mostly lower case"
    trunc_fname = fname#[chop_prefix:]
    while fnt.getsize(trunc_fname)[0] > (64 * line_height):
        trunc_fname = trunc_fname[1:]
    text_x = (64 * line_height) - fnt.getsize(trunc_fname)[0]  # negative is OKAY? not really
    text_x += x
    draw.text((text_x, y - 2), trunc_fname, fill=(255, 255, 255, 128), font=fnt)
    depth += int(math.ceil(fnt_height / float(line_height)))

    data = open(fname, 'r').readlines()
    #for line in covdata.statements:#range(lines):
    for line in range(lines):
        textcolor = (64, 64, 64)
        color = (32, 32, 32, 255)
        if line in covdata.missing:
            color = (128, 32, 32)
            textcolor = (200, 200, 200)
        elif line in covdata.branch_lines():
            color = (128, 128, 32)
            textcolor = (20, 20, 20)
        elif line in covdata.statements:
            color = (32, 44, 32)
            textcolor = (200, 200, 200)
        x = (depth / biggest) * 64 * line_height
        y = (depth % biggest) * line_height
        draw.rectangle([x, y, x + (64 * line_height) - 2, y + line_height - 2], fill=color, outline=color)
        draw.text((x, y - 2), data[line - 1].rstrip(), font=tinyfnt, fill=textcolor)
        depth += 1

if False:
    # giant "xx%" translucent coverage output
    bigtxt = Image.new('RGBA', img.size, (255, 255, 255, 0))
    fnt = ImageFont.truetype('/home/mike/dot-files/fonts/SourceCodePro_FontsOnly-1.017/TTF/SourceCodePro-Regular.ttf', int(max_height * 0.75))
    msg = "%2d%%" % (percent * 100.0)
    x = (width / 2) - (fnt.getsize(msg)[0] / 2)
    y = (height / 2) - (fnt.getsize(msg)[1] / 2)
    ImageDraw.Draw(bigtxt).text((x, y), msg, fill=(256, 256, 256, 32), font=fnt)

    foo = Image.alpha_composite(img, bigtxt)
    img = foo

if True:
    percent = total_covered / float(total_covered + total_missing)
    barsize = fnt_height * 2
    bar_w = math.ceil(width * percent)
    draw.rectangle((0, height - barsize, bar_w, height), fill=(32, 128, 0))
    draw.rectangle((bar_w, height - barsize, width, height), fill=(128, 32, 0))
    #draw.rectangle((0, height - barsize, width, height - 15), fill=(0, 0, 0, 255))
    draw.rectangle((0, height - barsize, width, height - barsize), fill=(128, 128, 128, 255))
    draw.text((10, height - barsize + 2), "Overall Coverage: %2d%% (%d of %d statements, %d comments)" % (percent * 100, total_covered, total_covered + total_missing, total_statements - total_covered - total_missing), font=fnt, fill=(255, 255, 255, 255))

print(max_height, height, width)
img.save('coverage.png')

