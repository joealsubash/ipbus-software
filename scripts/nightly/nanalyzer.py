#!/usr/bin/python
"""
Usage: nanalyzer.py [options] configuration.py
Executes the nightly analyzer with the givn configuration file.

arguments:
   configuration.py  Python configuration file 
   
options:
   -h, --help        help
"""
import getopt
import sys
import re
import time
import os
import smtplib
import platform
from socket import getfqdn
from email.MIMEText import MIMEText
import urllib
LIMIT, ERROR, TEST_PASSED = range(3)

def style(type):
    if type == LIMIT:
        return "display:inline;font-weight:bold;"
    elif type == ERROR:
        return "display:inline;color:red;"
    elif type == TEST_PASSED:
        return "display:inline;color:green;"
    else:
        return "display:inline;"

def findany(str,patterns):
    for i in patterns:
        if str.find(i)!=-1:
            return True

    return False

def analyze_log():
    result = []

    r_limit = re.compile(r'----\+\+\+\+(.*?)\+\+\+\+----')

    fn = CONF.NIGHTL_LOG_FILE
    current_section = "BEGIN"
    for (i, l) in enumerate(open(fn)):
        if r_limit.search(l):
            s = r_limit.search(l)
            current_section = s.groups()[0]
            result.append((i, LIMIT, l, current_section))
        elif findany(l, CONF.TEST_PASSED_LIST):
            result.append((i, TEST_PASSED, l, current_section))
        elif findany(l, CONF.ERROR_LIST):
            if findany(l, CONF.IGNORE_ERROR_LIST):
                pass
            else:
                result.append((i, ERROR, l, current_section))

    return result

def report_summary(result):
    html ="<h3>Summary</h3>\n"

    html += "<table border=1>\n"
    for (c, mytype, detail, section) in result:
        if mytype == LIMIT:
            errors = sum([1 for (i, t, d, s) in result if t == ERROR and s == section])
            ok = sum([1 for (i, t, d, s) in result if t == TEST_PASSED and s == section])
            bookmark = "incidence_" + urllib.quote(section)
            html += "<tr>\n"
            html += "<td><a href='#" + bookmark + "'>" + section + "</a></td>"
            html += "<td>"
            if errors:
                html += "<a style='text-decoration: none' href='#" + bookmark + "'>"
                html += "<pre style='" + style(ERROR) + "'> " + str(errors) + " ERRORS </pre>"
                html += "</a>"
            else:
                html += "<pre style='" + style(TEST_PASSED) + "'> NO ERRORS </pre>"
            html += "</td>"
            html += "<td>"
            if ok:
                html += "<a style='text-decoration: none' href='#" + bookmark + "'>"
                html += "<pre style='" + style(TEST_PASSED) + "'> " + str(ok) + " OK </pre>"
                html += "</a>"
            html += "</td>"
            html += "</tr>"

    html += "</table><br/>\n"

    html += "see <a href='%s'>RPMs...</a><br/>" % os.path.join(CONF.WEB_URL,"RPMS")
    html += "see <a href='%s'>log file...</a><br/>" % os.path.join(CONF.WEB_URL,"nightly.log.html")
    html += "see <a href='%s'>other logs...</a><br/>" % os.path.join(CONF.WEB_URL,"logs")

    return html

def report_links(result):
    html ="<h3>Incidence Summary</h3>\n"

    sections = [section for (c, mytype, detail, section) in result if mytype==LIMIT]
    for s in sections:
        incidences = [(c, t, d, section) for (c, t, d, section) in result if section==s]
        incidences.sort()
        for (c, t, d, section) in incidences:
            bookmark = "incidence_" + urllib.quote(s)
            if t == LIMIT:
                html += "<a name='" + bookmark + "'><h5>" + s + "</h5></a>"
            elif t == TEST_PASSED:
                pass
            else:
                html += "<a style='text-decoration: none' href='%s'>" % os.path.join(CONF.WEB_URL, "nightly.log.html#log_" + str(c))
                html += "<pre style='" + style(t) + "'> " + d + "</pre>"
                html += "</a>"

    return html

