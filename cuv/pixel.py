#!/usr/bin/env python

import sys
import math
import random
import pkg_resources
from os.path import split

from PIL import Image, ImageDraw, ImageFont
from cuv.analysis import CoverageAnalysis, create_analysis
import click


def pixel_vis(cfg, pixel_size, height, show_image):
    target_fname = 'coverage_pixel.png'
    randomize_brightness = False
    show_comments = True
    header_size = 8
    column_chars = 80
    maximum_height = height
    biggest_prefix = None
    total_statements = 0
    total_missing = 0
    total_files = 0
    total_covered = 0
    frmt = None

    coverage_data = []
    for fname in cfg.measured_filenames():
        try:
            covdata = create_analysis(cfg.data, fname)
        except Exception as e:
            click.echo("{}: {}".format(fname, e))
            continue

        if biggest_prefix is None:
            biggest_prefix = fname
        else:
            for (i, ch) in enumerate(fname[:len(biggest_prefix)]):
                if ch != biggest_prefix[i]:
                    biggest_prefix = biggest_prefix[:i]
                    break

        if len(covdata.statements) == 0:
            continue

        # can't we derive this info. from stuff in coverage?
        # "statements"/n_statements isn't every line
        if show_comments:
            lines = len(open(covdata.fname).readlines())
        else:
            # actually, ignoring comments etc seems more-sane sometimes
            # ...but then the code doesn't "look" right :/
            lines = len(covdata.statements)

        total_statements += lines
        total_missing += len(covdata.missing)
        total_files += 1
        total_covered += (len(covdata.statements) - len(covdata.missing))
        coverage_data.append((fname, covdata, lines))

    fnt = ImageFont.truetype(
        pkg_resources.resource_filename("cuv", "source-code-pro.ttf"),
        header_size,
    )
    fnt_height = fnt.getsize('0')[1]

    column_width = (column_chars * pixel_size[0]) + 2

    lines_per_column = maximum_height / pixel_size[1]
    total_pixel_height = (pixel_size[1] * total_statements) + (len(coverage_data) * (fnt_height + 2))

    num_columns = int(math.ceil(total_pixel_height / float(maximum_height)))
    click.echo(u"need {} columns for {} lines".format(num_columns, total_statements))
    # 3 for vertical 'total-coverage' bar on left
    width = (num_columns * column_width) + 3
    height = maximum_height
    click.echo(u"size: {}x{}".format(width, height))
    img = Image.new('RGBA', (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)

    if False:
        # do the biggest data first
        coverage_data.sort(lambda a, b: cmp(len(a[1].statements), len(b[1].statements)))
        coverage_data.reverse()

    from pygments import highlight
    from pygments.token import Token
    from pygments.lexers import get_lexer_by_name
    from pygments.formatter import Formatter

    def parse_color(col):
        r = int(col[:2], 16)
        g = int(col[2:4], 16)
        b = int(col[4:6], 16)
        return (r, g, b, 64)

    class Position(object):
        def __init__(self, x=0, y=0):
            self.x = x
            self.y = y
    pos = Position(3, 0)

    class ImageFormatter(Formatter):

        def __init__(self, draw, covdata, origin, **kw):
            Formatter.__init__(self, **kw)
            self.draw = draw
            self.covdata = covdata
            self.origin = origin

            #: maps Token -> r,g,b triple
            self.token_color = {}

            for (token, style) in self.style:
                if 'color' in style and style['color']:
                    c = parse_color(style['color'])
                    self.token_color[token] = c

        def draw_line_background(self, line_index, alpha=255):
            bg = (32, 32, 32, alpha)
            if (line_index + 1) in self.covdata.missing:
                bg = (164, 32, 32, alpha)
#            elif (line_index + 1) in self.covdata.branch_lines():
#                bg = (128, 128, 32, alpha)
            elif (line_index + 1) in self.covdata.statements:
                bg = (32, 44, 32, alpha)
            self.draw.rectangle((self.origin.x, pos.y, self.origin.x + column_width - 2, pos.y + pixel_size[1]), fill=bg)
            return bg

        def format(self, tokensource, outfile):
            index = 0
            bg = self.draw_line_background(index)

            for ttype, value in tokensource:
                try:
                    color = self.token_color[ttype]
                except KeyError:
                    color = (255, 255, 0, 255)

                text = u'{}'.format(value)

                fg_amt = 1
                bg_amt = 7
                color = (
                    int(((bg[0] * bg_amt) + (color[0] * fg_amt)) / (fg_amt + bg_amt)),
                    int(((bg[1] * bg_amt) + (color[1] * fg_amt)) / (fg_amt + bg_amt)),
                    int(((bg[2] * bg_amt) + (color[2] * fg_amt)) / (fg_amt + bg_amt)),
                    255
                )

                for snip in text.splitlines(True):
                    self.draw_text(snip, color, index)
                    assert snip.count('\n') <= 1
                    if '\n' in snip:
                        index += 1
                        bg = self.draw_line_background(index)

        def draw_text(self, text, color, line_index):
            assert text.count('\n') <= 1
            for ch in text:
                if pos.x >= self.origin.x + column_width:
                    pos.x = self.origin.x
                    break
                if ch not in ' \t\n\r':
                    if randomize_brightness:
                        dimness = 16 - random.randrange(32)
                        c = [x + dimness for x in color]
                        c[3] = 255
                        c = tuple(c)
                    else:
                        c = color
                    self.draw.rectangle((pos.x, pos.y, pos.x + pixel_size[0], pos.y + pixel_size[1]), fill=c)
                pos.x += pixel_size[0]
            # we ensure there's at most one newline in "format"
            if u'\n' in text:
                pos.y += pixel_size[1]
                pos.x = self.origin.x
            if pos.y > maximum_height:
                pos.y = 0
                pos.x = self.origin.x + column_width
                self.origin = Position(pos.x, pos.y)

    column = row = 0
    for (fname, covdata, lines) in coverage_data:
        percent = float(lines - len(covdata.missing)) / lines
        barmax = column_width - 2
        pwid = math.ceil(barmax * percent)

        if True:
            pos.y += pixel_size[1] + 1
            draw.rectangle([pos.x, pos.y, pos.x + pwid, pos.y + fnt_height - 1], fill=(32, 96, 32, 255))
            draw.rectangle([pos.x + pwid, pos.y, pos.x + barmax, pos.y + fnt_height - 1], fill=(96, 32, 32, 255))

        trunc_fname = fname
        while fnt.getsize(trunc_fname)[0] > column_width:
            trunc_fname = trunc_fname[1:]
        text_x = column_width - fnt.getsize(trunc_fname)[0]  # what if negative?
        text_x += pos.x
        draw.text((text_x, pos.y - 2), trunc_fname, fill=(255, 255, 255, 128), font=fnt)
        pos.y += fnt_height

        if True:
            new_x = pos.x
            if frmt:
                new_x = frmt.origin.x
            frmt = ImageFormatter(draw, covdata, Position(new_x, pos.y), style='monokai')
            highlight(open(fname, 'r').read(), get_lexer_by_name('python'), formatter=frmt)

    prct = float(total_statements - total_missing) / total_statements
    click.echo(u"total coverage: {}%".format(int(prct * 100)))
    prct_y = height * prct
    draw.rectangle([0, 0, 1, prct_y], fill=(0, 200, 0, 255))
    draw.rectangle([0, prct_y + 1, 1, height], fill=(200, 0, 0, 255))
    fname = 'coverage_cascade_pixel.png'
    img.save(fname)
    click.echo(u"wrote '{}'".format(fname))
    if show_image:
        img.show()
