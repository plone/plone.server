class SecurityMap(object):

    def __init__(self):
        self._clear()

    def _clear(self):
        self._byrow = {}
        self._bycol = {}

    def __nonzero__(self):
        return bool(self._byrow)

    def addCell(self, rowentry, colentry, value):
        # setdefault may get expensive if an empty mapping is
        # expensive to create, for PersistentDict for instance.
        row = self._byrow.get(rowentry)
        if row:
            if row.get(colentry) is value:
                return False
        else:
            row = self._byrow[rowentry] = {}

        col = self._bycol.get(colentry)
        if not col:
            col = self._bycol[colentry] = {}

        row[colentry] = value
        col[rowentry] = value

        self._invalidated_interaction_cache()

        return True

    def _invalidated_interaction_cache(self):
        # Invalidate this threads interaction cache
        interaction = queryInteraction()
        if interaction is not None:
            try:
                invalidate_cache = interaction.invalidate_cache
            except AttributeError:
                pass
            else:
                invalidate_cache()

    def delCell(self, rowentry, colentry):
        row = self._byrow.get(rowentry)
        if row and (colentry in row):
            del row[colentry]
            if not row:
                del self._byrow[rowentry]
            col = self._bycol[colentry]
            del col[rowentry]
            if not col:
                del self._bycol[colentry]

            self._invalidated_interaction_cache()

            return True

        return False

    def queryCell(self, rowentry, colentry, default=None):
        row = self._byrow.get(rowentry)
        if row:
            return row.get(colentry, default)
        else:
            return default

    def getCell(self, rowentry, colentry):
        marker = object()
        cell = self.queryCell(rowentry, colentry, marker)
        if cell is marker:
            raise KeyError('Not a valid row and column pair.')
        return cell

    def getRow(self, rowentry):
        row = self._byrow.get(rowentry)
        if row:
            return list(row.items())
        else:
            return []

    def getCol(self, colentry):
        col = self._bycol.get(colentry)
        if col:
            return list(col.items())
        else:
            return []

    def getAllCells(self):
        res = []
        for r in self._byrow.keys():
            for c in self._byrow[r].items():
                res.append((r,) + c)
        return res


class PloneSecurityMap(SecurityMap):

    def __init__(self, context):
        self.context = context

        map = self.context.__acl__.get(self.key)
        if map is None:
            self._byrow = {}
            self._bycol = {}
        else:
            self._byrow = map._byrow
            self._bycol = map._bycol
        self.map = map

    def _changed(self):
        map = self.map
        if map is None:
            map = SecurityMap()
            map._byrow = self._byrow
            map._bycol = self._bycol
            self.context.__acl__[self.key] = map
        else:
            self.context._p_changed = 1

    def addCell(self, rowentry, colentry, value):
        if SecurityMap.addCell(self, rowentry, colentry, value):
            self._changed()

    def delCell(self, rowentry, colentry):
        if SecurityMap.delCell(self, rowentry, colentry):
            self._changed()
