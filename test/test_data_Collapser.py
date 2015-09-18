import sys
sys.path.insert(0, '.')
from BeanBunny.data import Collapser
import string
import random

try:
    import faker
except:
    faker = None

IS_CLI = __name__ == '__main__'

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


def test_1pass_2pass_ideal_equality():
    gen = Gen()
    gen.generate_nested(3)
    print(gen.nresponse, "generated")

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
    print '1pass and 2pass are the same!'


if __name__ == '__main__':
    test_1pass_2pass_ideal_equality()
