from collections import Counter, namedtuple, defaultdict
from functools import wraps

import BeanBunny.data.DataStructUtil as dsu

try:
    import pandas as pd
except Exception:
    print('could not import pandas, export to dataframe will not work')
    pd = None

def cached(func):
    cache = {}
    @wraps(func)
    def with_cache(*argv):
        key = str(argv)
        if key in cache:
            return cache[key]
        cache[key] = func(*argv)
        return cache[key]
    return with_cache

@cached
def compile_header(d):
    '''
    note d should be a dict where keys are depth value and
    values are lists of str
    '''
    rtn = []
    for k in sorted(d.keys()):
        rtn.extend(map(lambda s: s.replace('\0', ''), d[k]))
    return rtn

@cached
def sorted_with_index(key_list):
    return sorted(enumerate(key_list), key=lambda x:x[1])

def empty_to_none(val):
    if not val and isinstance(val, (list,dict)):
        return None
    return val

def collapse(D_input, ORD_COLNAME = u'number'):
    '''
    first.3 version (and probably very slow)

    takes a nested dict of arbitrary depth construct a 2d table for it.
    children at the same depth are expected to have matching structure.

    at present, if a nested dict is given, as in "k3" in:
    {k1: v1,
     k2: v2,
     k3: {k3k1: k3v1, k3k2: k3v2},
     k4: [...]}
    the "k3" dict will get flattened such that a dict with structure
    {k1: v1,
     k2: v2,
     k3/k3k1: k3v1,
     k3/k3k2: k3v2,
     k4: [...]}
    gets operated on instead, and corresponding slash-concatenated keys are
    returned in the resultant table.

    In order for the current dict-squashing mechanism to work, list elements
    within the dict are pushed to be processed at the end of the dict element
    processing loop. See `key_list_with_type` below.

    ----
    this version only compiles the header list once for a given depth.
    this means that if you pass a structure with non-consistent headers
    in nested dicts, the later dicts will not have their keys saved
    '''
    # reduces chance of collision although current code doesn't use
    # keycheck or set() so this doesn't actually do anything now
    ORD_COLNAME = ORD_COLNAME+'\0'

    KSEP = '/'
    def kconcat(*kseq):
        return KSEP.join(str(k) for k in kseq)

    bottom_depth = dsu.dict_depth(D_input)
    dhdr = {}
    def cache_header_get_key_list(depth, D):
        '''

        returns a sorted key list to be used to iterate over
        for building the row at the current depth level.

        SIDE EFFECT: looks through the header specification to
        see if the keys are present. if not, add them to the
        corresponding header depth in the specification.
        '''
        if isinstance(D, dict):
            key_list_with_type = sorted([(type(v) is list and 1 or 0, k) for k, v in D.iteritems()])
            sorted_key_list = [pair[1] for pair in key_list_with_type]
        elif isinstance(D, list):
            pass
        else: raise Exception('input data not dict or list')

        if depth not in dhdr:
            dhdr[depth] = []
            if isinstance(D, dict):
                dhdr[depth].extend(sorted_key_list)
            else:
                dhdr[depth].append(ORD_COLNAME)
        return sorted_key_list

    data = []

    RecurStruct = namedtuple('RecurStruct', ['next_D', 'next_depth', 'insert_item', 'insert_index'])
    def recur(D, depth=1, prepend=None):

        if prepend is None:
            prepend = []

        to_recur = []

        if isinstance(D, list):
            ### NOTE XXX this is not well tested.
            # since a list of lists will immediately generate a new depth in
            # dhdr (because) we will check if the current list's depth has
            # anything in dhdr.  if not, assume it's the first time we've
            # reached this depth, and thus, we need to create a column name for
            # the list.
            if D and depth not in dhdr:
                cur_depth_hdr_list = dhdr.get(depth, [])
                dhdr[depth] = cur_depth_hdr_list + ['%s%s' % (ORD_COLNAME.strip('\0'), 1+len(cur_depth_hdr_list))]
            to_recur.extend(RecurStruct(obj, depth+1, idx, None) for idx, obj in enumerate(D))
        else:
            idx = -1
            sorted_key_list = cache_header_get_key_list(depth, D)
            # for idx, key in enumerate(sorted_key_list):
            while idx < len(sorted_key_list)-1:
                idx += 1
                key = sorted_key_list[idx]
                val = D[key]
                if   isinstance(val, dict):
                    if depth < bottom_depth:
                        insert_key_list = []
                        for kk, vv in val.items():
                            insert_key_list.append(kconcat(key, kk))
                            prepend.append(vv)
                        updated_key_list = sorted_key_list[:idx] +insert_key_list+ sorted_key_list[idx+1:]
                        dhdr[depth] = dhdr[depth][:-len(sorted_key_list)] + updated_key_list
                        sorted_key_list = updated_key_list
                        idx += len(insert_key_list)-1
                    else:
                        # NOTE WARNING XXX this may have problems
                        to_recur.append(RecurStruct(val, depth+1, None, None))
                elif isinstance(val, list):

                    # COMMENTARY: need to offset the idx of the key by the
                    # length of the prepend row passed in from higher depths.
                    # else our insertion in the to_recur loop below will put
                    # the object earlier in the list than necessary.
                    # to illustrate:
                    # in depth 1, if you have
                    # [conf1, conf2, history, conf3], and history yields rows
                    # [cf1, cf2, hist1, cf3]
                    # [cf1, cf2, hist2, cf3],
                    # via an insertion index of 2
                    # (so the first row is from [cf1, cf2] + [hist1] + [cf3])
                    # if in the next generation you have history rows like
                    # [cf4, histb1]
                    # [cf4, histb2]
                    # you ultimately want a concatenated row looking like
                    # [cf1, cf2, hist1, cf3, cf4, histb1], etc
                    # but trickiness arises because the insertion index for
                    # this lower depth row should be 1, RELATIVE TO ITS OWN
                    # DEPTH. but previously we were still passing index 1. So
                    # the solution is to pad depth-relative index with the
                    # depth-absolute offset, as calculated here.  in this
                    # example, we want to pass 4+1 = 5 to the next recursion.
                    offset_from_previous_depth = sum([len(hdr) for hdepth, hdr in dhdr.items() if hdepth < depth])

                    # NOTE `empty_to_none()` below seems to handle appends
                    # of empty iterables into to_recur, so we don't need to
                    # wazawaza iterate over some precomputed dhdr
                    if len(val) is 0:
                        # this actually doesn't seem to change anything
                        to_recur.append(RecurStruct([], depth+2, 0, offset_from_previous_depth+idx))
                    else:
                        for ith, row in enumerate(val):
                            to_recur.append(RecurStruct(row, depth+2, ith, offset_from_previous_depth+idx))
                else:
                    if depth < bottom_depth:
                        prepend.append(val)

        for next_D, next_depth, insert_item, insert_index in to_recur:
            if insert_index is None:
                if insert_item is None:
                    next_prepend = prepend
                else:
                    next_prepend = prepend + [insert_item]
            else:
                next_prepend = prepend[:insert_index] + [insert_item] + prepend[insert_index:]
            recur(next_D, next_depth, next_prepend)

        if depth == bottom_depth:
            if   isinstance(D, dict): # unify empty list/dict, string into a single None entry.
                # this avoids collapse output looking like a single row
                # with '[]' as the value of some empty list column
                data.append(prepend + [empty_to_none(D.get(k)) for k in dhdr[depth]])
            # NOTE didn't do any testing with any of these this is just the
            # data type compatible thing to do
            elif isinstance(D, list):
                data.append(prepend + D)
            else:
                data.append(prepend + [D])

    recur(D_input)
    return [compile_header(dhdr)] + data

