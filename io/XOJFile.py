import os, shutil, sys, time, re, gzip

class XOJFile(object):

    def __init__(self, xoj_filename, pdf_filename = None):
        self.pagecount = 0
        self.pdf_filename = pdf_filename
        self.xoj_filename = xoj_filename

    def doc_beg(self):
        self.ls_output = ["""<?xml version="1.0" standalone="no"?>
        <xournal version="0.4.5">
        <title>Xournal document - see http://math.mit.edu/~auroux/software/xournal/</title>"""]

    def doc_end(self):
        self.ls_output.extend(['</xournal>'])

    def page_beg(self):
        self.pagecount += 1
        self.ls_output.extend([
            '<page width="%s" height="%s">' % (width, height),
            (self.pagecount is 1 and self.pdf_filename is not None \
                 and '<background type="pdf" domain="absolute" filename="%s" pageno="%s" />' % (pdf_filename, self.pagecount)
                 or '<background type="pdf" pageno="%s" />' % (self.pagecount)),
            '<layer>'])

    def page_end(self):
        self.ls_output.extend(['</layer>', '</page>'])

    def __str__(self):
        return "\n".join(self.ls_output)

    def save(self):
        gz_xoj = gzip.open(self.xoj_filepath, 'wb')
        gz_xoj.write(str(self))
        gz_xoj.close()
