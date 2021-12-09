"""
none of this is thoroughly tested at the moment. created for some quick and
dirty data structure manipulations

the datastructure checking stuff doesn't always work as intended. It works for
the trivial cases it outlines but I've seen it fail in some, and haven't fixed
that
"""

import random
import string
import logging

try:
    import faker
except ImportError as e:
    logging.warning("no `faker`. generate_random_datastruct will not work")
    faker = None

try:
    basestring
except NameError:
    # python 3
    basestring = str

_DEBUG_LEVEL = 0


def check_dataset_consistency(D, level = 0):
    """
    currently 1 level deep only
    """
    if not isinstance(D, list):
        raise TypeError("non-list not supported")
    if not D:
        return None
    type0 = type(D[0])
    rtn = []
    dschema = None
    for dd in D:
        if type(dd) is not type0:
            return False
        if isinstance(dd, list):
            check_dataset_consistency(dd, level + 1)
        elif isinstance(dd, dict):
            if dschema is None:
                dschema = {}
                for k, v in dd.items():
                    dschema[k] = type(v)
                continue
            for k, vtype in dschema.items():
                if k not in dd or type(dd[k]) != vtype:
                    return False
    return dschema

try:
    import numpy as np
    import operator
    import decimal

    SmartTypeMap = {
            decimal.Decimal: lambda _: np.float,
            str: lambda ls: "|S%s" % max(map(len, ls)),
            }
    def smart_dataset_to_table(D):
        # infer base structure
        dschema = check_dataset_consistency(D)
        if not dschema:
            raise TypeError("could not discern a regular structure")
        dout = dict([(key, map(operator.itemgetter(key), D)) for key in dschema])
        dtype = [(str(key), SmartTypeMap.get(basetype, lambda _: basetype)(dout[key])) for key, basetype in dschema.items()]
        return np.array([tuple([dd[key] for key in dschema]) for dd in D], dtype = dtype)
except ImportError as e:
    def smart_dataset_to_table(D):
        return None
    logging.warning("error on import: %s\n%s will not function." % (e, smart_dataset_to_table.__name__))


if faker is None:
    def generate_random_string(min_length = 1, max_length = 50):
        strlen = random.randint(min_length, max_length)
        return ''.join(
            random.choice(string.printable)
            for _ in range(strlen))
else:
    def generate_random_string(min_length = 1, max_length = 50):
        return faker.Faker().user_name()


def identity(x):
    return x


def generate_random_datastruct(
        max_depth = 1,
        allow_type = None,
        # dict only
        key_transformer = identity,
        value_transformer = identity,
    ):

    if allow_type is None:
        allow_type = [int, float, str, list, dict]

    idx = random.randint(1, len(allow_type)) - 1
    mytype = allow_type[idx]

    MIN_OBJ_LEN, MAX_OBJ_LEN = (1, 4)
    obj_len = MIN_OBJ_LEN + random.randint(0, MAX_OBJ_LEN-MIN_OBJ_LEN)

    if mytype == int:
        return random.randint(0, 2e30)
    elif mytype == float:
        return random.random()
    elif mytype == str:
        return generate_random_string()
    elif mytype == list:
        # should parametrize this into arglist...
        rtn = []
        for i in range(obj_len):
            # shall we create another level?
            if max_depth > 1 and random.random() > 0.5:
                val_deep = generate_random_datastruct(max_depth - 1, allow_type,
                        key_transformer, value_transformer)
                if type(val_deep) in (list, dict):
                    val = val_deep
                else:
                    val = [val_deep]
            else:
                val = generate_random_datastruct(max_depth = 1, allow_type = [int, float, str])
            rtn.append(val)
        return rtn
    elif mytype == dict:
        rtn = {}
        for i in range(obj_len):
            # be boring for now
            k = generate_random_datastruct(max_depth = 1, allow_type = [str,int])
            # shall we create another level?
            if max_depth > 1 and random.random() > 0.5:
                val_deep = generate_random_datastruct(max_depth - 1, allow_type,
                        key_transformer, value_transformer)
                if type(val_deep) == dict:
                    val = val_deep
                else:
                    k_deep = generate_random_datastruct(max_depth = 1, allow_type = [str,int])
                    val = {k_deep: val_deep}
            else:
                val = generate_random_datastruct(max_depth = 1, allow_type = [int, float, str])
            xk = key_transformer(k)
            rtn[xk] = value_transformer(val)
        return rtn
    

