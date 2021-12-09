from collections import Counter, namedtuple, defaultdict
from functools import wraps

import BeanBunny.data.DataStructUtil as dsu
import logging
import flatten_dict
import operator


try:
    import pandas as pd
except Exception:
    logging.warning('could not import pandas, export to dataframe will not work')
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
            key_list_with_type = sorted([(type(v) is list and 1 or 0, k) for k, v in D.items()])
            sorted_key_list = [pair[1] for pair in key_list_with_type]
        elif isinstance(D, list):
            pass
        else: raise Exception('input data not dict or list')
        sorted_key_list.sort()

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
                    if len(val) == 0:
                        # this actually doesn't seem to change anything
                        to_recur.append(RecurStruct([], depth+2, 0, offset_from_previous_depth+idx))
                    else:
                        for ith, row in enumerate(val, start=1):
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
    if type(D_input.get('config')) is not dict:
        return D_input
    D = D_input.get('config', {}).copy()
    for k, v in D_input.items():
        if k == 'config': continue
        D[k] = v
    return D
        
def collapse_to_dataframe(D_input, *argv):
    processed = collapse(unravel_config(D_input), *argv)
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
        for k,v in D.items():
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

            for k, v in D.items():
                out_data[tuple(trav_path+[k])] = v
            out.append(tuple(out_data.get(key) for key in key_sorted))
            return
        # lists need to be processed last
        to_recur = []
        for k,v in D.items():
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
            if len(v) == 0 and list_depth < max_list_depth:
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
    processed = collapse_2pass(unravel_config(D))
    return pd.DataFrame(processed[1:], columns=processed[0])

def flatten_list(l):  # ref https://stackoverflow.com/a/2158532
    for el in l:
        if isinstance(el, list):
            yield from flatten_list(el)
        else:
            yield el

def get_in(D, path):
    if len(path) == 0:
        return D
    if path[0] == [] and isinstance(D, list):
        return [get_in(sub_D, path[1:]) for sub_D in D]
    return get_in(D.get(path[0]), path[1:])

def rindex(lst, value):  # https://stackoverflow.com/a/63834895
    return len(lst) - operator.indexOf(reversed(lst), value) - 1

def all_same_type(elements):
    if len(elements) < 2:
        return True
    first_element_type = type(elements[0])
    return all(type(element) == first_element_type for element in elements)

def dict_structurally_equivalent(d1, d2):
    return set(d1) == set(d2)

def get_leafiest_path(D_orig):
    paths_of_iterables = set()
    for path in dsu.walk_dict_keys(D_orig):
        try:
            last_list_index = rindex(path, [])
        except:
            last_list_index = len(path)
        paths_of_iterables.add(dsu.to_tuple(path[:last_list_index]))

    ranked_paths = []
    for tuplefied_path in paths_of_iterables:
        path = dsu.to_list(tuplefied_path)
        maybe_nested_elements = get_in(D_orig, path)

        if not isinstance(maybe_nested_elements, (tuple, list, dict)):
            ranked_paths.append((1, len(tuplefied_path), dsu.to_list(tuplefied_path)))
            continue
        
        if len(maybe_nested_elements) == 0:
            continue

        if isinstance(maybe_nested_elements[0], list):
            elements = list(flatten_list(maybe_nested_elements))
            num_elements = max(len(sub_elements) for sub_elements in maybe_nested_elements)
        else:
            elements = maybe_nested_elements
            num_elements = len(elements)
        if not isinstance(elements[0], dict):
            continue
        if not all_same_type(elements):
            continue
        if not all(dict_structurally_equivalent(elements[0], el) for el in elements[1:]):
            continue
        # weight first by most leaves
        # then by highest up the tree
        ranked_paths.append((num_elements, 1/len(path), path))
    ranked_paths.sort()
    if ranked_paths:
        return ranked_paths[-1][-1]
    return []


def tree2flattend(tree, prefix_path=None, depth=0):
    if prefix_path is None:
        prefix_path = []
    if not isinstance(tree, dict):
        return [tree]
    sub_item_paths = dsu.walk_dict_keys(tree)
    if not sub_item_paths:
        return []
    leafiest_path = get_leafiest_path(tree)

    shared_data = {}
    for path in sub_item_paths:
        if path[:len(leafiest_path)] == leafiest_path:
            continue

        if isinstance(path[-1], list):
            add_path = path[:-1]
        else:
            add_path = path
        shared_value = get_in(tree, add_path)
        shared_data[dsu.to_tuple(prefix_path + add_path)] = shared_value

    out = []

    if not leafiest_path:
        for k, v in tree.items():
            thing = {k: tree2flattend(v, prefix_path, depth+1)}
        return [tree]

    leafiest_root = get_in(tree, leafiest_path)
    if not isinstance(leafiest_root, (tuple, list, dict)):
        shared_data[dsu.to_tuple(prefix_path + leafiest_path)] = leafiest_root
        return [shared_data]

    for i, leaf_item in enumerate(leafiest_root):
        if not isinstance(leaf_item, dict):
            continue

        leaf_writeouts = []
        # leaf_writeout = shared_data.copy()
        combined_leaf_writeout = {}
        for leaf_key, leaf_val in leaf_item.items():
            if isinstance(leaf_val, dict):
                expanded = flatten_dict.flatten(leaf_val)
                for expanded_key, expanded_val in expanded.items():
                    leaf_writeout = shared_data.copy()
                    subkey = leafiest_path + [[], leaf_key] + list(expanded_key)
                    leaf_writeout[dsu.to_tuple(subkey)] = expanded_val
            else:
                combined_leaf_writeout.update(shared_data.copy())
                full_leaf_key = dsu.to_tuple(prefix_path + leafiest_path + [[], leaf_key])
                combined_leaf_writeout[full_leaf_key] = leaf_val
        if combined_leaf_writeout:
            leaf_writeouts.append(combined_leaf_writeout)
        out.extend(leaf_writeouts)

    return out


def tree2tabular(tree):
    if not isinstance(tree, dict):
        return []
    leafiest_path = get_leafiest_path(tree)

    shared_data = {}
    for path in dsu.walk_dict_keys(tree):
        if leafiest_path and path[:len(leafiest_path)] == leafiest_path:
            continue

        if isinstance(path[-1], list):
            add_path = path[:-1]
        else:
            add_path = path
        shared_value = get_in(tree, add_path)
        shared_data[dsu.to_tuple(add_path)] = shared_value

    leafiest_root = get_in(tree, leafiest_path)
    table_body = []
    if not isinstance(leafiest_root, (list, tuple, dict)):
        table_body.append({
            dsu.to_tuple(leafiest_path): leafiest_root,
        })
    else:
        for i, leaf_item in enumerate(leafiest_root):
            if not isinstance(leaf_item, dict):
                continue

            for sub_element in tree2flattend(leaf_item, leafiest_path + [[]]):
                table_body.append(sub_element)

    if not table_body:
        return []

    table_head = [dsu.to_list(k) for k in shared_data.keys()]
    for key in table_body[0].keys():
        if isinstance(key, tuple):
            table_head.append(dsu.to_list(key))
        else:
            table_head.append([key])

    out = [table_head] + [
        list(shared_data.values()) + list(row.values())
        for row in table_body
    ]
    return out

