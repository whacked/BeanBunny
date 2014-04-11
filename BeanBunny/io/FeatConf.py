import os, sys, types, re

# supposed to contain a class, FeatConf, to ease working with fsf files in
# python.  started as a quick-and-dirty parsing class with little semantic
# knowledge of the fsf file, but now I'm using this in several places, this
# code has a bunch of uglinesses that would require a search-and-replace in the
# other scripts to fix. Which I should do. But for the time being we'll be
# incrementally adding some more intelligence to the class in inelegant ways.

class FeatEntry:
    p = re.compile(r'''([^(]+)\((.+)\)''')

    # starting version 1, field quotes will be stripped
    VERSION = 1
    STRIP_QUOTES = True

    def _trim(self, s):
        if isinstance(s, basestring):
            return s.strip('"')
        else:
            return s

    def __init__(self, name, value, comment):
        self._is_keyword = False

        self.name = name
        match = self.p.match(name)
        self.groupname, self.entrykey = match.groups()
        if self.groupname == 'feat_files':
            self.entrykey = int(self.entrykey)
        elif self.entrykey.startswith("con_mode"):
            self._is_keyword = True
        elif self.entrykey == "unwarp_dir":
            self._is_keyword = True
        elif '"' not in value:
            # assume numeric
            if '.' in value:
                value = float(value)
            elif value.isdigit():
                value = int(value)
        if self.STRIP_QUOTES:
            value = self._trim(value)
        self.value = value
        self.comment = comment

    def renderedvalue(self):
        if not self.STRIP_QUOTES:
            return self.value
        if isinstance(self.value, basestring) and not self._is_keyword:
            return '"%s"' % self.value
        else:
            return self.value

    def __str__(self):
        return \
            (self.comment and '# %s\n' % self.comment.replace('\n', '\n# ') or '') + \
            'set %s %s' % (self.name, self.renderedvalue())

    def __repr__(self):
        return str(self)
        

class Bunch(dict):
    def __init__(self, **kw):
        dict.__init__(self, kw)
        self.__dict__ == self
    __getattr__ = dict.__getitem__
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__


class FeatConf:

    FEATVERSION = 5.98

    def output_order(self):
        out = []
        for key in """\
version
inmelodic
level
analysis
relative_yn
help_yn
featwatcher_yn
sscleanup_yn
outputdir
tr
npts
ndelete
tagfirst
multiple
inputtype
filtering_yn
brain_thresh
critical_z
noise
noisear
newdir_yn
mc
sh_yn
regunwarp_yn
dwell
te
signallossthresh
unwarp_dir
st
st_file
bet_yn
smooth
norm_yn
perfsub_yn
temphp_yn
templp_yn
melodic_yn
stats_yn
prewhiten_yn
motionevs
robust_yn
mixed_yn
evs_orig
evs_real
evs_vox
ncon_orig
ncon_real
nftests_orig
nftests_real
constcol
poststats_yn
threshmask
thresh
prob_thresh
z_thresh
zdisplay
zmin
zmax
rendertype
bgimage
tsplot_yn
reg_yn
reginitial_highres_yn
reginitial_highres_search
reginitial_highres_dof
reghighres_yn
reghighres_search
reghighres_dof
regstandard_yn
regstandard
regstandard_search
regstandard_dof
regstandard_nonlinear_yn
regstandard_nonlinear_warpres
paradigm_hp
ncopeinputs
copeinput.1
""".strip().split():
            out.append(str(self.fmri[key]))

        # feat_files section
        for feat_file_num in range(1, len(self.feat_files)+1):
            out.append(str(self.feat_files[feat_file_num]))
# TODO
# keys that get created per event and group etc.
# e.g. evtitle1, groupmem.1 and stuff like that
# these were laid out in an old modification
# and i no longer remember the original intention
# axh Mon Feb 18 17:55:35 EST 2013
# ---
# evtitle
# shape
# convolve
# convolve_phase
# tempfilt_yn
# deriv_yn
# custom
# ortho
# evg
# groupmem
# conpic_real
# conname_real
# con_real
# conmask
# ...

        for key in """\
confoundevs
alternative_example_func
alternative_mask
init_initial_highres
init_highres
init_standard
overwrite_yn
level2orth
con_mode_old
con_mode
conmask_zerothresh_yn
""".strip().split():
            out.append(str(self.fmri[key]))
        return "\n\n".join(out)

    def __setitem__(self, key, val):
        if key not in self.dc_index:
            print("WARNING: setting new item [%s]" % key)
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

                if not hasattr(self, fe.groupname):
                    setattr(self, fe.groupname, Bunch())
                self.__dict__[fe.groupname][fe.entrykey] = fe

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
                        print("removing: " + fe.value)
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

    from optparse import OptionParser

    parser = OptionParser()
    parser.add_option("-c", "--contrast_list", action="store_true",
            help = "list contrasts")
    parser.add_option("-i", "--input_list", action="store_true",
            help = "list inputs")
    parser.add_option("-p", "--print_everything", action="store_true",
            help = "print everything (echo... to test output)")
    (options, args) = parser.parse_args()
    
    if len(sys.argv) < 2:
        parser.print_help()
        sys.exit()

    fsf_file = sys.argv[-1]
    if not os.path.exists(fsf_file):
        print("the file does not exist!")
        sys.exit(1)

    def sort_by_dotnumber(t1, t2):
        p = re.compile(r'\D*(\d+)\D*')
        def getnum(s):
            m = p.match(s)
            return m and int(m.group(1)) or 0
        return getnum(t1[0]) > getnum(t2[0]) and 1 or -1

    FC = FeatConf(fsf_file)
    if options.print_everything:
        print(str(FC))
    else:
        res = None
        if options.contrast_list:
            res = FC.find(r'.*conname_real.*')
        elif options.input_list:
            res = FC.find(r'.*feat_files.*')
        if res:
            maxlenk = max(map(len, res.keys()))
            for k, v in sorted(res.items(), sort_by_dotnumber):
                print(" " + k.ljust(maxlenk + 1) + ": " + v)
