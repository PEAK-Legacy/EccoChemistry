from ecco_dde import *
from peak.util.decorators import decorate, classy
import datetime, operator
from decimal import Decimal

Ecco = EccoDDE()

__all__ = [
    'Ecco', 'Item', 'CheckmarkFolder', 'TextFolder', 'PopupFolder',
    'DateFolder', 'NumericFolder', 'Folder',
]






























class _ItemChildren(object):
    """Container for an item's children"""

    def __init__(self, itemtype, parentid, depth=1):
        self.itemtype = itemtype
        self.parentid = parentid
        self.depth = depth

    def __iter__(self):
        for depth, id in Ecco.GetItemSubs(self.parentid, self.depth):
            cls = _find_item_subclass(self.itemtype, id)
            if cls is not None: yield cls(id, __class__=cls)        

    def __nonzero__(self):
        for sub in self: return True
        return False

    def __len__(self):
        return len(list(iter(self)))    # iter prevents recursion

    def __contains__(self, item):
        if isinstance(item, self.itemtype):
            parents = Ecco.GetItemParents(int(item))
            return self.parentid in parents[:-self.depth or len(parents)]
        return False

    def extend(self, items):
        items = map(int, items)[::-1]
        subs = Ecco.GetItemSubs(self.parentid, 1)
        if subs:
            Ecco.InsertItem(subs[-1][1], items, InsertLevel.Same)
        else:
            Ecco.InsertItem(self.parentid, items)

    def append(self, item):
        self.extend([item])

    def prepend(self, item):
        Ecco.InsertItem(self.parentid, int(item))


class Children(object):
    """Property for parent item of a given type"""

    def __init__(self, itemtype=None, depth=1):
        assert itemtype is None or isinstance(itemtype, ItemClass)
        self.itemtype = itemtype
        self.depth = depth

    def __get__(self, ob, typ):
        if ob is None:
            return self
        return _ItemChildren(self.itemtype or typ, int(ob), self.depth)
        
    def __set__(self, ob, value):
        value = list(value)[::-1]
        # unlink children
        Ecco.InsertItem(0, [
            int(i) for i in _ItemChildren(self.itemtype, int(ob), 1) if i!=ob
        ])
        if value:
            it = self.itemtype or type(ob)
            Ecco.InsertItem(int(ob), [int(it(i)) for i in value if i!=ob])

    def __delete__(self, ob):
        self.__set__(ob, ())
















class Parent(object):
    """Property for parent item of a given type"""

    def __init__(self, itemtype=None):
        assert itemtype is None or isinstance(itemtype, ItemClass)
        self.itemtype = itemtype

    def __get__(self, ob, typ):
        if ob is None:
            return self
        parents = Ecco.GetItemParents(int(ob))
        if parents:
            cls = _find_item_subclass(self.itemtype or typ, parents[-1])
            if cls:
                return cls(parents[-1], __class__ = cls)
        return None

    def __set__(self, ob, value):
        if value is None:
            parent = 0
        else:
            assert self.itemtype is None or isinstance(value, self.itemtype)
            parent = int(value)
        Ecco.InsertItem(parent, int(ob))

    def __delete__(self, ob):
        self.__set__(ob, None)














class ItemClass(type(classy)):
    """General item class"""

    __container__ = None
    
    def _query(self, *criteria):
        return self.__container__._query(*criteria)

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


_folder_bits = {}
_folder_bit = 1

def _folder_mask(fid):
    try:
        return _folder_bits[fid]
    except KeyError:
        global _folder_bit
        result = _folder_bits[fid] = _folder_bit
        _folder_bit <<= 1
        return result



