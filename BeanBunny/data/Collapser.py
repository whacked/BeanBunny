from collections import Counter, namedtuple
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
    first.2 version (and probably very slow)

    takes a nested dict of arbitrary depth construct a 2d table for
    it

    children at the same depth are expected to have matching
    structure

    at present this cannot handle such a structure:
    {k1: v1,
     k2: v2,
     k3: {k3k1: k3v1},
     k4: [...]}
    the k3 dict will cause breakage.
    '''
    # reduces chance of collision although current code doesn't use
    # keycheck or set() so this doesn't actually do anything now
    ORD_COLNAME = ORD_COLNAME+'\0'

    dhdr = {}
    data = []

    RecurStruct = namedtuple('RecurStruct', ['next_D', 'next_depth', 'insert_item', 'insert_index'])
    def recur(D, depth=1, prepend=None):

        if prepend is None:
            prepend = []

        if isinstance(D, dict):
            sorted_key_list = sorted(D.keys())
        elif isinstance(D, list):
            pass
        else: raise Exception('input data not dict or list')

        if depth not in dhdr:
            dhdr[depth] = []
            if isinstance(D, dict):
                dhdr[depth].extend(sorted_key_list)
            else:
                dhdr[depth].append(ORD_COLNAME)

        to_recur = []

        if isinstance(D, list):
            to_recur.extend(RecurStruct(obj, depth+1, idx, None) for idx, obj in enumerate(D))
        else:
            for idx, key in enumerate(sorted_key_list):
                val = D[key]
                if   isinstance(val, dict):
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
            if   isinstance(D, dict):
                # unify empty list/dict, string into a single None entry.
                # this avoids collapse output looking like a single row
                # with '[]' as the value of some empty list column
                data.append(prepend + [empty_to_none(D[k]) for k in dhdr[depth]])
            # NOTE didn't do any testing with any of these this is just the
            # data type compatible thing to do
            elif isinstance(D, list):
                data.append(prepend + D)
            else:
                data.append(prepend + [D])

    bottom_depth = dsu.dict_depth(D_input)
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

if __name__ == '__main__':

    import string
    import random

    if True:
        # another test case
        import sys
        import re
        from termcolor import colored
        HIST1 = '0 history1'
        HIST2 = '1 history2'
        d = {
                'config': {'1 config-key': '1 config-value'},
                HIST1: [
                    {'2 onset': 123,
                     '2 answer': 'ab',
                     HIST2: [
                         {'3 switch': 'sw1',
                          '3 char': 'b',
                          }
                     ]
                     },
                    {'2 onset': 841,
                     '2 answer': 'we',
                     HIST2: [
                         {'3 switch': 'sw3',
                          '3 char': 'w',
                          }
                     ]
                     },
                ]
        }

        expected = '''\
0 history1      0               1
1 config-key    1 config-value  1 config-value
1 history2      0               0
2 answer        ab              we
2 onset         123             841
3 char          b               w
3 switch        sw1             sw3
'''.strip()

        d = {
            "history": [
                {
                    "expected": "answer 1",
                    "key": "key-1",
                    "history": [
                        {
                            "character": "s",
                            "onset": 1
                        }
                    ],
                    "received": "[ESC]",
                    "duration": 25422
                },
                {
                    "expected": "answer 2",
                    "key": "key-2",
                    "history": [
                        {
                            "character": "n",
                            "onset": 0
                        },
                        {
                            "character": "z",
                            "onset": 139
                        },
                        {
                            "character": "y",
                            "onset": 135
                        }
                    ],
                    "received": "attempt 2",
                    "duration": 1983
                },
                {
                    "expected": "answer 3",
                    "key": "key 3",
                    "history": [
                        {
                            "character": "e",
                            "onset": 0
                        },
                        {
                            "character": "r",
                            "onset": 45
                        }
                    ],
                    "received": "answer 3",
                    "duration": 1111
                }
                ],
                    "config": {
                        "my-version": 'ver. 1',
                        "a-conf-value": 0.71,
                        "g-conf-value": 1.01,
                        "z-conf-value": 1.5,
                        "xyz": {'a': 'a8', 'b': 'b1',},
                        }
            }
        expected = '''\
a-conf-value  0.71          0.71          0.71          0.71          0.71          0.71
g-conf-value  1.01          1.01          1.01          1.01          1.01          1.01
history1      0             1             1             1             2             2
my-version    ver. 1        ver. 1        ver. 1        ver. 1        ver. 1        ver. 1
z-conf-value  1.5           1.5           1.5           1.5           1.5           1.5
duration      25422         1983          1983          1983          1111          1111
expected      answer 1      answer 2      answer 2      answer 2      answer 3      answer 3
key           key-1         key-2         key-2         key-2         key 3         key 3
history2      0             0             1             2             0             1
received      [ESC]         attempt 2     attempt 2     attempt 2     answer 3      answer 3
character     s             n             z             y             e             r
onset         1             0             139           135           0             45
xyz/a         a8            a8            a8            a8            a8            a8
xyz/b         b1            b1            b1            b1            b1            b1
        '''.strip()
        dexpected = dict(re.split(r'\s{2,}', line, 1) for line in expected.split('\n'))

        col = collapse(unravel_config(d))
        maxlenk = max(map(lambda s: len(str(s)), col[0]))
        maxlenv = max(map(lambda s: len(str(s)), [v for vrow in col for v in vrow]))

        print('= ' * 40)
        for vlist in zip(uniquify_header(col[0]), *col[1:]):
            key = vlist[0]
            sval = (' '.join([str(v).ljust(maxlenv+1) for v in vlist[1:]])).strip()

            if sval == dexpected[key]:
                print(colored(sval, 'green', None, ['bold']))
            else:
                print(colored(sval, 'red', None, ['bold']))
                print(colored(dexpected[key], 'blue', None, ['bold']))
        sys.exit()

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
                return faker.Faker().username
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

    processed = collapse(gen.D)
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
        if nprint > 10: break
    print(nprint-1, 'printed')



