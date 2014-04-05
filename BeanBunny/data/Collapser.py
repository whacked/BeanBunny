import pandas as pd
from collections import Counter
from functools import wraps

import DataStructUtil as dsu

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
        rtn.extend(list(sorted(map(lambda s: s.replace('\0', ''), d[k]))))
    return rtn

@cached
def sorted_with_index(key_list):
    return sorted(enumerate(key_list), key=lambda x:x[1])

def collapse(D_input, ORD_COLNAME = 'number'):
    '''
    first.2 version (and probably very slow)

    takes a nested dict of arbitrary depth construct a 2d table for
    it

    children at the same depth are expected to have matching
    structure
    '''
    # reduces chance of collision although current code doesn't use
    # keycheck or set() so this doesn't actually do anything now
    ORD_COLNAME = '\0' + ORD_COLNAME

    dhdr = {}
    data = []

    def recur(D, depth=1, prepend=None):
        if type(D) is dict:
            sorted_key_list = list(sorted(D.keys()))
        elif type(D) is list:
            sorted_key_list = range(len(D))
        else:
            raise Exception('input data not dict or list')

        if prepend is None:
            prepend = []

        if depth not in dhdr:
            dhdr[depth] = []
            if type(D) is dict:
                dhdr[depth].extend(sorted_key_list)
            else:
                dhdr[depth].append(ORD_COLNAME)

        to_recur = []

        if type(D) is list:
            for idx in sorted_key_list:
                to_recur.append((D[idx], depth+1, [idx]))
        else:
            for key in sorted_key_list:
                val = D[key]
                if   type(val) is dict:
                    to_recur.append((val, depth+1, []))
                elif type(val) is list:
                    for ith, row in enumerate(val):
                        to_recur.append((row, depth+2, [ith]))
                else:
                    if depth < bottom_depth:
                        prepend.append(val)

        for next_D, next_depth, next_prepend in to_recur:
            recur(next_D, next_depth, prepend + next_prepend)
        if depth == bottom_depth:
            if   type(D) is dict:
                data.append(prepend + [D[k] for k in dhdr[depth]])
            # NOTE didn't do any testing with any of these this is just the
            # data type compatible thing to do
            elif type(D) is list:
                data.append(prepend + D)
            else:
                data.append(prepend + [D])

    bottom_depth = dsu.dict_depth(D_input)
    recur(D_input)
    return [compile_header(dhdr)] + data


def collapse_to_dataframe(D_input, *argv):
    processed = collapse(D_input, *argv)
    # process column names and rename any duplicated columns
    setting = dict((colname, {
        'should_process': count > 1,
        'format_string': '%%s%%0%dd' % len(str(count)),
        'total_added': 0,
        }) for colname, count in Counter(processed[0]).items())
    hdr = []
    for k in processed[0]:
        if setting[k]['should_process']:
            setting[k]['total_added'] += 1
            colname = setting[k]['format_string'] % (k, setting[k]['total_added'])
            hdr.append(colname)
        else:
            hdr.append(k)
    return pd.DataFrame.from_records(processed[1:], columns=hdr)


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
                return faker.Faker().username
            else:
                return lambda: ''.join([random.choice(string.letters) for i in range(6)])

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


    import matplotlib.pyplot as plt

    gen = Gen()
    gen.generate_nested(3)
    print gen.nresponse, "generated"
    raw_input()

    nprint = 0
    processed = collapse(gen.D)
    for row in processed:
        nprint += 1
        line = '\t'.join(map(lambda x: str(x)[:6], row))
        print line
        if nprint == 1:
            print '-' * (len(row)+line.count('\t')*8)
    print nprint-1, 'printed'



