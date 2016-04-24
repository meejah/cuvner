'''
This is a simple sphinx extension to provide nice output from "click"
decorated command-lines. Enables markup like this in the Sphinx rst
files::

.. cuv_command:: downloadbundle

Which will document the command "carml downloadbundle"
'''

from contextlib import contextmanager

import click

from docutils import nodes
from docutils.parsers.rst import Directive

class click_command(nodes.Element):
    pass

class CarmlCommandDirective(Directive):
    has_content = True
    required_arguments = 1
    optional_arguments = 1

    def run(self):
        env = self.state.document.settings.env

        node = click_command()
        node.line = self.lineno
        node['command'] = self.arguments
        return [node]

    #targetid = "cb-cmd-%d" % env.new_serialno('cb-cmd')
    #targetnode = nodes.target('', '', ids=[targetid])
    #return [targetnode, node]


def find_command(cmd_name):
    from cuv import cli
    return getattr(cli, cmd_name, None)


class AutodocClickFormatter(object):#click.HelpFormatter):
    def __init__(self, topname, cmd):
        self._topname = topname
        self._cmd = cmd
        self._node = nodes.section()

    def getvalue(self):
        return ''

    def get_node(self):
        return self._node

    @contextmanager
    def section(self, name):
        yield

    @contextmanager
    def indentation(self):
        yield

    def write_usage(self, prog, args='', prefix='Usage: '):
        """Writes a usage line into the buffer.

        :param prog: the program name.
        :param args: whitespace separated list of arguments.
        :param prefix: the prefix for the first line.
        """
        title = nodes.subtitle()
        title.append(nodes.literal('', '{} {}'.format(self._topname, prog)))
        usage = nodes.paragraph()
        usage.append(nodes.Text(prefix))
        usage.append(nodes.literal('', '{} {} {}'.format(self._topname, prog, args)))
        self._node.append(title)
        self._node.append(usage)

    def write_paragraph(self):
        self._last_paragraph = nodes.paragraph()
        self._node.append(self._last_paragraph)

    def write_text(self, text):
        for line in text.split('\n'):
            if not line.strip():
                self.write_paragraph()
            else:
                if line.startswith(' '):
                    block = nodes.literal_block()
                    block.append(nodes.Text(line))
                    self._last_paragraph.append(block)
                else:
                    self._last_paragraph.append(nodes.Text(line))

    def write_dl(self, rows, col_max=30, col_spacing=2):
        """Writes a definition list into the buffer.  This is how options
        and commands are usually formatted.

        :param rows: a list of two item tuples for the terms and values.
        :param col_max: the maximum width of the first column.
        :param col_spacing: the number of spaces between the first and
                            second column.
        """
        rows = list(rows)
        dl = nodes.bullet_list()
        self._node.append(dl)
        for (option, help_text) in rows:
            item = nodes.list_item()
            dl.append(item)
            p = nodes.paragraph()
            p.append(nodes.literal('', option))
            p.append(nodes.Text(': '))
            p.append(nodes.Text(help_text))
            item.append(p)


def document_commands(app, doctree):
    for node in doctree.traverse(click_command):
        cmd = node.get('command', [])
        top = cmd[0]
        cmd_name = cmd[1]
        cmd = find_command(cmd_name)
        context = cmd.make_context(cmd_name, [])
        formatter = AutodocClickFormatter(top, cmd)
        context.make_formatter = lambda: formatter
        cmd.get_help(context)
        node.replace_self(formatter.get_node())

def setup(app):
    app.add_directive('click_command', CarmlCommandDirective)
    app.connect(str('doctree-read'), document_commands)