def recursive_fuzzer(refds, type_change = None, level = 0):
    """
    recursively corrupt the data in refds by replacing it with
    - data of the same type
    - data of a different type, same nesting level
    - randomly generate

    Arguments:
    - `refds`: reference data structure to fuzz. will not be altered (SHALLOW COPY!)
    - `type_change`: rules for changing data structure data type
    - `level`: ignored

    Returns:
    A data structure with the same superficial layout, including
    nested data structures, but altered elements

    example:
      type_change = None
      [1, 2, "x"] => [234, 79, "water"] # random value of same type

      type_change = str
      [1, 2, 3] => ["snowman", "balloon", "candy"]
      [1, 2, "x"] => ["snowman", "balloon", "candy"]

      type_change = "different"
      [1, 2, "x"] => ["snowman", 7.985253, 3] # scalars to scalars

   TODO:
      type_change = {int: str}
      [1, 2, "x"] => ["snowman", "balloon", "x"] # affects only specified type

    """
    
    if refds is None:
        # raise TypeError("why are you fuzzing a None?")
        return None

    type_refds = type(refds)
    if type_refds == list:
        return [recursive_fuzzer(subds, type_change) for subds in refds]
    elif type_refds == dict:
        rtn = refds.copy()
        for key in rtn:
            rtn[key] = recursive_fuzzer(rtn[key], type_change)
        return rtn
    else:
        if type_change is None:
            return generate_random_datastruct(allow_type = [type_refds])
        elif type(type_change) == list:
            return generate_random_datastruct(allow_type = type_change)
        elif type_change == "different":
            if type_refds == int:
                return generate_random_datastruct(allow_type = [float, str])
            elif type_refds == float:
                return generate_random_datastruct(allow_type = [int, str])
            elif type_refds == str:
                return generate_random_datastruct(allow_type = [int, float])
            else:
                raise TypeError("unprocessed type: %s" % type_refds)
        else:
            return generate_random_datastruct(allow_type = [type_change])


def recursive_type_compare(d1, d2):
    """
    returns True if d1 and d2 have the same type:
      if d1 and d2 are list or dict,
      check all subelements have the same type
      True if yes, False if not
    Arguments:
    - `d1`, `d2`: 2 objects
    """
    if type(d1) == list:
        if len(d1) != len(d2):
            raise ValueError("unequal length")
        return all([recursive_type_compare(v1, v2) for v1, v2 in zip(d1, d2)])
    elif type(d1) == dict:
        if len(d1) != len(d2):
            raise ValueError("unequal length")
        return all([recursive_type_compare(d1[k1], d2[k1]) for k1 in d1])
    else:
        return type(d1) == type(d2)


def to_tuple(lst):   # c/p https://stackoverflow.com/a/27050037
    return tuple(to_tuple(i) \
            if isinstance(i, list) else i for i in lst)

def to_list(lst):
    return list(to_list(i) \
            if isinstance(i, tuple) else i for i in lst)

def walk_dict_keys(D_orig):
    if not isinstance(D_orig, dict):
        return None
    all_paths = []

    def recur(D, prefix=None):
        if isinstance(D, list):
            #all_paths.append(prefix + [[]])
            for item in D:
                recur(item, prefix + [[]])
        elif isinstance(D, dict):
            for k in D.keys():
                if prefix is None:
                    next_path = []
                else:
                    next_path = prefix[:]
                recur(D[k], next_path + [k])
        else:
            all_paths.append(prefix)

    recur(D_orig)

    filtered_paths = []
    visited = set()
    for path in all_paths:
        tuple_fied = to_tuple(path)
        if tuple_fied in visited:
            continue
        visited.add(tuple_fied)
        filtered_paths.append(path)
    return filtered_paths


def dict_depth(dc, DEPTH = 1):
    """
    how we define depth:
    - scalar = None
        in a max() operation, treated as 0
    - string, list, tuple = 1
        if nested, the maximum nest depth
    - dict: as deep as the key depth, i.e.
        {1: 2} = 1
        {1: {2: 3}} = 2

    def test_dict_depth():
        for test, expect in [
            (  None, None    ),
            (  1, None       ),
            (  [], 0         ),
            (  [1,2], 1      ),
            (  "", 0         ),
            (  "a", 1        ),
            (  [1,2], 1      ),
            (  (1,), 1       ),
            (  (1,[1,2]), 2  ),
            (  {}, 0         ),
            ]:
            assert dict_depth(test) == expect
        a = {"a": "b"}
        assert dict_depth(a) == 1
        a["c"] = {"d": "e"}
        assert dict_depth(a) == 2
        a["c"]["d"] = []
        assert dict_depth(a) == 2
        a["c"]["d"] = [1,]
        assert dict_depth(a) == 3

    """
    try:
        if len(dc) == 0:
            return 0
    except TypeError:
        return None
    if isinstance(dc, basestring):
        return 1
    elif isinstance(dc, dict):
        get = dc.get
    else:
        get = lambda x: x
    rtn_depth = DEPTH
    for k in dc:
        next = get(k)
        # print("+++" + (" %s>" % DEPTH) * DEPTH, k)
        if hasattr(next, "__iter__"):
            rtn_depth = max(rtn_depth, dict_depth(next, DEPTH + 1) or 0)
    return rtn_depth


