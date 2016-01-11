#!/usr/bin/env python

import sys
import math
from os.path import split

import svgwrite
import click


def histogram_coverage(keywords, cfg):
    total_statements = 0
    total_lines = 0
    total_missing = 0
    total_files = 0
    total_covered = 0
    coverage_data = []
    biggest_prefix = None

    cov = cfg.data

    for fname in cov.data.measured_files():
        if len(keywords) > 0:
            match = False
            for arg in keywords:
                if arg in fname:
                    match = True
                    break
            if not match:
                continue

        try:
            covdata = cov._analyze(fname)
        except Exception:
            click.echo(u"failed: {}".format(fname))
            continue

        if biggest_prefix is None:
            biggest_prefix = fname
        else:
            for (i, ch) in enumerate(fname[:len(biggest_prefix)]):
                if ch != biggest_prefix[i]:
                    biggest_prefix = biggest_prefix[:i]
                    break

        if covdata.numbers.n_statements == 0:
            click.echo(u'no statements, ignoring: {}'.format(fname))
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

    line_height = 16

    max_lines = max(map(lambda x: x[1].numbers.n_statements, coverage_data))
    max_width = 1920
    max_width = 1024
    max_lines_per_row = max_width / line_height

    wrapped_lines = 0
    for (fname, covdata, lines) in coverage_data:
        rows = max_width / (lines * line_height)
        wrapped_lines += rows

    width = max_width
    height = (line_height + 1) * (len(coverage_data) + wrapped_lines)

    #coverage_data.sort(lambda a, b: cmp(a[1].numbers.n_statements, b[1].numbers.n_statements))
    #coverage_data.sort(lambda a, b: cmp(a[0], b[0]))
    coverage_data.sort(key=lambda x: x[0])

    svgdoc = svgwrite.Drawing(
        filename="histogram-coverage.svg",
        size=(str(width) + "px", str(height) + "px"),
        style="background-color: #073642;",
    )

    depth = 0
    for (fname, covdata, lines) in coverage_data:
        percent = float(lines - covdata.numbers.n_missing) / lines
        percent = float(covdata.numbers.n_statements - covdata.numbers.n_missing) / covdata.numbers.n_statements
        barmax = min(1024, width)
        pwid = math.ceil(barmax * percent)
        y = depth * (line_height + 1)

        if False:
            draw.rectangle([256, y, 256 + pwid, y + line_height - 1], fill=(32, 96, 32, 255))
            draw.rectangle([256 + pwid, y, width, y + line_height - 1], fill=(96, 32, 32, 255))

        if True:
            if True:
                trunc_fname = fname[len(biggest_prefix):]
                tx = 0  # how to get length of string in pixels?
                # okay if tx is negative? i.e. if string longer than 256px
                svgdoc.add(
                    svgdoc.text(
                        trunc_fname, insert=(tx, y + line_height - 2),
                        fill="#ffffff",
                        style="font: 85% monospace;",
                    )
                )

                greenwidth = int(math.ceil(percent * 256))
                svgdoc.add(
                    svgdoc.rect(
                        insert=(0, y + 2),
                        size=(greenwidth, line_height - 2),
                        fill="rgb(0,255,0)",
                        opacity=0.2,
                    )
                )
                svgdoc.add(
                    svgdoc.rect(
                        insert=(greenwidth, y + 2),
                        size=(256 - greenwidth, line_height - 2),
                        fill="rgb(255,0,0)",
                        opacity=0.2,
                    )
                )

            if True:
                x = 256
            else:
                x = 0

            barwidth = 5
            for line in range(lines):
                color = (32, 32, 32)
                if line in covdata.missing:
                    color = (128, 32, 32)
                elif cfg.branch and line in covdata.branch_lines():
                    color = (128, 80, 32)
                elif line in covdata.statements:
                    color = (32, 44, 32)
                else:
                    continue
                x += barwidth
                if x >= max_width:
                    x = 256 + 3
                    y += line_height + 1
                    depth += 1
                if True and barwidth > 2:  # gaps-between-lines
                    svgdoc.add(
                        svgdoc.rect(
                            insert=(x, y),
                            size=(barwidth - 2, line_height),
                            fill="rgb({},{},{})".format(*color),
                        )
                    )
                else:
                    draw.rectangle((x, y, x + barwidth, y + line_height - 1), fill=color)

            ignored = lines - covdata.numbers.n_statements
            svgdoc.add(
                svgdoc.text(
                    '< {} missing, {} ignored'.format(covdata.numbers.n_missing, ignored),
                    insert=(x + 2, y + line_height - 4),
                    fill=("#ffffff"),
                    style="font: 85% monospace;",
                    opacity=0.2,
                )
            )

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

    svgdoc.save()
    click.echo(u"total coverage {}%".format(float(total_statements - total_missing) / total_statements * 100.0), nl=False)
    click.echo(u" (missing {} of {} lines)".format(total_missing, total_statements))
    click.echo(u"wrote histogram-coverage.svg")
