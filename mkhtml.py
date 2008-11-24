#!/usr/bin/python
"""Turn Markdown documents into HTML documents.

Depends on python-markdown and Beautiful Soup.

Markdown normally generates HTML document content; this generates HTML
documents instead.

"""
import markdown, BeautifulSoup, sys, os.path

def render(text):
    "Given Markdown input as a string, produce an HTML document as a string."
    body = str(markdown.Markdown(text))
    soup = BeautifulSoup.BeautifulSoup(body)

    headers = soup('h1')
    if len(headers) > 0:
        title = headers[0].renderContents()
    else:
        title = 'Lame document with no top-level header'

    return '''<html><head><title>%s</title>
    <meta http-equiv="content-type" content="text/html; charset=utf-8" />
    </head>
    <body>%s</body></html>''' % (title, body)

def process(infile):
    "Given a filename of Markdown input, create an HTML file as output."
    outfile = infile + '.html'

    if os.path.exists(outfile) and \
           os.stat(outfile).st_mtime > os.stat(infile).st_mtime:
        print "`%s` is newer than `%s`, skipping  " % (outfile, infile)
        return

    outfiletmp = outfile + '.tmp'
    fo = file(outfiletmp, 'w')
    fo.write(render(file(infile).read()))
    fo.close()

    os.rename(outfiletmp, outfile)  # atomic replace; won't work on Win32
    print "rendered `%s` to `%s`  " % (infile, outfile)

def main(args):
    filenames = args[1:]
    if filenames:
        for filename in filenames: process(filename)
        return 0
    else:
        print ("usage: `%s foo bar baz`; implicitly writes to `foo.html`, etc."
               % args[0])
        return 1

if __name__ == '__main__':
    sys.exit(main(sys.argv))
