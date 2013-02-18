
# handler for Okular's annotation files
import os, sys
import subprocess

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
        sys.exit(okl_filepath)
    else:
        sys.exit()