def uniquify_header(hdr):
    setting = dict((colname, {
        'should_process': count > 1,
        'format_string': '%%s%%0%dd' % len(str(count)),
        'total_added': 0,
        }) for colname, count in Counter(hdr).items())

    rtn = []
    for k in hdr:
        if setting[k]['should_process']:
            setting[k]['total_added'] += 1
            colname = setting[k]['format_string'] % (k, setting[k]['total_added'])
            rtn.append(colname)
        else:
            rtn.append(k)
    return rtn

def unravel_config(D_input):
    '''
    !!! NOT A SAFE FUNCTION (it alters the input argument) !!!

    utility function to prepare a given dict to be collapsed.

    input dict is assumed to have a 'config' key with an associated
    dict containing primitive key-value entries defining the config
    for the dict.

    this function will then return a "standard world" dict by
    placing all the key-value entries in `config` at the root level
    of the dict. e.g.

    input:
    D = {'config': {'version': 1, 'setting': 'blah'}, 'history': [{'rt': 0.23}, {'rt': 0.99}]}

    return:
    {'version': 1, 'setting': 'blah', 'history': [{'rt': 0.23}, {'rt': 0.99}]}
    '''
    D = D_input['config'].copy()
    for k, v in D_input.iteritems():
        if k == 'config': continue
        D[k] = v
    return D
        
def collapse_to_dataframe(D_input, *argv):

    if type(D_input.get('config')) is dict:
        processed = collapse(unravel_config(D_input), *argv)
    else:
        processed = collapse(D_input, *argv)
    # process column names and rename any duplicated columns
    hdr = uniquify_header(processed[0])
    if pd:
        return pd.DataFrame.from_records(processed[1:], columns=hdr)
    else:
        return [hdr] + processed[1:]

