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

def collapse(D_input):
    '''
    first version (and probably very slow)

    takes a nested dict of arbitrary depth construct a 2d table for
    it

    children at the same depth are expected to have matching
    structure
    '''

    @cached
    def compile_header(d):
        '''
        note d should be a dict where keys are depth value and
        values are lists of str
        '''
        rtn = []
        for k in sorted(d.keys()):
            rtn.extend(list(sorted(d[k])))
        return rtn

    def compile_data(dhdr, data):
        '''
        return a flatted row for data, based on the kind of
        ordering we'd get from calling compile_header in the header
        dict
        '''
        rtn = []
        for k in sorted(dhdr.keys()):
            if not data[k]: continue
            for key_index, key_sorted in sorted(enumerate(dhdr[k]), key=lambda v:v[1]):
                rtn.append( data[k][key_index] )
        return rtn

    dhdr = {} # store header names
    dcat = {} # store (repeat) categorical data
    data = []
    def recur(D, depth = 1):

        if depth not in dhdr:
            key_list = []
            for k in D.keys():
                if type(D[k]) is not list:
                    key_list.append(k)
            dhdr[depth] = key_list

        # unlike header, the categorical stuff gets rewritten every pass!
        dcat[depth] = []

        # save this, so we can recur to next level after everything at current
        # level has been processed
        to_recur = []
        for k, v in D.iteritems():
            if type(v) is list:
                for row in v:
                    # list itself is 1 depth
                    to_recur.append((row, depth+2))
            else:
                dcat[depth].append(v)
        for argv in to_recur:
            recur(argv[0], argv[1])
        if depth == bottom_depth:
            # hit bottom.
            # at this point, if the data is well-formed, dhdr should contain
            # all the header names we need
            data.append(compile_data(dhdr, dcat))

    # everything less than this depth should provide category variables
    bottom_depth = dsu.dict_depth(D_input)

    recur(D_input)

    return [compile_header(dhdr)] + data


def collapse_to_dataframe(D_input):
    processed = collapse(D_input)
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
            print '-' * (len(line)+line.count('\t')*1)
    print nprint-1, 'printed'



