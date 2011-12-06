
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
    