def collapse_2pass(D):

    LIST_INDEX_LABEL = '\0i'

    # first sweep to determine depth of graph
    # and full set of keys required to build header
    dkey_level = defaultdict(set)
    def sweep1(D, trav_path=None):
        trav_path = trav_path or []
        # not sure if good idea. doing this turns a list of primitives, like
        # 'choice': [1,2,3] into an as-is representation, meaning that the
        # resulting table gets a 'choice' column with a row value of '[1,2,3]'.
        # 
        # this has not been tested beyond being the quickest modification that
        # makes the Karpicke multiplication verification task data not raise an
        # exception
        if not isinstance(D, dict):
            return
        for k,v in D.iteritems():
            dkey_level[tuple(trav_path)].add(k)
            if isinstance(v, dict):
                sweep1(v, trav_path+[k])
            elif isinstance(v, list):
                for i, vv in enumerate(v):
                    sweep1(vv, trav_path+[k,LIST_INDEX_LABEL])
    sweep1(D)

    # sweep once to determine uniques,
    # i.e. to see if we need to add discriminator
    # numbers to end of header labels
    dkey_count = defaultdict(int)
    max_list_depth = 0
    for trav_path, level_set in dkey_level.items():
        for k in level_set:
            dkey_count[k] += 1
        max_list_depth = max(max_list_depth, trav_path.count(LIST_INDEX_LABEL))
    # build header
    header_mapping = {}
    for n, trav_path in enumerate(sorted(dkey_level.keys()), start=1):
        for k in dkey_level[trav_path]:
            if dkey_count[k] > 1:
                label = '{}{}'.format(k, n)
            else:
                label = k
            header_mapping[tuple(list(trav_path)+[k])] = label

    header_sorted = sorted(header_mapping.items(), key=lambda k: (len(k[0]), k[0]))[:]
    header_list = [header for _,header in header_sorted]
    key_sorted = [lvl_lbl for lvl_lbl,_ in header_sorted]

    # sweep again, to build output table
    out = []
    def sweep2(D, trav_path=None, trav_data=None, list_depth=0):
        trav_path = trav_path or []
        trav_data = trav_data or {}
        if list_depth == max_list_depth:
            out_data = trav_data.copy()

            for k, v in D.iteritems():
                out_data[tuple(trav_path+[k])] = v
            out.append(tuple(out_data.get(key) for key in key_sorted))
            return
        # lists need to be processed last
        to_recur = []
        for k,v in D.iteritems():
            if isinstance(v, dict):
                # has not been tested yet
                sweep2(v, trav_path+[k], trav_data, list_depth)
            elif isinstance(v, list):
                # questionable
                trav_data[tuple(trav_path+[k])] = None
                to_recur.append((k,v))
            else:
                trav_data[tuple(trav_path+[k])] = v
        for k,v in to_recur:
            if len(v) is 0 and list_depth < max_list_depth:
                # WARNING NOTE XXX
                # risky: assumes successive nested data structs
                # are ALL dict
                td = trav_data.copy()
                td[tuple(trav_path+[k])] = 0
                sweep2(
                    {},
                    trav_path+[k,LIST_INDEX_LABEL],
                    td,
                    list_depth+1)
            # HUMAN-friendly indexing
            for n, vv in enumerate(v, start=1):
                td = trav_data.copy()
                td[tuple(trav_path+[k])] = n
                sweep2(
                    vv,
                    trav_path+[k,LIST_INDEX_LABEL],
                    td,
                    list_depth+1)
    sweep2(D)

    out.insert(0, header_list)
    return out

def collapse_to_dataframe_2pass(D):
    allrow = collapse_2pass(D)
    return pd.DataFrame(allrow[1:], columns=allrow[0])

if __name__ == '__main__':

    import string
    import random

    try:
        import faker
    except:
        faker = None

    class Gen:
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

                if remaining is 0:
                    self.nresponse += 1
                    myd = self.generate_child()
                else:
                    myd = self.generate_parent(mydepth-remaining)
                    for iresponse in range(random.randint(2,7)):
                        myd['history'].append(recur(remaining - 1))
                return myd

            self.D = recur(mydepth)
            return self.D


    gen = Gen()
    gen.generate_nested(3)
    print(gen.nresponse, "generated")
    try:
        raw_input()
    except:
        input()

    NPRINT = 20
    for desc, fn in [('SINGLE PASS', collapse),
                     ('TWO PASS', collapse_2pass)]:

        print('\n')
        heading = '|| %s VERSION ||' % desc
        print('_'*(len(heading)))
        print(heading)
        print('`'*(len(heading)))
        processed = fn(gen.D)
        hdr_list  = uniquify_header(processed[0])
        padding = 2
        len_list = [len(hdr) for hdr in hdr_list]
        fmt_list = [('{:<%s}'+' '*padding)%(x) for x in len_list]
        nprint = 0
        for row in [hdr_list] + processed[1:]:
            line = ''.join([fmt.format(val) for fmt, val in zip(fmt_list, row)])
            print(line)
            nprint += 1
            if nprint == 1:
                print('-' * sum([x+padding for x in len_list]))
            if nprint > NPRINT: break
        print('---------------')
        print(nprint-1, 'printed')


