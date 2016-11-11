import zope.component
import zope.interface.declarations
from zope.interface import Interface

from plone.server import _
from plone.server.interfaces import INameChooser
from plone.server.interfaces import IReservedNames, NameReserved

try:
    from ZODB.interfaces import IBroken
except ImportError:
    class IBroken(Interface):
        pass


@zope.interface.implementer(INameChooser)
class NameChooser(object):

    def __init__(self, context):
        self.context = context

    def checkName(self, name, object):
        if not name:
            raise ValueError(
                _("An empty name was provided. Names cannot be empty.")
            )

        if name[:1] in '+@' or '/' in name:
            raise ValueError(
                _("Names cannot begin with '+' or '@' or contain '/'")
            )

        reserved = IReservedNames(self.context, None)
        if reserved is not None:
            if name in reserved.reservedNames:
                raise NameReserved(name)

        if name in self.context:
            raise KeyError(
                _("The given name is already being used")
            )

        return True

    def chooseName(self, name, object):

        container = self.context

        # convert to unicode and remove characters that checkName does not allow
        if isinstance(name, bytes):
            name = name.decode()
        if not isinstance(name, unicode):
            try:
                name = unicode(name)
            except:
                name = u''
        name = name.replace('/', '-').lstrip('+@')

        if not name:
            name = object.__class__.__name__
            if isinstance(name, bytes):
                name = name.decode()

        # for an existing name, append a number.
        # We should keep client's os.path.extsep (not ours), we assume it's '.'
        dot = name.rfind('.')
        if dot >= 0:
            suffix = name[dot:]
            name = name[:dot]
        else:
            suffix = ''

        n = name + suffix
        i = 1
        while n in container:
            i += 1
            n = name + u'-' + str(i) + suffix

        # Make sure the name is valid.  We may have started with something bad.
        self.checkName(n, object)

        return n