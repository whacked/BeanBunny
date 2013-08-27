
# handler for Okular's annotation files
import os, sys
import subprocess
from BeautifulSoup import BeautifulStoneSoup

class OkularAnnotation:
    # this from long ago. if you play with this, don't expect to look the same
    # on your next pull

    processor_template = "process_annotation_%s"
    dc_type_lookup     = {
        1: 'TEXT_NOTE', 
        2: 'STRAIGHT_LINE', # yellow or bluegreen
        3: 'SHAPE_STAMP', 
        4: 'TEXT_HIGHLIGHTER', # yellow or black
        5: 'IMAGE_STAMP', 
        6: 'FREEHAND_LINE', # green
        }

    DOC_WIDTH  = 595
    DOC_HEIGHT = 793

    def __repr__(self):
        dc = dict(
                stype = self.type,
                )
        return "<%(stype)s>" % dc
    
    def __init__(self, annotation):
        self.annotation = annotation
        self.type = OkularAnnotation.dc_type_lookup.get(int(self.annotation.get('type')))
        self.line_color = self.annotation.base.get("color")

    def path_string(self, x, y):
        return "%s %s" % (x * self.DOC_WIDTH, y * self.DOC_HEIGHT)

    def boundary2xywh(self, boundary):
        return [((L    ) * OkularAnnotation.DOC_WIDTH,
                 (T    ) * OkularAnnotation.DOC_HEIGHT,
                 (R - L) * OkularAnnotation.DOC_WIDTH,
                 (B - T) * OkularAnnotation.DOC_HEIGHT) for L, T, R, B in [ tuple([float(self.annotation.boundary.get(pt)) for pt in ('l', 't', 'r', 'b')]) ] ][0]

    def process(self):
        fn_processor_name = self.processor_template % self.type
        if hasattr(self, fn_processor_name):
            return getattr(self, fn_processor_name)()
        else:
            print "UNSUPPORTED TYPE:", self.type
            return None

    def process_annotation_FREEHAND_LINE(self): # green
        ls_point = []
        line_width = self.annotation.base.penstyle.get("width")
        for point in self.annotation.path.findChildren("point"):
            x, y = float(point.get('x')), float(point.get('y'))
            ls_point.append(self.path_string(x, y))
        return """<path d="M%s" stroke="%s" stroke-width="%s" fill="none"/>""" % (" L".join(ls_point), self.line_color, line_width)
        
    def process_annotation_TEXT_HIGHLIGHTER(self): # yellow or black
        x, y, w, h = self.boundary2xywh(self.annotation.boundary)
        
        if self.annotation.hl.get("type") == '2':
            style = """fill="none" stroke-width="1" stroke="%s" """ % (self.line_color)
        else:
            style = """style="fill:%s;fill-opacity:0.3" """ % (self.line_color)
        return """<rect x="%s" y="%s" width="%s" height="%s" %s/>""" % (x, y, w, h, style)
        
    def process_annotation_STRAIGHT_LINE(self): # yellow or bluegreen
        ls_point = []
        line_width = 1
        for point in self.annotation.line.findChildren("point"):
            x, y = float(point.get('x')), float(point.get('y'))
            ls_point.append(self.path_string(x, y))
        if self.annotation.line.get("closed"):
            ls_point.append(ls_point[0])

        return """<path d="M%s" stroke="%s" stroke-width="%s" fill="none"/>""" % (" L".join(ls_point), self.line_color, line_width)
        
    def process_annotation_IMAGE_STAMP(self): # 5
        x, y, w, h = self.boundary2xywh(self.annotation.boundary)
        return """<rect x="%s" y="%s" width="%s" height="%s" style="stroke:#ff6666;stroke-width:2;fill:#ffcccc;fill-opacity:0.3"/>""" % (x, y, w, h,)
    def process_annotation_SHAPE_STAMP(self): # 3
        x, y, w, h = self.boundary2xywh(self.annotation.boundary)
        rx, ry = w/2     , h/2
        cx, cy = (x + rx), (y + ry)
        line_width = 5
        return """<ellipse cx="%s" cy="%s" rx="%s" ry="%s" style="fill:none;stroke:%s;stroke-width:%s"/>""" % (cx, cy, rx, ry, self.line_color, line_width)
    def process_annotation_TEXT_NOTE(self): # 1
        x, y, w, h = self.boundary2xywh(self.annotation.boundary)
        font_size = 12
        if self.annotation.text.get("type") == '1': # inline text box
            text = self.annotation.text.escapedtext.contents[0]
            return """<rect x="%s" y="%s" width="%s" height="%s" style="stroke:#000000;stroke-width:1;fill:#ffff00;fill-opacity:0.3"/>""" % (x, y, w, h,) + \
                """<text x="%s" y="%s" font-size="%s">%s</text>""" % (x, y + font_size, font_size, text)
        else: # text icon with text
            text = self.annotation.base.get("contents")
            ls_rtn = []
            line_num = 0
            for line in textwrap.wrap(text, 20):
                line_num += 1
                ls_rtn.append("""<text x="%s" y="%s" font-size="%s">%s</text>""" % (x, y + font_size * line_num, font_size, line))
            return """<rect x="%s" y="%s" width="%s" height="%s" style="stroke:#000000;stroke-width:1;fill:#00ffff;fill-opacity:0.3"/>\n""" % (x, y, w, h,) + \
                "\n".join(ls_rtn)
                
        
