import os, shutil, sys, time, re, gzip

class XOJFile(object):

    def __init__(self, xoj_filepath, pdf_filepath = None, width = None, height = None):
        self.pagecount = 0
        self.pdf_filepath = pdf_filepath
        self.xoj_filepath = xoj_filepath
        self.width = width
        self.height = height

    def doc_beg(self):
        self.ls_output = ["""<?xml version="1.0" standalone="no"?>
        <xournal version="0.4.5">
        <title>Xournal document - see http://math.mit.edu/~auroux/software/xournal/</title>"""]

    def doc_end(self):
        self.ls_output.extend(['</xournal>'])

    def page_beg(self):
        self.pagecount += 1
        self.ls_output.extend([
            '<page width="%s" height="%s">' % (self.width, self.height),
            (self.pagecount == 1 and self.pdf_filepath is not None \
                 and '<background type="pdf" domain="absolute" filename="%s" pageno="%s" />' % (self.pdf_filepath, self.pagecount)
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