def dict_breadth(mixed):
    """
    for test, expect in [
        (  [], 0                                ),
        (  (), 0                                ),
        (  {}, 0                                ),
        (  [1,2,3], 3                           ),
        (  [1,[2,2,3,4],3], 4                   ),
        (  {1:2, 3:4, 5:6}, 3                   ),
        (  {1:2, 3:[1,2,3,4,5]}, 5              ),
        (  {1:2, 3:[1,[1,2,3,4]]}, 4            ),
        (  {1:2, 3: {"a": [1,2,(2,3,4,5)]}}, 4  ),
        ]:
        assert dict_breadth(test) == expect
    """
    
    lslevel = []
    breadth = 0
    lsv = isinstance(mixed, dict) and mixed.values() or mixed
    for v in lsv:
        breadth += 1
        if isinstance(v, (tuple, list, dict)):
            lslevel.append(dict_breadth(v))
    return max(breadth, sum(lslevel))


def extract_obj_at_depth_offset(dc, offset = 0):
    """
    for test, expect in [
        (([[2,3,[4,5]]], 0), [[[2, 3, [4, 5]]]]),
        (([[2,3,[4,5]]], 1), [[2, 3, [4, 5]]]),
        (([[2,3,[4,5]]], 2), [[4, 5]]),
        (([[2,3,[4,5]]], 3), []),
        (([[2,3,[4,5]]], 0), [[[2, 3, [4, 5]]]]),
        (([[2,3,[4,5]]], 1), [[2, 3, [4, 5]]]),
        (([[2,3,[4,5]]], 2), [[4, 5]]),
        ]:
        print("TESTING:", test)
        assert extract_obj_at_depth_offset(*test) == expect
    """

    rtn = []
    if offset == 0:
        return [dc]
    else:
        lsnext = []
        if isinstance(dc, dict):
            lsnext = dc.values()
        elif isinstance(dc, (tuple, list)):
            lsnext = dc
        for subdc in lsnext:
            rtn.extend([extracted for extracted in extract_obj_at_depth_offset(subdc, offset-1) if hasattr(extracted, "__iter__")])
    return rtn


def sliding_subset_check(sub, SUP, empty_set = None, tolerate_key_val = None):
    """
    for test, expect in [
        (  ({1: None, 4: None}, {2: [[{1: None, 4: None, 5:[]}], [], 1], 3:None}), True  )
        ]:
        assert sliding_subset_check(*test) == expect
    """

    # if k sub, k SUP don't match up in beginning iteration
    # and SUP has larger depth than sub,
    # allow sliding window search for depth
    depth_sub = dict_depth(sub)
    depth_SUP = dict_depth(SUP)
    if depth_sub and depth_SUP:
        for depth_offset in range(depth_SUP - depth_sub, -1, -1):
            # extract into individual dict at given offset level
            if _DEBUG_LEVEL > 0:
                logging.debug("CHECKING DEPTH", depth_offset, len(extract_obj_at_depth_offset(SUP, depth_offset)))
            for extracted_SUP in extract_obj_at_depth_offset(SUP, depth_offset):
                if depth_offset > 1:
                    if _DEBUG_LEVEL > 0:
                        logging.debug(extracted_SUP)
                subcheck = is_obj_subset(sub, extracted_SUP, empty_set, tolerate_key_val)
                if subcheck:
                    if _DEBUG_LEVEL > 0:
                        logging.debug("FOUND SUBSET:")
                        # print(sub)
                        logging.debug("-------------------- AT LAYER %s --------------------" % (depth_offset))
                        # print(extracted_SUP)
                    return subcheck
        return False
    else:
        if depth_sub is None and depth_SUP is not None:
            if sub in SUP:
                return True
        logging.debug(f'scalar comparison: {sub} / {SUP}')

