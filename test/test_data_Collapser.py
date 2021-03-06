import sys
sys.path.insert(0, '.')
from BeanBunny.data import Collapser
from BeanBunny.data import DataStructUtil as dsu
import string
import random

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


if __name__ == '__main__':
    test_1pass_2pass_ideal_equality()
