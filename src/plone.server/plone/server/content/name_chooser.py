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
        """See zope.container.interfaces.INameChooser

        We create and populate a dummy container

        >>> from zope.container.sample import SampleContainer
        >>> container = SampleContainer()
        >>> container['foo'] = 'bar'
        >>> from zope.container.contained import NameChooser

        An invalid name raises a ValueError:

        >>> NameChooser(container).checkName('+foo', object())
        Traceback (most recent call last):
        ...
        ValueError: Names cannot begin with '+' or '@' or contain '/'

        A name that already exists raises a KeyError:

        >>> NameChooser(container).checkName('foo', object())
        Traceback (most recent call last):
        ...
        KeyError: u'The given name is already being used'

        A name must be a string or unicode string:

        >>> NameChooser(container).checkName(2, object())
        Traceback (most recent call last):
        ...
        TypeError: ('Invalid name type', <type 'int'>)

        A correct name returns True:

        >>> NameChooser(container).checkName('2', object())
        True

        We can reserve some names by providing a IReservedNames adapter
        to a container:

        >>> from zope.container.interfaces import IContainer
        >>> @zope.component.adapter(IContainer)
        ... @zope.interface.implementer(IReservedNames)
        ... class ReservedNames(object):
        ...
        ...     def __init__(self, context):
        ...         self.reservedNames = set(('reserved', 'other'))

        >>> zope.component.getSiteManager().registerAdapter(ReservedNames)

        >>> NameChooser(container).checkName('reserved', None)
        Traceback (most recent call last):
        ...
        NameReserved: reserved
        """

        if isinstance(name, bytes):
            name = name.decode()
        elif not isinstance(name, unicode):
            raise TypeError("Invalid name type", type(name))

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
        """See zope.container.interfaces.INameChooser

        The name chooser is expected to choose a name without error

        We create and populate a dummy container

        >>> from zope.container.sample import SampleContainer
        >>> container = SampleContainer()
        >>> container['foobar.old'] = 'rst doc'

        >>> from zope.container.contained import NameChooser

        the suggested name is converted to unicode:

        >>> NameChooser(container).chooseName(u'foobar', object())
        u'foobar'

        >>> NameChooser(container).chooseName(b'foobar', object())
        u'foobar'

        If it already exists, a number is appended but keeps the same extension:

        >>> NameChooser(container).chooseName('foobar.old', object())
        u'foobar-2.old'

        Bad characters are turned into dashes:

        >>> NameChooser(container).chooseName('foo/foo', object())
        u'foo-foo'

        If no name is suggested, it is based on the object type:

        >>> NameChooser(container).chooseName('', [])
        u'list'

        """

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