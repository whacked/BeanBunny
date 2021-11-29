import sys
sys.path.insert(0, '.')
from BeanBunny.data import Collapser
from BeanBunny.data import DataStructUtil as dsu
import string
import random
from unittest import TestCase

try:
    import faker
except:
    faker = None

IS_CLI = __name__ == '__main__'

def test_1pass_2pass_ideal_equality():
    gen = dsu.DictGenerator()
    gen.generate_nested(3)
    print(gen.nresponse, "generated")
    # doing this will break the equivalence
    # due to how additional nested dicts are
    # processed across versions.
    # gen.D['config'] = {'a': 1, 'b': 'mouse'}
    # adding this will equalize it
    # gen.D = Collapser.unravel_config(gen.D)

    out = []
    NPRINT = 20
    for desc, fn in [('SINGLE PASS', Collapser.collapse),
                     ('TWO PASS', Collapser.collapse_2pass)]:

        if IS_CLI:
            print('\n')
            heading = '|| %s VERSION ||' % desc
            print('_'*(len(heading)))
            print(heading)
            print('`'*(len(heading)))
        processed = fn(gen.D)
        hdr_list  = Collapser.uniquify_header(processed[0])
        padding = 2
        len_list = [len(hdr) for hdr in hdr_list]
        fmt_list = [('{:<%s}'+' '*padding)%(x) for x in len_list]
        nprint = 0

        buf = []
        for row in [hdr_list] + processed[1:]:
            line = ''.join([fmt.format(val) for fmt, val in zip(fmt_list, row)])
            buf.append(line)
            nprint += 1
            if IS_CLI:
                print(line)
                if nprint == 1:
                    print('-' * sum([x+padding for x in len_list]))
            if nprint > NPRINT: break
        if IS_CLI:
            print('---------------')
            print(nprint-1, 'printed')
        out.append('\n'.join(buf))
    assert out[0] == out[1]
    print('1pass and 2pass are the same!')


def test_simple_collapse():
    source_data = {
        'weather': [
            {'feeling': 'fine', 'celsius': 22},
            {'feeling': 'hot', 'celsius': 32},
        ],
    }

    collapsed = Collapser.collapse(source_data)
    TestCase().assertListEqual(collapsed, [
        ['weather', 'celsius', 'feeling',],
        [1, 22, 'fine'],
        [2, 32, 'hot'],
    ])


def test_walk_dict_keys():  # MOVEME
    TestCase().assertListEqual(
        dsu.walk_dict_keys({
            'a': {
                'b': {
                    'c': 1
                }
            },
            'x': {
                'y': 2,
                'z': 3,
            },
            'w': [1, 2],
            '?': [
                {'QQ': 'PP', 'J': 'j', 'alice': 'apple'},
                {'QQ': 'TT', 'J': 'k', 'bob': 'banana'},
            ],
            '_': {
                3: [4, 5,],
                6: 7,
            }
        }),
        [
            ['a', 'b', 'c'],
            ['x', 'y'],
            ['x', 'z'],
            ['w', []],
            ['?', [], 'QQ'],    # this order has no guarantee
            ['?', [], 'J'],
            ['?', [], 'alice'],
            ['?', [], 'bob'],
            ['_', 3, []],
            ['_', 6],
        ]
    )

def test_nested_collapse():
    D = {
            'shared': {
                'a': 1,
                'b': 'C',
                'd': ['e', 'f'],
            },
            '[complex,key]': {
                '[more,complex]': [
                    {'rt': 123, 'r': 'foo'},
                    {'rt': 456, 'r': 'bar'},
                    {'rt': 789, 'r': 'baz'},
                ]
            },
        }
    tabularized = Collapser.tree2tabular(D)
    TestCase().assertListEqual(
        tabularized,
        [
            # note they key order is not guaranteed
            # the test order is matched manually
            [ ['shared', 'a'], ['shared', 'b'], ['shared', 'd'], ['[complex,key]', '[more,complex]', [], 'rt'], ['[complex,key]', '[more,complex]', [], 'r'], ],
            [1, 'C', ['e', 'f'], 123, 'foo'],
            [1, 'C', ['e', 'f'], 456, 'bar'],
            [1, 'C', ['e', 'f'], 789, 'baz'],
        ]
    )


if __name__ == '__main__':
    test_1pass_2pass_ideal_equality()