class Item(classy, int):
    """Base class for Ecco items"""
    __metaclass__ = ItemClass
    __slots__ = ()  # XXX should keep in subclasses
    def __new__(cls, id_or_text, **kw):
        vals = attrs = ()
        if isinstance(id_or_text, basestring):
            d = cls.default_values.copy()
            d.update(kw)
            if d: vals, attrs, extra = cls._attrvalues(d)
            cls = _find_item_subclass(cls, None, vals, True)
            id_or_text = Ecco.CreateItem(id_or_text,vals)
        else:
            if kw: vals, attrs, extra = cls._attrvalues(kw)
            if '__class__' in kw:
                cls = kw.pop('__class__')   # fast path for collections
            else:
                cls = _find_item_subclass(cls, id_or_text, vals, True)
            if vals: Ecco.SetFolderValues(id_or_text, *zip(*vals))
        self = super(Item, cls).__new__(cls, id_or_text)
        if attrs:
            for k, v in attrs: setattr(self, k, v)
        return self

    required_values = dict()
    default_values = dict()
    id = property(int)

    def _check_fields():
        return True

    def text(self):
        return Ecco.GetItemText(int(self))
    def _set_text(self, value):
        Ecco.SetItemText(int(self), value)

    text = property(text, _set_text)

    def __repr__(self):
        return "%s(%d)" % (self.__class__.__name__, int(self))

    def __class_init__(cls, name, bases, cdict, supr):
        supr()(cls, name, bases, cdict, supr)
        defaults = cls.required_values.copy()
        required = {}
        for base in bases[::-1]:
            if isinstance(base, ItemClass):
                defaults.update(base.default_values)
                required.update(base.required_values)

        defaults.update(cls.default_values)
        cls.default_values = defaults
        required.update(cls.required_values)
        if cls.__container__:
            required.setdefault('__container__', None)
            if isinstance(cls.__container__.folder, CheckmarkFolder):
                defaults.setdefault('__container__',True)

        vals, attrs, extra = cls._attrvalues(required)
        assert not attrs    # XXX error message
        cls._exclusion_mask = 0
        required = cls._required_values = dict(vals)
        for f, v in extra:
            if v is False:
                cls._exclusion_mask |= _folder_mask(f)
                del required[f]
            elif v is None:
                required[f] = None
            elif v is True and cls.__container__ is None:
                cls.__container__ = Folder(f)

        cls._folder_mask = reduce(operator.or_, map(_folder_mask, required), 0)
        checker = cls._check_fields.im_func  # XXX error handling
        decoders = []
        code = checker.func_code
        names = code.co_varnames[:code.co_argcount]
        assert not checker.func_defaults    # XXX error message
        for attr, default in zip(names, defaults):
            folder = getattr(cls, attr).folder  # XXX error handling
            _folder_mask(folder.id) # ensure the value will be retrieved
            decoders.append((folder.id, folder.decode))

        def _validate_fields(values):
            return True

        if decoders:
            def _validate_fields(values, decoders=decoders):
                vget = values.get
                return checker(*[d(vget(f)) for f,d in decoders])

        cls._validate_fields = staticmethod(_validate_fields)

    decorate(classmethod)
    def _attrvalues(cls, d):
        vals, attrs, original = [], [], []
        for k, v in d.items():
            if not hasattr(cls, k):
                raise TypeError("No such attribute: ", k)
            descr = getattr(cls, k)
            if isinstance(descr, Container):
                fid = descr.folder.id
                vals.append((fid, descr.encode(v)))
                original.append((fid, v))
            else:
                attrs.append((k, v))
        return vals, attrs, original

    def update(self, **kw):
        """Set multiple attributes at once"""
        vals, attrs, extra = self._attrvalues(kw)
        if vals: Ecco.SetFolderValues(int(self), *zip(*vals))
        for k, v in attrs: setattr(self, k, v)











    decorate(classmethod)
    def upgrade(cls, itemid, **kw):
        """Upgrade `itemid` to this class by initializing required values"""
        fids = dict.fromkeys(Ecco.GetItemFolders(itemid))
        d = cls.default_values.copy()
        for k, v in d.items():
            if v is not None:
                descr = getattr(cls, k)
                if isinstance(descr, Container) and descr.folder.id in fids:
                    del d[k]
        d.update(kw)
        return cls(itemid, **d)

    parent = Parent()
    children = Children()
    all_children = Children(depth=0)

























