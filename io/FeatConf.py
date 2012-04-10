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
    def __getitem__(self, key):
        return self.dc_index[key]

    def __setitem__(self, key, val):
        if key not in self.dc_index:
            print "WARNING: setting new item [%s]" % key
        self.dc_index[key].value = val

    def __delitem__(self, key):
        idx = self.index(key)
        fe = self.dc_index[key]
        del self.ls_entry[idx]
        del self.dc_index[key]
        return fe

    def __init__(self, fl_input):
        if type(fl_input) == types.StringType:
            if len(fl_input) < 255 and os.path.exists(fl_input):
                ls_line = open(fl_input).readlines()
            else:
                ls_line = fl_input.split("\n")
                ls_line[-1] += "\n"
        else:
            ls_line = fl_input.readlines()

        self.ls_entry = []
        self.dc_index = {}
        entrypattern = re.compile(r'^set\s+(\S+)\s+(.*)$')

        self.ls_groupmem = []

        commentbuf = []
        for line in ls_line:
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

    def find(self, matcher):
        p = re.compile(matcher)
        rtn = {}
        for k in self.dc_index.keys():
            if p.match(k):
                rtn[k] = self[k]
        return rtn

    def complain_if_exists(self, fe):
        if fe.name in self.dc_index:
            raise Exception("this entry already exists")

    def append(self, fe):
        self.complain_if_exists(fe)
        self.ls_entry.append(fe)
        self.dc_index[fe.name] = fe

    def index(self, key):
        return [fe.name for fe in self.ls_entry].index(key)

    def insert(self, idx, fe):
        self.complain_if_exists(fe)
        self.ls_entry.insert(idx, fe)
        self.dc_index[fe.name] = fe

    def remove_feat_input(self, p_match):
        """remove from the 4D or feat directory input list, and rebuild output structure
        this is a very dumb function and only assumes 1 group type and 1 EV type!
        
        make sure your fsf fits this use case!
        
        Arguments:
        - `p_match`: the regex to match
        """
        ls_feat_files = []
        idx, end = 0, len(self.ls_entry)
        while idx < end:
            fe = self.ls_entry[idx]
            if any(map(lambda search: fe.name.startswith(search),
                       ["feat_files",
                        "fmri(evg",
                        "fmri(groupmem"])):
                # exclude anything that matches from the new buffer
                if fe.name.startswith("feat_files"):
                    if not re.match(p_match, fe.value):
                        ls_feat_files.append(fe.value)
                    else:
                        print "removing: " + fe.value
                del self.dc_index[fe.name]
                del self.ls_entry[idx]
                end -= 1
            else:
                idx += 1
        
        # rebuild
        idx = 0
        while idx < len(self.ls_entry):
            fe = self.ls_entry[idx]
            make_fe = None
            if fe.name == "fmri(confoundevs)":
                make_fe = lambda num, feat_file: FeatEntry("feat_files(%s)" % num, feat_file, "4D AVW data or FEAT directory (%s)" % num)
            elif fe.name == "fmri(level2orth)":
                make_fe = lambda num, feat_file: FeatEntry("fmri(evg%s.1)" % num, "1.0", "Higher-level EV value for EV 1 and input %s" % num)
            elif fe.name == "fmri(con_mode_old)":
                make_fe = lambda num, feat_file: FeatEntry("fmri(groupmem.%s)" % num, "1", "Group membership for input %s" % num)

            if make_fe:
                num_feat_file = 0
                for feat_file in ls_feat_files:
                    num_feat_file += 1
                    fenew = make_fe(num_feat_file, feat_file)
                    self.dc_index[fenew.name] = fenew
                    self.ls_entry.insert(idx, fenew)
                    idx += 1
            idx += 1
            
        self.dc_index["fmri(npts)"].value = len(ls_feat_files)
        self.dc_index["fmri(multiple)"].value = len(ls_feat_files)

if __name__ == "__main__":
    
    if len(sys.argv) < 2:
        print """USAGE: FeatConf.py <OPTION> <featfile.fsf>
        -c    list contrasts
        -p    print everything (echo... to test output)
        """
    fsf_file = sys.argv[-1]
    if not os.path.exists(fsf_file):
        print "the file does not exist!"
        sys.exit(1)

    def sort_by_dotnumber(t1, t2):
        getnum = lambda s: int(s.split(".")[-1][:-1])
        return getnum(t1[0]) > getnum(t2[0]) and 1 or -1

    FC = FeatConf(fsf_file)
    if "-p" in sys.argv:
        print str(FC)
    else:
        res = None
        if "-c" in sys.argv:
            res = FC.find(r'.*conname_real.*')
        elif "-i" in sys.argv:
            res = FC.find(r'.*feat_files.*')
        if res:
            maxlenk = max(map(len, res.keys()))
            for k, v in sorted(res.items(), sort_by_dotnumber):
                print " " + k.ljust(maxlenk + 1) + ": " + v
