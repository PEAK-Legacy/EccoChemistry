from ecco_dde import EccoDDE, FolderType, format_date, format_datetime
from peak.util.decorators import decorate
import datetime
from decimal import Decimal

Ecco = EccoDDE()

__all__ = [
    'Ecco', 'Item', 'CheckmarkFolder', 'TextFolder', 'PopupFolder',
    'DateFolder', 'NumericFolder',
]


class ItemClass(type):
    """General item class"""
    
    def _query(self, *criteria):
        return self.container._query(*criteria)

    def __iter__(self):
        return self._query()        

    def startswith(self, value):     
        return self._query("IB", value)

    def with_text(self, value):
        return self._query("IC", value)

    def without_text(self, value):
        return self._query("IN", value)

    def __pos__(self):
        return self._query("ia")

    def __neg__(self):
        return self._query("id")





class Item(object):
    """Base class for Ecco items"""

    __metaclass__ = ItemClass

    def __init__(self, id_or_text, **kw):
        if isinstance(id_or_text, basestring):
            vals, attrs = self._attrvalues(kw)
            self.id = Ecco.CreateItem(id_or_text, vals)
            for k, v in attrs: setattr(self, k, v)
        else:
            self.id = id_or_text
            if kw: self.update(**kw)

    def text(self):
        return Ecco.GetItemText(self.id)

    def _set_text(self, value):
        Ecco.SetItemText(self.id, value)

    text = property(text, _set_text)

    decorate(classmethod)
    def _attrvalues(cls, d):
        vals, attrs = [], []
        for k, v in d.items():
            if not hasattr(cls, k):
                raise TypeError("No such attribute: ", k)
            descr = getattr(cls, k)
            if isinstance(descr, Container):
                vals.append((descr.folder.id, descr.encode(v)))
            else:
                attrs.append((k, v))
        return vals, attrs

    def update(self, **kw):
        vals, attrs = self._attrvalues(kw)
        Ecco.SetFolderValues(self.id, *zip(*vals))
        for k, v in attrs: setattr(self, k, v)


class Container(object):
    """Find items in a given folder/itemtype"""
    
    def __init__(self, itemtype, folder):
        self.folder = folder
        self.itemtype = itemtype
        self.encode = self.folder.encode

    def _query(self, *criteria):
        for id in Ecco.GetFolderItems(self.folder.id, *criteria):
            yield self.itemtype(id)

    def __iter__(self):
        return self._query()        
    def __gt__(self, value):
        return self._query("GT", self.encode(value))
    def __ge__(self, value):         
        return self._query("GE", self.encode(value))
    def __lt__(self, value):         
        return self._query("LT", self.encode(value))
    def __le__(self, value):         
        return self._query("LE", self.encode(value))
    def __eq__(self, value):         
        return self._query("EQ", self.encode(value))
    def __ne__(self, value):         
        return self._query("NE", self.encode(value))
                                    
    def startswith(self, value):     
        return self._query("TB", value)
    def with_text(self, value):
        return self._query("TC", value)
    def without_text(self, value):
        return self._query("TN", value)
    def __pos__(self):
        return self._query("va")
    def __neg__(self):
        return self._query("vd")

    def __repr__(self):
        return "Container(%s, %r)" % (self.itemtype.__name__, self.folder)

    def setdefault(self, __key, text, **defaults):
        """Look up item by unique key, and create if non-existent"""
        item = self.get(__key)
        if item is None:
            item = self.itemtype(text, **defaults)
            self.folder.__set__(item, __key)
        return item

    def get(self, key, default=None):        
        """Look up item by unique key, or return default"""
        items = list(self==key)
        if len(items)>1:
            raise KeyError("Multiple items for", key)
        if items:
            return items.pop()
        return None

    def __getitem__(self, key):
        """Look up item by unique key"""
        item = self.get(key)
        if item is None:
            raise KeyError(key)
        return item

    def __contains__(self, __key):
        """Does at least one item exist with the given value?"""
        for item in (self==__key):
            return True
        return False












class Folder(object):
    """Folder-based property"""
    
    def __init__(self, name_or_id, create=False):
        if isinstance(name_or_id, basestring):
            fids = Ecco.GetFoldersByName(name_or_id)
            self.name = name_or_id
            if not fids:
                if create:
                    self.id = Ecco.CreateFolder(name_or_id, self.ftype)
                else:
                    raise KeyError(name_or_id)                    
            else:
                self.id, = fids
        else:
            self.id = name_or_id
            self.name = Ecco.GetFolderName(self.id)

        if Ecco.GetFolderType(self.id) != self.ftype:
            raise TypeError("%s is not a %s" %
                (name_or_id, self.__class__.__name__)
            )
        
    def __set__(self, ob, value):
        Ecco.SetFolderValues(ob.id, self.id, self.encode(value))

    def __get__(self, ob, typ=None):
        if ob is None:
            return Container(typ, self)
        return self.decode(Ecco.GetFolderValues(ob.id, self.id))

    def __delete__(self, ob):
        Ecco.SetFolderValues(ob.id, self.id, '')

    decorate(staticmethod)
    def encode(value):
        if value is None: return ''
        return value



    decorate(staticmethod)
    def decode(value):
        return value

    def __getitem__(self, key):
        """cls->Container or item->value"""
        if isinstance(key, ItemClass):
            return Container(item, self)
        if isinstance(key, Item):
            return self.__get__(key)
        raise TypeError, key    # XXX

    def __contains__(self, item):
        """Is item in this folder?"""
        if isinstance(item, Item):
            item = item.id
        return self.id in Ecco.GetItemFolders(item)

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.name)


class TextFolder(Folder):
    ftype = FolderType.Text

class PopupFolder(Folder):
    ftype = FolderType.PopUpList

class CheckmarkFolder(Folder):
    ftype = FolderType.CheckMark

    decorate(staticmethod)
    def encode(value):
        if value is None: return ''
        return int(bool(value))

    decorate(staticmethod)
    def decode(value):
        return bool(value)
    

class DateFolder(Folder):
    ftype = FolderType.Date

    decorate(staticmethod)
    def encode(value):
        if value is None: return ''
        if isinstance(value, datetime.datetime):
            return format_datetime(value)
        elif isinstance(value, datetime.date):
            return format_date(value)
        return value

    decorate(staticmethod)
    def decode(value):
        if value=='':
            return None
        y,m,d = map(int, (value[:4], value[4:6], value[6:8]))
        if len(value)==8:
            return datetime.date(y,m,d)
        value = value[8:]
        return datetime.datetime(y,m,d, int(value[:2]), int(value[2:4]))


class NumericFolder(Folder):
    ftype = FolderType.Number
    
    def encode(self, value):
        if value is None: return ''
        return str(Decimal(value))

    def decode(self, value):
        if value=='':
            return None
        if '.' in value:
            return Decimal(value)
        return int(value)
        




def additional_tests():
    import doctest
    return doctest.DocFileSuite(
        'README.txt',
        optionflags=doctest.ELLIPSIS|doctest.NORMALIZE_WHITESPACE,
    )



