class Container(object):
    """Find items in a given folder/itemtype"""
    def __init__(self, itemtype, folder):
        self.folder = folder
        self.itemtype = itemtype
        self.encode = self.folder.encode

    def _query(self, *criteria):
        for id in Ecco.GetFolderItems(self.folder.id, *criteria):
            cls = _find_item_subclass(self.itemtype, id)
            if cls is not None: yield cls(id, __class__=cls)

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
        return default

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
    """Folder-based property/item container"""

    ftype = None

    def __init__(self, name_or_id, create=False):
        if create and self.ftype is None:
            raise TypeError("You can only create Folder subclasses")
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

        ftype = Ecco.GetFolderType(self.id)
        if self.ftype is None:
            self.__class__ = folder_classes[ftype]
        elif ftype != self.ftype:
            raise TypeError("%s is not a %s" %
                (name_or_id, self.__class__.__name__)
            )

    def __set__(self, ob, value):
        Ecco.SetFolderValues(int(ob), self.id, self.encode(value))

    def __get__(self, ob, typ=None):
        if ob is None:
            return Container(typ, self)
        return self.decode(Ecco.GetFolderValues(int(ob), self.id))

    def __delete__(self, ob):
        Ecco.SetFolderValues(int(ob), self.id, '')

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
            return Container(key, self)
        if isinstance(key, int):
            return self.decode(Ecco.GetFolderValues(int(key), self.id))
        raise TypeError, key

    def __setitem__(self, key, value):
        if isinstance(key, int):
            return Ecco.SetFolderValues(int(key), self.id, self.encode(value))
        raise TypeError, key

    def __contains__(self, item):
        """Is item in this folder?"""
        return self.id in Ecco.GetItemFolders(int(item))

    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, self.name)

    children = property(lambda self: map(Folder, all_folders()[self.id][1]))
    parent   = property(lambda self: Folder(all_folders()[self.id][0]))

    def __iter__(self):
        return iter(Container(Item, self))







class TextFolder(Folder):
    ftype = FolderType.Text

class PopupFolder(Folder):
    ftype = FolderType.PopUpList

class CheckmarkFolder(Folder):
    ftype = FolderType.CheckMark

    decorate(staticmethod)
    def encode(value):
        if value: return '1'
        return ''

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
        if not value:
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
        if not value:
            return None
        if '.' in value:
            return Decimal(value)
        return int(value)


folder_classes = [
    TextFolder, PopupFolder, CheckmarkFolder, DateFolder, NumericFolder
]

folder_classes = dict([(f.ftype, f) for f in folder_classes])
folder_decoders = dict([(t, f.decode) for t,f in folder_classes.items()])

def all_folders():
    """Return a mapping of folder ids to (parentid,[childids]) pairs"""
    info, stack = {}, []
    parent, children = None, []
    for fid, depth in Ecco.GetFolderOutline():
        while depth<len(stack):
            parent, children = stack.pop()
            #ignore, children = info[parent]
        children.append(fid)
        stack.append((parent,children))
        children = []
        info[fid] = parent, children
        parent = fid
    return info





def _find_item_subclass(cls, itemid=None, data=(), required=False):
    get = _folder_bits.get
    mask, values = 0, []
    if itemid is not None:
        fids = Ecco.GetItemFolders(itemid)
        for fid in fids:
            bit = get(fid, 0)
            if bit:
                values.append(fid)
                mask |= bit
        values = dict(zip(values, Ecco.GetFolderValues(itemid, values)))
    else:
        values = {}
    if data:
        values.update(data)
        mask |= reduce(operator.or_, [get(fid,0) for fid,val in data], 0)

    matches = []
    match = None
    candidates = [cls]
    while True:
        for subclass in candidates:
            m = subclass._folder_mask
            if (mask & m)!=m or (mask & subclass._exclusion_mask):
                continue
            for k, v in subclass._required_values.iteritems():
                if v!=values[k] and v is not None:
                    break
            else:
                if subclass._validate_fields(values):
                    matches.append(subclass)
        if matches:
            if len(matches)>1:
                raise TypeError("Validation ambiguity:",itemid or None,matches)
            match = matches.pop()
            candidates = [c for c in match.__subclasses__() if '_validate_fields' in c.__dict__]
        elif match is None and required:
            raise TypeError # XXX error message
        else:
            return match

def additional_tests():
    import doctest
    return doctest.DocFileSuite(
        'README.txt',
        optionflags=doctest.ELLIPSIS|doctest.NORMALIZE_WHITESPACE,
    )



































