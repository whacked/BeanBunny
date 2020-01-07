'''
ISSUES: changing the decorator size will not change the
persistence size. you will need to modify or delete the shelf for
the new size to be reflected
'''
import pylru
import functools
import shelve
import atexit

DEFAULT_SHELVE_FILENAME = 'pylru_persistence.shelve'

_dshelve = {}

def dict_to_dlnode(d):
    dln = pylru._dlnode()
    dln.empty = d['empty']
    dln.value = d['value']
    dln.prev = dln.next = None
    return dln

def dlnode_to_dict(dln):
    return {
        'empty': dln.empty,
        'value': dln.value,
        'prev': getattr(dln.prev, 'key', None),
        'next': getattr(dln.next, 'key', None),
    }

def persisted_lrudecorator(size, shelve_path = DEFAULT_SHELVE_FILENAME):
    if shelve_path not in _dshelve:
        _dshelve[shelve_path] = (shelve.open(shelve_path), {})
    def lruwrap(func):
        @pylru.lrudecorator(size)
        @functools.wraps(func)
        def wrapped(*argv, **kw):
            return func(*argv, **kw)

        db, funcmap = _dshelve[shelve_path]
        funcmap[wrapped.__name__] = wrapped
        dprev = dnext = None
        dlnfirst = None
        # seed the pylru cache table from shelve if it exists
        if wrapped.__name__ in db:
            funcd = db[wrapped.__name__]

            for argt, dlnd in funcd.items():
                dln = dict_to_dlnode(dlnd)
                dln.key = argt
                wrapped.cache.table[argt] = dln
                wrapped.cache.head = dln
            mapping = wrapped.cache.table
            for argt, dlnd in funcd.items():
                dln = mapping[argt]
                dln.prev = dlnd['prev'] and mapping[dlnd['prev']] or wrapped.cache.head
                if dlnd['next'] is None:
                    dln.next = wrapped.cache.head
                else:
                    dln.next = mapping[dlnd['next']]
        if dprev:
            dlnfirst.prev = dprev
        return wrapped
    return lruwrap

@atexit.register
def persist_all():
    for shelve_path, (db, funcmap) in _dshelve.items():
        for func_name, func in funcmap.items():
            funcd = {}
            for argt, dlnode in func.cache.table.items():
                funcd[argt] = dlnode_to_dict(dlnode)
            db[func_name] = funcd
        db.close()

