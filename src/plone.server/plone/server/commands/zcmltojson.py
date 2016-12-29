from plone.server import configuration
from plone.server.commands import Command


class ZCML2HJSONCommand(Command):
    description = 'Convert zcml to hjson'

    def get_parser(self):
        parser = super(ZCML2HJSONCommand, self).get_parser()
        parser.add_argument('-i', '--input', help='ZCML filepath')
        parser.add_argument('-o', '--output', help='HJSON output filepath')
        return parser

    def make_app(self, settings):
        pass

    def run(self, arguments, settings, app):
        with open(arguments.input) as fi:
            output_txt = configuration.convert_zcml_to_hjson(fi)
            with open(arguments.output, 'w') as output:
                output.write(output_txt)
