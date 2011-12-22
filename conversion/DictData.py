import csv, copy

class DataSet(object):
    dc_header = {}
    @classmethod
    def headerrow(selfclass):
        return sorted(selfclass.dc_header.keys())
    def __init__(self, **kw):
        for k, v in kw.items():
            self[k] = v
    def __setattr__(self, k, v):
        self[k] = v
    def __setitem__(self, k, v):
        self.__dict__[k] = v
        if k not in self.__class__.dc_header:
            self.__class__.dc_header[k] = len(self.__class__.dc_header)
    def __getitem__(self, k):
        return self.__dict__[k]
    def datarow(self):
        return [self.__dict__.get(k, "NA") for k in self.__class__.headerrow()]
  

class StrictDataSet(DataSet):
    dc_header = {}
    def __init__(self, **kw):
        already_initialized = self.__class__.dc_header and True or False
        if not kw:
            raise Exception("empty!")
        for k, v in kw.items():
            if already_initialized and k not in self.__class__.dc_header:
                raise Exception("undefined key [%s]" % k)
            self[k] = v
    


class SmartDataRowMaker(object):
    """load up a data row in the form of a dict
    for each un-collapsable dict structure
    it will create a new class to handle it

    if you specify a transformer that effectively
    collapses a dict structure, it will merge them
    into an old dict class, if it exists

    if transformation is key --> None, ignore the key
    """
    def __init__(self, dctransform = None, collapse_rule = 'union'):
        """
        
        Arguments:
        - `dctransform`: dictionary key --> string or function mapping that transforms the key name into a different representation
        - `collapse_rule`: in final output, how to handle multiple sheets
           'union' (default) is to return a single sheet, where columns that don't exist in a sheet are filled with None
           'intersection' is to return a single sheet, where columns that don't exist in a sheet are dropped
           'separate' is to keep them as separate sheets and output separately
        """
        self._dctransform = {}
        if dctransform:
            for k0, k1 in dctransform.items():
                if type(k1) == str:
                    self._dctransform[k0] = (lambda transformed: lambda inkey, inval: (transformed, inval))(k1)
                # placeholder
                else:
                    self._dctransform[k0] = k1
        self._dcsheet = {'union': []}
        if collapse_rule != 'union':
            raise Exception("rule '' %s '' not yet implemented" % collapse_rule)
        self._collapse_rule = collapse_rule
        
    def addrow(self, dc):
        rowcopy = {}
        for key, val in dc.items():
            if key in self._dctransform:
                if self._dctransform[key] is None:
                    continue
                mkey, val = self._dctransform[key](key, val)
            else:
                mkey = key
            if type(val) == unicode:
                rowcopy[mkey] = val.encode("utf-8")
            else:
                rowcopy[mkey] = val
        tp_header = tuple(sorted(rowcopy.keys()))
        if tp_header not in self._dcsheet:
            self._dcsheet[tp_header] = []
        if self._collapse_rule == 'union':
            ds = DataSet(**rowcopy)
            self._dcsheet['union'].append(ds)

    def write_to_csv(self, csv_filepath):
        with open(csv_filepath, 'wb') as ofile:
            writer = csv.writer(ofile)
            if self._collapse_rule == 'union':
                writer.writerow(self._dcsheet[self._collapse_rule][0].__class__.headerrow())
                for ds in self._dcsheet[self._collapse_rule]:
                    writer.writerow(ds.datarow())