def is_obj_subset(sub, SUP, empty_set = None, tolerate_key_val = None, depth = 0):
    """
    `empty_set`: what counts as an empty set
                 if None, nothing is an empty set, so
                    comparing [] <=> None --> False
                 if [None,], None is an empty set, so
                    an int, e.g. 2, is a superset
                 if [0, False, None]
                    then pretty much it will return True

    is sub:Dict a subset of sup:Dict

    for test, expect in [
        # scalar
        (  (1,1), True    ), # same
        (  (2,1), False   ), # diff
        # list/tuple
        (  ((1,1),(1,1)), True    ), # same list
        (  ((1,1),(1,1,1)), True    ), # easy subset list
        (  ((1,1),(1,1,2)), True    ), # strict subset list
        (  ((1,1),(2,1,1)), True    ), # subset at end
        (  ((1,2),(1,2,1)), True    ), # different value
        (  ((1,2),(1,1,2)), True    ), # subset at end, different value
        (  ((1,2),(1,3,3,3,1,2)), True    ), # subset at long end
        # dict
        (  ({1:2},{1:2}), True    ), # same
        (  ({1:2},{2:1}), False    ), # diff
        (  ({1:2},{1:2, 2:3}), True    ), # proper subset
        (  ({1:2, 3: [1,2]},{1:2, 2:3, 3: [1,2]}), True    ), # proper subset with list value
        (  ({1:2, 3: [1,2,3]},{1:2, 2:3, 3: [1,1,2,3]}), True    ), # proper subset with list value
        (  ({1:2, 3: [1,2,3], 4: {2:5}},{1:2, 2:3, 3: [1,1,2,3], 4:{2:5, 6:7}, 8:9}), True    ), # proper subset with list value

        (  ({"a": 1, "b": 2},{"a": 1, "b": 2}), True    ), # proper subset with list value
        (  ({"a": 1, "b": 3},{"a": 1, "b": 2}), False    ), # proper subset with list value

        (  ({"a": 1, "b": None},{"a": 1, "b": 2}), False    ), # proper subset with list value
        (  ({"a": 1, "b": 2},{"a": 1, "b": None}), False    ), # proper subset with list value
        (  ({"a": 1, "b": None},{"a": 1, "b": 2}, [None]), True    ), # proper subset with list value
        (  ({"a": 1, "b": 2},{"a": 1, "b": None}, [None]), False    ), # proper subset with list value

        (  ({"a": 1, "b": []},{"a": 1, "b": 2}, [[],]), True    ), # proper subset with list value
        (  ({"a": 1, "b": 2},{"a": 1, "b": []}, [[],]), False    ), # proper subset with list value

        (  ({"a": 1, "b": {}},{"a": 1, "b": 2}, [{},]), True    ), # proper subset with list value
        (  ({"a": 1, "b": 2},{"a": 1, "b": {}}, [{},]), False    ), # proper subset with list value
        ]:
        print("TESTING:", test)
        assert is_obj_subset(*test) == expect


    """

    if _DEBUG_LEVEL > 0:
        logging.debug(">> " + ("%s> " % depth) * depth, sub, " -- ", SUP)
    if not hasattr(sub, "__iter__") or \
            (not sub and hasattr(sub, "__iter__")):
        if SUP and empty_set and (sub in empty_set):
            return True
        elif hasattr(SUP, "__iter__"):
            return sub in SUP or sub == SUP
        return sub == SUP
    if not isinstance(sub, dict):
        # 2 cases here if length doesn't match up:
        # A,B vs A,B,x --> true
        # A,B vs x,A,B --> false on first zip
        # A,B vs x,x,A,B --> false on first zip
        # so need to realign and test again
        # use a sliding window:
        if isinstance(SUP, list):
            try:
                nslide = 1 + len(SUP) - len(sub)
            except TypeError as e:
                nslide = 0
            while nslide > 0:
                # XXX this looks risky
                # because it seems to assume there is a matching order of the sliding list window?
                nslide -= 1
                lstest = [is_obj_subset(v_sub, v_SUP, empty_set, tolerate_key_val, depth + 1) for v_sub, v_SUP in zip(sub, SUP[nslide:])]
                if all(lstest):
                    return True
        return False
    else:
        if isinstance(SUP, dict):
            lstest = []
            for k, v_sub in sub.items():
                if k not in SUP:
                    if _DEBUG_LEVEL > 0:
                        print("SUP not have:", k)
                    if tolerate_key_val is not None and k in tolerate_key_val and (v_sub == tolerate_key_val[k]):
                        if _DEBUG_LEVEL > 0:
                            print("tolerated ex ante!")
                    else:
                        #lstest.append(False)
                        return False
                else:
                    lstest.append(is_obj_subset(v_sub, SUP[k], empty_set, tolerate_key_val, depth + 1))
            return all(lstest)
        return False

