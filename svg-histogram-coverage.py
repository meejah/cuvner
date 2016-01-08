#!/usr/bin/env python

from __future__ import print_function

import sys
import math
import cPickle
from os.path import split
from xml.sax.saxutils import escape

import svgwrite

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name


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

    total_statements += covdata.numbers.n_statements
    total_lines += lines
    total_missing += covdata.numbers.n_missing
    total_files += 1
    total_covered += (covdata.numbers.n_statements - covdata.numbers.n_missing)
    coverage_data.append((fname, covdata, lines))

line_height = 16
line_height = 32

max_lines = max(map(lambda x: x[1].numbers.n_statements, coverage_data))
max_width = 1920
#max_width = 1024
#max_width = 512
#max_width = 768
max_lines_per_row = max_width / line_height

wrapped_lines = 0
for (fname, covdata, lines) in coverage_data:
    rows = max_width / (lines * line_height)
    wrapped_lines += rows

print("WRAPPED", wrapped_lines)
width = max_width # * 3
height = (line_height + 1) * (len(coverage_data) + wrapped_lines)
print("height:", height)

coverage_data.sort(lambda a, b: cmp(a[1].numbers.n_statements, b[1].numbers.n_statements))
coverage_data.sort(lambda a, b: cmp(a[0], b[0]))

svgdoc = svgwrite.Drawing(
    filename="histogram-coverage.svg",
#    size=(str(width) + "px", str(height) + "px"),
    size=("100%", "100%"),
    viewBox="0 0 %d %d" % (width, height),
    style="background-color: #073642;",
#    extra=dict(
#    )
)

depth = 0
line_anchor_id = 0
all_file_html = open('histogram-coverage-sourcecode.html', 'w')
all_file_html.write('''
<html>
  <head>
    <style type="text/css">
body, section, article, h2
{
    font-family: source code pro, monospace;
    font-size: 10px;
}

.yes
{
    background-color: #afa;
}
.maybe
{
    background-color: #ff7;
}
.no
{
    background-color: #faa;
}
    </style>
  </head>
  <body>
    <article>
''')
for (fname, covdata, lines) in coverage_data:
    percent = float(lines - covdata.numbers.n_missing) / lines
    percent = float(covdata.numbers.n_statements - covdata.numbers.n_missing) / covdata.numbers.n_statements
    barmax = min(1024, width)
    pwid = math.ceil(barmax * percent)
    y = depth * (line_height + 1)

    all_file_html.write('''\n\n<section>\n  <h2>{fname}</h2>\n  <pre>'''.format(fname=fname))

    if False:
        draw.rectangle([256, y, 256 + pwid, y + line_height - 1], fill=(32, 96, 32, 255))
        draw.rectangle([256 + pwid, y, width, y + line_height - 1], fill=(96, 32, 32, 255))

    if True:
        if True: # names-at-front
            trunc_fname = fname[len(biggest_prefix):].strip()
            #trunc_fname = ('/' + trunc_fname[-29:]).rjust(30, '_')
            tx = -256 # how to get length of string in pixels?
            glyph_width = line_height - 4
            tx = 200 - (len(trunc_fname) * glyph_width)
            svgdoc.add(
                svgdoc.text(
                    trunc_fname, insert=(tx, y + line_height - 2 - 4),
                    fill="#eee",
                    style="font: {}px monospace;".format(glyph_width),
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

        barwidth = 8
        datalines = open(fname, 'r').readlines()
        for line in range(1, lines + 1):
            if line in covdata.missing:
                cls = 'no'
            elif line in covdata.branch_lines():
                cls = 'maybe'
            elif line in covdata.statements:
                cls = 'yes'
            else:
                cls = 'ignore'

            line_anchor_id += 1
            all_file_html.write('''<div class="%s" id="fid_%05d">%s</div>''' % (cls, line_anchor_id, escape(datalines[line - 1].rstrip())))

            color = (32, 32, 32)
            if line in covdata.missing:
                color = (128, 32, 32)
            elif line in covdata.branch_lines():
                #color = (128, 128, 32)
                color = (128, 80, 32)
            elif line in covdata.statements:
                color = (32, 44, 32)
            else:
                continue

            x += barwidth
            if x >= max_width:
                x = 256 + barwidth
                y += line_height + 1
                depth += 1
            if True and barwidth > 2: # gaps-between-lines
                #draw.rectangle((x, y, x + barwidth - 2, y + line_height - 1), fill=color)
                svgdoc.add(
                    svgdoc.rect(
                        insert=(x, y),
                        size=(barwidth - 2, line_height),
                        fill="rgb({},{},{})".format(*color),
                        onmouseover="highlight_line('fid_%05d');" % (line_anchor_id + 1,)
                    )
                )
            else:
                draw.rectangle((x, y, x + barwidth, y + line_height - 1), fill=color)

        if False: ## show-ignored
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
    all_file_html.write('</pre></section>\n\n\n\n')

all_file_html.write('''
    </article>
  </body>
</html>
''')
all_file_html.close()

svgdoc.save()
print(dir(svgdoc))
with open('histogram-coverage.html', 'w') as f:
    f.write(r'''
<html>
  <head>
    <title>coverage: {project}</title>
    <style type="text/css">
body
{{
    background-color: black;
}}
    </style>
  </head>
  <body>
    <header>
      <h2>{project}</h2>
    </header>
    <article>

    <script>
var _last = null;
function highlight_line(anchor) {{
// FIXME pretty cheezy, but works
// --> would rather center it in iframe, highlight it
    if (_last) {{
        _last.element.style.backgroundColor = _last.bg;
    }}
    var e = window.frames[0].document.getElementById(anchor);
    if (e) {{
    var where = e.offsetTop;// - (window.clientHeight / 2);
    window.frames[0].scroll(0, where - 512);
//    e.scrollIntoView(false);
    _last = {{
        "element": e,
        "bg": e.style.backgroundColor,
    }}
    e.style.backgroundColor = '#f0f';
}}
}}
</script>

<svg xmlns="http://www.w3.org/2000/svg" version="1.1"
viewBox="0 0 {width} {height}"
  style="width:70%; height:auto; position:absolute; top:0; left:0; z-index:-1;" src="histogram-coverage.svg">
{svg}
</svg>

  <iframe seamless="seamless" scrolling="no" name="sc" style="position: fixed; top: 0; right: 0; width: 30%; height: 100%; overflow-x: hidden; overflow-y: scroll; background-color: grey; color: black;" src="histogram-coverage-sourcecode.html"></iframe>

    </article>
  </body>
</html>
    '''.format(
        project='project',
        svg=svgdoc.tostring(),
        width=width,
        height=height,
    )
)
print("total coverage", float(total_statements - total_missing) / total_statements * 100.0)
print("missing {} of {} lines".format(total_missing, total_statements))

