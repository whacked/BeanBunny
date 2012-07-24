import sys, os, random
from xml import sax

# TODO: x, y offset in iliad - jarnal conversion


"""
a motley collection of classes to handle iRex Iliad (ili?) files

called from the command line, it will attempt to convert the iliad file to an svg

"""


height = 792 # height of the pdf?
width  = 612
filename = ""

class IliadPage:
    def __init__(self, pagenum):
        self.id = int(pagenum) - 1
        self.orientation = 0
        self.height = 0
        self.width = 0
        self.backgroundcolor = None # ignore for now
        self.ls_stroke = []

class IliadStroke:
    def __init__(self, color, layer, penSize, lineStyle, zoom):
        self.color = color
        self.layer = int(layer)
        self.penSize = int(penSize)
        self.lineStyle = "solid"
        self.zoom = float(zoom)
        self.xml = ""

    def set_stroke(self, str_data):
        ls_data = []
        for line in str_data.strip().split("\n"):
            x, y, SOMETHING = line.split()
            ls_data.append("%s %s" % (x, y))

        # notice the initial MOVE-TO command "M" is in the """ string
        # apart from the " L" join command that impolodes with LINE-TO ("L")
        self.xml = """<path d="M%s" stroke="%s" stroke-width="%s" fill="none" stroke-opacity="%s" />""" % (" L".join(ls_data), self.color, self.penSize, 1)

class IliadScribbleHandler(sax.ContentHandler):
    def __init__(self):
        self.ls_page = []
        self.cur_page = None
        self.cur_stroke = None

        self.buffer = ""

    def startElement(self, tag, attrs):
        if tag == "page":
            print("START PAGE\n\n\n\n\n\n\n")
            self.cur_page = IliadPage(attrs.getValue("id"))
        elif tag == "stroke":
            self.cur_stroke = IliadStroke(attrs.getValue("color"),
                                          attrs.getValue("layer"),
                                          attrs.getValue("penSize"),
                                          attrs.getValue("linestyle"),
                                          attrs.getValue("zoom"),
                                          )
            
    def characters(self, ch):
        self.buffer += ch

    def endElement(self, tag):
        if tag == "page":
            print("END PAGE")
            self.ls_page.append(self.cur_page)
            self.cur_page = None

        elif tag == "orientation":
            self.cur_page.orientation = int(self.buffer)
            print("setting orientation to %s" % self.cur_page.orientation)
        elif tag == "height":
            self.cur_page.height = int(self.buffer)
            print("setting height to %s" % self.cur_page.height)
        elif tag == "width":
            self.cur_page.width = int(self.buffer)
            print("setting width to %s" % self.cur_page.width)
        elif tag == "stroke":
            self.cur_stroke.set_stroke(self.buffer)
            self.cur_page.ls_stroke.append(self.cur_stroke)
            self.cur_stroke = None

        self.buffer = ""


def render_page(page):
    global background_id, filename
    return """<?xml version="1.0" standalone="no"?>
<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 20010904//EN" "http://www.w3.org/TR/2001/REC-SVG-20010904/DTD/svg10.dtd">
<svg width="%spx" height="%spx" xmlns="http://www.w3.org/2000/svg">
<title>Jarnal document - see http://www.dklevine/general/software/tc1000/jarnal.htm for details</title>
<desc>
[Jarnal Page Parameters]
paper=Lined
lines=25
height=%s
width=%s
bg=1
transparency=255
bcolor=-1
bgtext=false
bgfade=0
bgrotate=0
bgscale=1.0
bgid=background%s.%s
bgindex=0
pageref=%s
</desc>

%s

</svg>
""" % (page.width, page.height, page.height, page.width, background_id, filename, make_pageref(), "\n".join([stroke.xml for stroke in page.ls_stroke]))
        


def make_rand():
    return int(random.random() * 10 ** 8)

def make_pageref():
    return "pageref%s" % make_rand()

background_id = "background%s" % make_rand()




if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("insufficient parameters")
        sys.exit()
    filename = sys.argv[1]
    
    parser = sax.make_parser()
    handler = IliadScribbleHandler()
    parser.setContentHandler(handler)
    parser.parse(open("scribble.irx"))
    
    #import time
    for page in handler.ls_page:
        xml_page = render_page(page)
        ofile = open("p%s.svg" % page.id, "w")
        ofile.write(xml_page)
        ofile.close()
#        print(xml_page)
        print("rendered page %s" % page.id)
    
    #    time.sleep(0.5)