def process_okular_xml(xml_path):

    xml = open(xml_path).read()
    soup = BeautifulStoneSoup(xml)
    ls_ano = []
    for page in soup.findChildren("page"):
        ls_annotation = page.findChildren("annotation")
    
        if not ls_annotation:
            print "no annotations found"
            return
    
        for ano in ls_annotation:
            OKA = OkularAnnotation(ano)
            ls_xml.append(OKA.process())
            ls_ano.append(OKA)
    return ls_ano
    

def write_okular_annotation(source_pdf, okular_xml, output_dir):
    print "#" * 80
    print "OUTPUTTING TO: %s" % output_dir
    print "#" * 80

    pdfr = pyPdf.PdfFileReader(open(source_pdf, "rb"))
    _xzero, _yzero, DOC_WIDTH, DOC_HEIGHT = pdfr.getPage(0)['/MediaBox']
    pdfr.stream.close() # duno if this frees anything at all

    DIR_ANNOTATION = '.'

    FILE_OUTPUT_TEMPLATE = "p%s.svg"

    dc_page_annotation = {}
    soup = BeautifulStoneSoup(okular_xml)
    for page in soup.findChildren("page"):
        page_num = int(page.get("number"))
        
        ls_annotation = page.findChildren("annotation")
    
        if not ls_annotation:
            print "no annotations found"
            return
    
        ls_xml = []
        for ano in ls_annotation:
            OKA = OkularAnnotation(ano)
            ls_xml.append(OKA.process())
    
        svg_out = wrap_into_svg(DOC_WIDTH, DOC_HEIGHT, "\n".join(ls_xml))

        open(FILE_OUTPUT_TEMPLATE % page_num, "w").write(svg_out)
        dc_page_annotation[page_num] = FILE_OUTPUT_TEMPLATE % page_num

        #print svg_out
        #print "\n------\n\n"
    
    PDFAP = PDFAnnotationProcessor.PDFAnnotationProcessor( \
        source_pdf,
        DIR_ANNOTATION,
        dc_page_annotation)
    PDFAP.extract_all_annotation(output_dir)

    


if __name__ == "__main__":
    proc = subprocess.Popen(['kde4-config', '--localprefix'], stdout = subprocess.PIPE)
    out, err = proc.communicate()

    OKULAR_ANNOTATION_PATH = os.path.join(out.strip(), 'share', 'apps', 'okular', 'docdata')

    try:
        pdf_filepath = sys.argv[1]
    except IndexError, e:
        sys.exit("need filepath")

    pdf_filename = os.path.split(pdf_filepath)[-1]

    if not os.path.exists(pdf_filepath):
        sys.exit()

    pdf_filesize = os.path.getsize(pdf_filepath)
    #print "filesize of %s is %s" % (pdf_filepath, pdf_filesize)
    
    okl_filepath = os.path.join(OKULAR_ANNOTATION_PATH, "%d.%s.xml" % (pdf_filesize, pdf_filename))
    #print "filepath of okular xml: %s" % (okl_filepath)

    if os.path.exists(okl_filepath):
        # print "filesize of %s is %s\n\n" % (okl_filepath, os.path.getsize(okl_filepath))
        process_okular_xml(okl_filepath)
        sys.exit(okl_filepath)
    else:
        sys.exit()
