import os, sys, types, re

class FeatEntry:
    def __init__(self, name, value, comment):
        self.name = name
        self.value = value
        self.comment = comment

    def __str__(self):
        return \
            (self.comment and '# %s\n' % self.comment.replace('\n', '\n# ') or '') + \
            'set %s %s' % (self.name, self.value)

    def __repr__(self):
        return str(self)
        

class FeatConf:
    def __init__(self, fl_input):
        if type(fl_input) == types.StringType:
            fl_input = open(fl_input)

        self.ls_entry = []
        self.dc_index = {}
        entrypattern = re.compile(r'^set\s+(\S+)\s+(.*)$')

        commentbuf = []
        for line in fl_input.readlines():
            line = line.strip()
            if len(line) is 0 and len(commentbuf) is 0:
                continue
            if line.startswith('#'):
                commentbuf.append(line[2:])
            elif line.startswith('set '):
                match = entrypattern.match(line).groups()
                fe = FeatEntry(match[0], match[1], "\n".join(commentbuf))
                commentbuf = []
                self.dc_index[fe.name] = fe
                self.ls_entry.append(fe)

    def __getitem__(self, name):
        return self.dc_index.get(name).value

    def __str__(self):
        return "\n\n".join([str(fe) for fe in self.ls_entry])

if __name__ == "__main__":
    testfile = "/Users/Shared/MRIDATA/analysis-FSL/OC/design/level1/pre.fsf"
    FC = FeatConf(testfile)
    open("testout.fsf", "w").write(str(FC))
    print len(str(FC)), len(open(testfile).read())
    print str(FC) == open(testfile).read()
