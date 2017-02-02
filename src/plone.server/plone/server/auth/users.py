

ROOT_USER_ID = 'root'
ANONYMOUS_USER_ID = 'Anonymous User'


class RootUser(object):
    def __init__(self, password):
        self.id = ROOT_USER_ID
        self.password = password
        self.groups = ['Managers']
        self._roles = {}
        self._properties = {}


class PloneUser(object):

    def __init__(self, request):
        self.id = 'plone'
        self.request = request
        self._groups = []
        self._roles = {}
        self._permissions = {}
        self._properties = {}

    @property
    def groups(self):
        return self._groups

    @property
    def roles(self):
        return self._roles

    @property
    def permissions(self):
        return self._permissions


class AnonymousUser(PloneUser):

    def __init__(self, request):
        super(AnonymousUser, self).__init__(request)
        self.id = ANONYMOUS_USER_ID
