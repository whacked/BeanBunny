import os, sys
import zipfile

def statlog(s):
    print(" --   %s" % s)
    
class JAJFile:
    def __init__(self, jaj_filepath):
        if not zipfile.is_zipfile(jaj_filepath):
            raise Exception("I need a zipfile")
    
        self.filepath = jaj_filepath
        self.filename = os.path.split(jaj_filepath)[0]
        self.zf = zipfile.ZipFile(jaj_filepath, 'r')

        self.background_pdf_filename = None
        self.background_pdf_filepath = None
        self.dc_svg_annotation = {}
        self.ls_extract = []
        self.dir_tmp = None

        for info in self.zf.infolist():
            if info.filename.startswith("background") and info.filename.endswith(".pdf"):
                self.background_pdf_filename = info.filename
                self.ls_extract.append(info.filename)
            # jarnal annotations have format "p%d.svg" and start from 0
            if info.filename.startswith('p') and info.filename.endswith('.svg'):
                svg_page_num = int(os.path.splitext(info.filename[1:])[0])
                # cache the svgs in the annotation directory
                self.dc_svg_annotation[svg_page_num] = info.filename
                self.ls_extract.append(info.filename)
        
        if self.background_pdf_filename is None:
            raise Exception("did not did not find any pdfs in the jaj")
        
    def extract_to_directory(self, output_directory):
        if not os.path.exists(output_directory):
            os.mkdir(output_directory)
        self.dir_tmp = output_directory
        for filename in self.ls_extract:
            extract_path = os.path.join(output_directory, filename)
            open(extract_path, 'wb').write(self.zf.read(filename))
            #statlog('extracted %s' % filename)

        self.background_pdf_filepath = os.path.join(output_directory, self.background_pdf_filename)
        
    def cleanup(self):
        if not self.dir_tmp: return
        for filename in self.ls_extract:
            print "~ jaj", filename
            os.unlink(os.path.join(self.dir_tmp, filename))
        os.rmdir(self.dir_tmp)
        
    # old stuff from another class that did something similar, possibly
    # redundant. shoehorned to fit here, may not work
    def deflate(self):
        if not self.dir_tmp:
            self.dir_tmp = "%s.dir" % self.filename
        CWD = os.getcwd()
        os.mkdir(self.dir_tmp)
        os.chdir(self.dir_tmp)
        
        # extract into dir_tmp
        for info in self.zf.infolist():
            with open(info.filename, "w") as ofile:
                ofile.write(self.zf.read(info.filename))

        os.chdir(CWD)
    
    def inflate(self, remove_temp = True):
        if not self.dir_tmp:
            self.deflate()

        CWD = os.getcwd()
        os.chdir(self.dir_tmp)

        ls_archive_file = os.listdir('.')
        print("creating archive...")
        zofile = zipfile.ZipFile(self.filename, mode='w')
        try:
            for filename in ls_archive_file:
                zofile.write(filename)
        finally:
            print("archive successfully created")
            zofile.close()

        os.chdir(CWD)
        
        if remove_temp:
            os.rename(os.path.join(self.dir_tmp, self.filename), os.path.join(CWD, self.filename))
            shutil.rmtree(self.dir_tmp)
            self.dir_tmp = None
            

