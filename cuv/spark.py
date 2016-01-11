import sys

import six
import colors
import click


def spark_coverage(keywords, cfg, sort=True):
    cov = cfg.data
    total_statements = 0
    total_missing = 0
    total_files = 0
    percents = []
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
        percent = 1.0  # if no statements, it's all covered, right?
        if covdata.numbers.n_statements:
            if cfg.branch:
                percent = float(covdata.numbers.n_statements - covdata.numbers.n_missing - covdata.numbers.n_missing_branches) / covdata.numbers.n_statements
            else:
                percent = float(covdata.numbers.n_statements - covdata.numbers.n_missing) / covdata.numbers.n_statements
        total_statements += covdata.numbers.n_statements
        total_missing += covdata.numbers.n_missing
        total_files += 1

        percents.append(percent)

    if sort:
        percents.sort()
    for percent in percents:
        bar = int(percent * 7)
        click.echo(colors.color(six.unichr(0x2581 + bar), fg=46, bg=124), nl=False)
    click.echo(u'')
