=================================
Accessing Ecco With EccoChemistry
=================================

The EccoChemistry module lets you interface with the Ecco Pro PIM using an
SQLAlchemy-like object mapping.  It's primarily intended for batch interaction
scripts, such as synchronization, importers, exporters, etc.  An example::

    >>> from ecco_chemistry import Ecco
    >>> session = Ecco.NewFile()  # the Ecco global is a EccoDDE API object

    >>> import ecco_chemistry as ec, datetime as dt, decimal as d

    >>> class Task(ec.Item):
    ...     due      = ec.DateFolder('Due Dates')
    ...     effort   = ec.NumericFolder('Effort Hours', create=True)
    ...     priority = ec.PopupFolder('Priority', create=True)
    ...     serial   = ec.TextFolder('Task Serial #', create=True)

    >>> t1 = Task("Overhaul the whatzit", serial="42A",
    ...           due=dt.date(2008,11,1), effort=8, priority="High"
    ... )

    >>> t2 = Task("Upload this module to PyPI", effort=d.Decimal("0.5"),
    ...           due=dt.datetime(2008,11,7, 20,30,40), priority="Medium",
    ...           serial="B59"
    ... )

    >>> t3 = Task("Contemplate navel",
    ...           due=dt.date(2010,12,31), effort=d.Decimal("0.25"),
    ...           priority="Low", serial="K27",
    ... )

    >>> for t in (Task.due<dt.date(2009,1,1,)):  # query by folder
    ...     print "%s: %s" % (t.text, t.due)
    Overhaul the whatzit: 2008-11-01
    Upload this module to PyPI: 2008-11-07 20:30:00

    >>> for t in +Task.effort:  # ascending sort by folder
    ...     print "%s: %s hrs" % (t.text, t.effort)
    Contemplate navel: 0.25 hrs
    Upload this module to PyPI: 0.5 hrs
    Overhaul the whatzit: 8 hrs

    >>> Task.serial['B59'].text     # dictionary interface
    'Upload this module to PyPI'

    >>> 'B59' in Task.serial
    True

    >>> print Task.serial.get('Q22')    # no such Task
    None

    >>> t4 = Task.serial.setdefault('Q22', "Another task", priority="Low")
    >>> t4.serial
    'Q22'  

Please note a few important limitations:

* Mapping classes MUST NOT be defined until *after* the appropriate file is
  loaded in Ecco; i.e., your script must set up the Ecco connection **before**
  defining its classes!  (You may wish to put your classes in a separate
  module, and delay its import until you .)

* Parent/child traversal isn't supported (yet)

* Polymorphic types aren't supported (yet)

* Date/time ranges are not currently supported and may cause errors

* You can't mix sorting and filtering, nor filter on more than one field
  (This may be improved in a future version.)
  
You can work around some of these limitations by appropriate use of the
``Ecco`` singleton, which is an ``ecco_dde.EccoDDE`` instance.  (See the
`EccoDDE developer's guide`_ for more information on its API.)  "Item" and
"Folder" objects have ``id`` attributes that can be passed to the ``EccoDDE``
API, and you can also create items and folders using ids retrieved from the
``EccoDDE`` API::

    >>> Task(t4.id).text
    'Another task'

    >>> ec.CheckmarkFolder(ec.CheckmarkFolder('PhoneBook').id).name
    'PhoneBook'

    >>> for tid in Ecco.GetFolderItems(ec.DateFolder('Due Dates').id):
    ...     print Task(tid).text
    Overhaul the whatzit
    Upload this module to PyPI
    Contemplate navel



Please consult the complete `EccoChemistry developer's guide`_ for more details.
Questions, comments, and bug reports for this package should be directed to the
`PEAK mailing list`_.

.. EccoDDE developer's guide: http://peak.telecommunity.com/DevCenter/EccoDDE
.. EccoChemistry developer's guide: http://peak.telecommunity.com/DevCenter/EccoChemistry#toc
.. _PEAK mailing list: http://www.eby-sarna.com/mailman/listinfo/peak/

.. _toc:
.. contents: **Table of Contents**


-----------------
Developer's Guide
-----------------

Undocumented/untested Features:

* other query ops (==, !=, <=, >, >=, .startswith, .with_text, .without, -)

* writing to Item.text, Item(**kw), Item().update()

* value conversions, deleting values

* folders vs. containers, dict interface on folders

* itemclass-level queries (i.e. query/sort ops on text, .container attribute)

* replacing/configuring the ``.Ecco`` global

* folder-item operations (e.g. ``aFolder[anItem]`` -> value)

* folder-type operations (e.g. ``for t in (aFolder[Task]=="X"):``)


Unimplemented Features:

* Polymorphic item/folder lookups (i.e., determine appropriate subtype when
  calling ``Folder(id)`` or ``SomeItemClass(id)``)

* Fast validity filtering (required fields + filter function over field names)

* Parent()/Children() attributes and sequence/hierarchy manipulation

* Field defaults for item creation

* Default repr() for items

* ``Folder.__setitem__`` (e.g. ``aFolder[anItem] = value``)

* Folder parent/child info


-------------------
Internals and Tests
-------------------

XXX::

    >>> Ecco.CloseFile(session)
    >>> Ecco.close()

