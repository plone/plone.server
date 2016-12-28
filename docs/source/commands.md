# Commands

You can provide your own CLI commands for plone.server through a simple interface.


## Available commands

* pserver: run the http rest api server
* pmigrate: run available migration steps
* pcli: command line utility to run manually RUN API requests with
* pshell: drop into a shell with root object to manually work with
* pcreate: use cookiecutter to generate plone.server applications


## Creating commands

plone.server provides a simple API to write your own CLI commands.


Here is a minimalistic example:

```python

from plone.server.commands import Command
class MyCommand(Command):

    def get_parser(self):
        parser = super(MyCommand, self).get_parser()
        # add command arguments here...
        return parser

    def run(self, arguments, settings, app):
        pass

```

Then, in your setup.py file, include an entry point like this for your command:

```python
  setup(
    entry_points={
      'console_scripts': [
            'mycommand = my.package.commands:MyCommand'
      ]
  })
```