def get_add_op(d0, d1, searchpath = ""):
    """
    assuming d0:dict --> d1:dict via some strictly additive operation,
    i.e., is_obj_subset(d0, d1) == True,
    find out the exact add operation F(dict) s.t. F(d0) == d1
    returns: a tuple:
      (searchpath, operation, substructure) where
      `searchpath`:string = a d0 lookup path that can be eval-ed, e.g.
        '["sequence"]'
      `operation`:string = name of a function that should be eval-ed:
        'append', or 'assign' (which you should interpret as '=')
      `substructure`:dict = python native structure, the data to
        be applied to d0

    for test, expect in [
        (  ({1:2},{1:2}), (None, None, None)    ), # same
        (  ({1:2},{1:2, 2:1}), ("[2]", "assign", 1)    ), # diff
        (  ({1:2},{1:2, 2:[1,2,3]}), ("[2]", "assign", [1,2,3])    ), # proper subset
        (  ({1:2, 3: [1,2]},
            {1:2, 2:3, 3: [1,2]}),
            ("[2]", "assign", 3) ), # proper subset with list value
        (  ({1:2, 3: [1,2,3]},{1:2, 3: [1,2,3,4]}),
           ("[3]", "append", 4) ), # proper subset with list value
        ]:
        print("TESTING:", test)
        actual = get_add_op(*test)
        try:
            assert actual == expect
        except Exception as e:
            print("FAIL on:", test)
            print("-" * 20)
            print("expected:", expect)
            print("got", actual)
            break        
    """
    # skip for speedup
    # if not is_obj_subset(d0, d1):
    #     raise Exception("first dict is not a proper subset of second dict!")
    
    operation = None
    substructure = None
    for k1, v1 in d1.items():
        searchpath_current = "[%s]" % k1.__repr__()
        if k1 not in d0:
            searchpath += searchpath_current
            operation = "assign"
            substructure = v1
        else:
            if not isinstance(v1, dict):
                # list/tuple
                if hasattr(v1, "__iter__"):
                    if len(v1) == len(d0[k1]) + 1 and v1[:-1] == d0[k1]:
                        searchpath += searchpath_current
                        operation = "append"
                        substructure = v1[-1]
                    elif v1 != d0[k1]:
                        searchpath += searchpath_current
                        operation = "assign"
                        substructure = v1
            else:
                print("IFFY IFFY! " * 20)
                return get_add_op(d0[k1], v1, searchpath_current)
    return (len(searchpath) and searchpath or None, operation, substructure)



# http://stackoverflow.com/questions/1165352/fast-comparison-between-two-python-dictionary
class DictDiffer(object):
    """
    Calculate the difference between two dictionaries as:
    (1) items added
    (2) items removed
    (3) keys same in both but changed values
    (4) keys same in both and unchanged values
    """
    def __init__(self, base, comp):
        self.comp, self.base = comp, base
        self.set_current, self.set_past = set(comp.keys()), set(base.keys())
        self.intersect = self.set_current.intersection(self.set_past)
    def added(self):
        return self.set_current - self.intersect
    def removed(self):
        return self.set_past - self.intersect
    def changed(self):
        return set(o for o in self.intersect if self.base[o] != self.comp[o])
    def unchanged(self):
        return set(o for o in self.intersect if self.base[o] == self.comp[o])
    def __str__(self):
        return "\n".join([":: %s ::\n%s" % (fn, getattr(self, fn)()) for fn in ("added","removed","changed","unchanged") if getattr(self, fn)()])


class DictGenerator:
    '''
    generate random nested data to test the collapser
    '''

    def _random_generator(self):
        if faker:
            return faker.Faker().user_name
        else:
            return lambda: ''.join([random.choice(string.ascii_letters) for i in range(6)])

    def __init__(self):
        self.nresponse = 0
        self.D = None
        self.makesomething = self._random_generator()

    def generate_child(self):
        return dict(
                response = self.makesomething(),
                rt = random.randint(10,99),
                )

    def generate_parent(self, depth):
        return {
                'setting': self.makesomething()[:6],
                'history': [],
                }

    def generate_nested(self, min_depth = 2, max_depth = 5):
        if self.D:
            return self.D

        self.nresponse = 0
        mydepth = random.randint(min_depth, max_depth)

        def recur(remaining = 0):

            if remaining == 0:
                self.nresponse += 1
                myd = self.generate_child()
            else:
                myd = self.generate_parent(mydepth-remaining)
                for iresponse in range(random.randint(2,7)):
                    myd['history'].append(recur(remaining - 1))
            return myd

        self.D = recur(mydepth)
        return self.D
