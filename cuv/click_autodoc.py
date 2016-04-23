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

class cuv_command(nodes.Element):
    pass

class CarmlCommandDirective(Directive):
    has_content = True
    required_arguments = 1

    def run(self):
        env = self.state.document.settings.env

        node = cuv_command()
        node.line = self.lineno
        node['command'] = self.arguments[0]
        return [node]

    #targetid = "cb-cmd-%d" % env.new_serialno('cb-cmd')
    #targetnode = nodes.target('', '', ids=[targetid])
    #return [targetnode, node]


def find_command(cmd_name):
    from cuv import cli
    return getattr(cli, cmd_name, None)


class AutodocClickFormatter(object):#click.HelpFormatter):
    def __init__(self, cmd):
        self._cmd = cmd
        self._node = nodes.section()
        title = nodes.subtitle()
        title.append(nodes.literal('', 'cuv {}'.format(cmd.name)))
        self._node.append(title)

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
        print("write_usage", prog, args)

    def write_heading(self, heading):
        """Writes a heading into the buffer."""
        print("write_heading")

    def write_paragraph(self):
        """Writes a paragraph into the buffer."""
        print("write_paragram")

    def write_text(self, text):
        """Writes re-indented text into the buffer.  This rewraps and
        preserves paragraphs.
        """

    def write_dl(self, rows, col_max=30, col_spacing=2):
        """Writes a definition list into the buffer.  This is how options
        and commands are usually formatted.

        :param rows: a list of two item tuples for the terms and values.
        :param col_max: the maximum width of the first column.
        :param col_spacing: the number of spaces between the first and
                            second column.
        """
        rows = list(rows)
        print("write_dl", rows)


def document_commands(app, doctree):
    for node in doctree.traverse(cuv_command):
        cmd_name = node.get('command', None)
        cmd = find_command(cmd_name)
        context = cmd.make_context(cmd_name, [])
        print("CONTEXT", context)
        formatter = AutodocClickFormatter(cmd)
        context.make_formatter = lambda: formatter
        cmd.get_help(context)
        node.replace_self(formatter.get_node())
"""
        section = nodes.section()
        title = nodes.subtitle()
        title.append(nodes.literal('', 'cuv {}'.format(cmd.name)))
        section.append(title)
        section.append(nodes.paragraph(text=cmd.help))
        params = nodes.bullet_list()
        section.append(params)
        for param in cmd.params:
            if param.param_type_name == 'argument':
                print(str(param), dir(param))
                item = nodes.list_item()
                item.append(nodes.literal('', str(dir(param))))#"fooo"))
                item.append(nodes.literal('', param.name))
                item.append(nodes.literal('', param.get_help_record(context)))
                params.append(item)
                continue

            item = nodes.list_item()
            arg = '--{}'.format(param.name)
            if param.metavar:
                arg = '--{} {}'.format(param.name, param.metavar)
            item.append(nodes.literal('', arg))
            item.append(nodes.Text(': ' + str(param.help)))
            #item.append(nodes.Text(': ' + str(dir(param))))
            if param.show_default:
                item.append(nodes.Text(' (default: '))
                item.append(nodes.literal('', str(param.default)))
                item.append(nodes.Text(')'))
            params.append(item)

        node.replace_self(section)
"""

def setup(app):
    app.add_directive('cuv_command', CarmlCommandDirective)
    app.connect(str('doctree-read'), document_commands)
