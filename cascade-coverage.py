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

show_comments = True
#line_height = 12  # maybe "box_size" or "statement_size" or similar? it's width too
line_height = 3
#line_height = 2

for fname in cov.data.measured_files():
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
                break

    if covdata.numbers.n_statements == 0:
        print('no statements, ignoring:', fname)
        continue

    # can't we derive this info. from stuff in coverage?
    # "statements"/n_statements isn't every line
    if show_comments:
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

big_line = max(10, line_height * 4)
fnt = ImageFont.truetype('/home/mike/dot-files/fonts/SourceCodePro_FontsOnly-1.017/TTF/SourceCodePro-Regular.ttf', big_line)
fnt_height = fnt.getsize('0')[1]
print("HEIGHT", fnt_height)

tinyfnt = ImageFont.truetype('/home/mike/dot-files/fonts/SourceCodePro_FontsOnly-1.017/TTF/SourceCodePro-Regular.ttf', line_height)

column_chars = 80
column_width = tinyfnt.getsize('0' * column_chars)[0]

max_title_chars = int(column_width / fnt.getsize('0')[0])

num_columns = int(math.ceil(2560.0 / column_width))
column_content = []
for x in range(num_columns):
    column_content.append([])

# do the biggest data first
coverage_data.sort(lambda a, b: cmp(a[1].numbers.n_statements, b[1].numbers.n_statements))
coverage_data.reverse()

def column_height(col):
    return sum(map(lambda x: x[2], col), 0)

for (fname, covdata, lines) in coverage_data:
    # find shortest column
    heights = map(column_height, column_content)
    min_height = min(heights)
    #print("HEIGHTS", heights, "min", min_height)
    idx = heights.index(min_height)
    #print("index:", idx)
    column_content[idx].append((fname, covdata, lines))
#    if lines == 1944:
#        print("DING", idx, column_content[idx])

width = num_columns * column_width
max_column_height = max(map(column_height, column_content))
height = line_height * max_column_height

print("HEIGHTS", map(column_height, column_content))
for col in column_content:
    print('  ', map(lambda x: x[2], col))
print("MAX", max_column_height)

img = Image.new('RGBA', (width, height), (0, 0, 0))
draw = ImageDraw.Draw(img)

from pygments import highlight
from pygments.token import Token
from pygments.lexers import get_lexer_by_name
from pygments.formatter import Formatter

def parse_color(col):
    r = int(col[:2], 16)
    g = int(col[2:4], 16)
    b = int(col[4:6], 16)
    return (r, g, b)

class ImageFormatter(Formatter):

    def __init__(self, draw, fnt, origin, covdata, **kw):
        Formatter.__init__(self, **kw)
        self.draw = draw
        self.fnt = fnt
        self.origin = origin
        self.covdata = covdata

        #: maps Token -> r,g,b triple
        self.token_color = {}

        for (token, style) in self.style:
            if 'color' in style and style['color']:
                c = parse_color(style['color'])
                self.token_color[token] = c
                #print('  {} -> {}'.format(token, c))

    def draw_line_background(self, line_index):
        bg = (32, 32, 32, 255)
        if (line_index + 2) in self.covdata.missing:
            bg = (128, 32, 32)
        elif (line_index + 2) in self.covdata.branch_lines():
            bg = (128, 128, 32)
        elif (line_index + 2) in self.covdata.statements:
            bg = (32, 44, 32)
        x = self.origin[0]
        y = self.y + line_height # self.origin[1] + (line_height * line_index)
        self.draw.rectangle((x, y, x + column_width, y + line_height - 2), fill=bg)
#        elif not show_comments:
#            continue


    def format(self, tokensource, outfile):
        self.x = self.origin[0]
        self.y = self.origin[1]
        index = 0
        self.draw_line_background(index)

        for ttype, value in tokensource:
            try:
                c = self.token_color[ttype]
            except KeyError:
                c = (32, 32, 32)

            try:
                text = str(value).encode('utf8')
            except:
                text = ''
            for snip in text.splitlines(True):
                size = self.draw_text(snip, c, index)
                if '\n' in snip:
                    index += 1
                    self.draw_line_background(index)
                    self.y += size[1]
                    self.x = self.origin[0]

    def draw_text(self, text, color, line_index):
        # FIXME need to clip text at column-border -- but can't just
        # text[:80] because we get these in color-specific chunks, I
        # think? E.g. each differently-styled token...
        size = self.fnt.getsize(text)
        self.draw.text((self.x, self.y - 2), text.rstrip(), fill=color, font=self.fnt)
        self.x += size[0]
        return size

if False:
    fname = column_content[0][0][0]
    print("FNAME", fname)
    raw = open(fname, 'r').read()
    fmt = ImageFormatter(raw, style='monokai')
    lines = highlight(
        open(fname, 'r').read(),
        get_lexer_by_name('python'),
        formatter=fmt#draw, x, y, line_height),
    )
    print("lines '{}'".format(lines))
    print("got", fmt.found)
    print("wanted", len(fmt.raw.split('\n')))
    sys.exit(0)


for column in range(num_columns):
    x = column * column_width
    y = 0
    for (fname, covdata, lines) in column_content[column]:
        percent = float(lines - covdata.numbers.n_missing) / lines
        barmax = column_width - 1
        pwid = math.ceil(barmax * percent)

        if True:
            draw.rectangle([x, y, x + pwid, y + fnt_height - 1], fill=(32, 96, 32, 255))
            draw.rectangle([x + pwid, y, x + barmax, y + fnt_height - 1], fill=(96, 32, 32, 255))
        #draw.rectangle([x, y, x + barmax, y + fnt_height - 1], fill=(96, 32, 32, 255))

        trunc_fname = fname
        while fnt.getsize(trunc_fname)[0] > column_width:
            trunc_fname = trunc_fname[1:]
        text_x = column_width - fnt.getsize(trunc_fname)[0]  # negative is OKAY? not really
        text_x += x
        draw.text((text_x, y - 2), trunc_fname, fill=(255, 255, 255, 128), font=fnt)
        y += fnt_height

        if True:
            frmt = ImageFormatter(draw, tinyfnt, (x, y), covdata, style='monokai')
            highlight(open(fname, 'r').read(), get_lexer_by_name('python'), formatter=frmt)
            y += line_height * len(open(fname, 'r').readlines())

        else:
            data = open(fname, 'r').readlines()
            #for line in covdata.statements:#range(lines):
            for line in range(len(data)):#range(lines):
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
                elif not show_comments:
                    continue
                draw.rectangle([x, y, x + column_width - 1, y + line_height - 2], fill=color, outline=color)
                draw.text((x, y - 2), data[line - 1].rstrip()[:column_chars], font=tinyfnt, fill=textcolor)
                y += line_height



print("total coverage", float(total_statements - total_missing) / total_statements * 100.0)
img.save('coverage_cascade.png')