def render_log(result):
    
    html = html_header("CACTUS Nightlies: Log details")
    
    html += "<a href='%s'>back...</a><br/><br/>" % os.path.join(CONF.WEB_URL,"index.html")

    fn = CONF.NIGHTLY_LOG_FILE
    keys = [i[0] for i in result]
    types = [i[1] for i in result]
    for (i, l) in enumerate(open(fn)):
        mytype = ""
        if i in keys:
            mytype = types[keys.index(i)]
            html += "<a name='log_" + str(i) + "'></a>"

        html += "<pre style='" + style(mytype) + "'>" + l + "</pre>\n"
        
    html += html_footer()
        
    fn = os.path.join(CONF.NIGHTLY_LOG_DIR, "nightly.log.html")
    tmp = open(fn, "w")
    tmp.write(html)
    tmp.close()

def html_header(title):
    html = """
    <?xml version="1.0" encoding="utf-8"?>
    <!DOCTYPE html
    PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml" lang="en-US.UTF-8" xml:lang="en-US.UTF-8">
    <head>
    <title>
    """

    html += title

    html += """
    </title>
    </head>
    <body>
    """
    html += "<a href='https://twiki.cern.ch/twiki/bin/view/CMS/TrgSupDevGuide1dot11#10_Nightly_Builds'><img src='static/question_mark.png' height='60' width='60' style='border-style: none' align='right'/></a>"
    html += "<h2>" + title + "</h2>\n"
    
    html += "<p><b>Date:</b> %s</p>" % time.asctime()
    html += "<p><b>Platform:</b> %s</p>" % platform.platform()
    html += "<p><b>Node:</b> %s</p>" % getfqdn()

    return html

def html_footer():
    html = """<center>
    <span>
    <a href=\"https://svnweb.cern.ch/trac/cactus/newticket\">Contact us</a> 
    </span>
    </center>
    """
    html += """
    </body>
    </html>
    """
    return html

def render_main(result):
    html = html_header(CONF.TITLE)
    html += report_summary(result)
    html += report_links(result)
    html += html_footer()

    fn = os.path.join(CONF.NIGHTLY_BASE,"index.html")
    open(fn,"w").write(html)

def send_mail():
    fn = os.path.join(CONF.NIGHTLY_BASE,"index.html")
    content = open(fn).read()

    msg = MIMEText(content,'html')

    if re.search("\d+\s+ERRORS",content):
        msg['Subject'] = "ERROR: " + CONF.TITLE 
    else:
        msg['Subject'] = CONF.TITLE

    fromaddr = CONF.FROM_EMAIL
    msg['From'] = fromaddr
    toaddr = CONF.TO_EMAIL
    msg['To'] = toaddr

    s = smtplib.SMTP('localhost')
    s.sendmail( fromaddr, [toaddr], msg.as_string())
    s.quit()


def report(conf):
    global CONF
    CONF = conf
    
    result = analyze_log()

    render_log(result)
    render_main(result)

    send_mail()

if __name__ == '__main__':
    try:
        opts, args = getopt.getopt(sys.argv[1:], "h", ["help"])
    except getopt.GetoptError, err:
        print __doc__
        sys.exit(2)

    silent = False
    keep = False
    for o, a in opts:
        if o in ("-h", "--help"):
            print __doc__
            sys.exit(0)
                

    if len(args) == 1:
        global CONF
        try:
            p,fn = os.path.split(args[0])
            n,ext = os.path.splitext(fn)
            CONF = __import__(n)
        except ImportError,e:
            sys.stderr.write("ERROR: Failed to import '%s': %s\n\n" % (args[0],str(e)))
    else:
        sys.stderr.write("ERROR: Wrong number of arguments\n\n")
        print __doc__
        sys.exit(2)
        
    report(CONF)
