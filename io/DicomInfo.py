import os, subprocess
from string import Template
from nibabel import load
from nipype.interfaces.base import Bunch, load_template

class PulseSequence(object):
    _LS_ATTR = None
    def __init__(self, imgnum, filename, number, ignore0, ignore1, ignore2, x, y, numslice, ntp, TR, ignore3, name):
        """
        Arguments:
        - `ntp`: number of time points
        """
        dcarg = locals()
        if self.__class__._LS_ATTR is None:
            self.__class__._LS_ATTR = [k for k in dcarg.keys() if k != "self"]
        for attr in self.__class__._LS_ATTR: setattr(self, attr, dcarg[attr].isdigit() and int(dcarg[attr]) or dcarg[attr])
        self.type = "unknown"
    def __str__(self):
        return " ".join([str(getattr(self, attr)) for attr in self.__class__._LS_ATTR])

class DicomInfo(object):
    """easier reading of cfg files
    """
    def parse_line(self, line):
        "dumb version of parse line, get PulseSequence object"
        return PulseSequence(*line.strip().split())
    
    def isMoco(self, dcmfile):
        """Determine if a dicom file is a mocoseries
        """
        proc  = subprocess.Popen(['mri_probedicom', '--i', dcmfile, '--t', '8', '103e'],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        return stdout.strip().startswith('MoCoSeries')

    def __init__(self, mixed_cfg_input, dicom_dir):
        """
        Arguments:
        - `mixed_cfg_input`: either file, filepath, or config text
        """
        if type(mixed_cfg_input) == file:
            str_cfg = mixed_cfg_input.read()
        elif type(mixed_cfg_input) == str:
            # multiple lines, assume cfg text
            if mixed_cfg_input.strip().count("\n"): str_cfg = mixed_cfg_input
            # assume filepath
            else: str_cfg = open(mixed_cfg_input).read()
        self.ls_cfg = [self.parse_line(line) for line in str_cfg.strip().split("\n")]
         
        self.info = dict([(scantype, []) for scantype in
                          ("bold", "dwi", "field_mapping", "3danat", "resting")])
        # heuristic function for sorting out which runs to unpack + which are MoCo
        for seq in self.ls_cfg:
            if   ("MPRAGE"            in seq.name) and (seq.numslice == 176) and (seq.ntp == 1):
                seq.type = "3danat"
            elif \
                    (("func"              in seq.name) and (seq.ntp > 100)) or \
                    (("ep2d"              in seq.name) and (seq.ntp > 100)) :
                if self.isMoco(os.path.join(dicom_dir, seq.filename)):
                    continue
                seq.type = "bold"
            #elif ("DIFFUSION"         in seq.name) and (seq.numslice > 1) and (seq.ntp > 25):
            #    seq.type = "dwi"
            elif ("resting"           in seq.name):
                seq.type = "resting"
            elif ("field_mapping"     in seq.name):
                seq.type = "field_mapping"
            if seq.type in self.info:
                self.info[seq.type].append(seq.number)
