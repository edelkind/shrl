import re
import sys
import select

import cf


class HTTPRequest:
    def __init__(self):
        self.headers=[]
        self.headerMap={}
        self.cookies=[]
        self.cookieMap={}
        self.body=''
        self.request=''
        self.postLen=0

    def addRequest(self, reqStr):
        for host_pair in cf.HostReplace:
            reqStr = reqStr.replace(host_pair[0], host_pair[1])

        self.request = reqStr

    def addHeader(self, headStr):
        """
        >>> req = HTTPRequest()
        >>> req.addHeader("Asdf: a header")
        >>> req.addHeader(" etc")
        >>> req.headerMap['asdf']
        ['Asdf', 'a header etc']
        """

        # if the header line begins with whitespace, add the data to the last
        # header value seen
        if re.match('\s', headStr):
            if not len(self.headers):
                raise ValueError("malformed header line: "
                                 "[{0}]".format(headStr))

            self.headers[-1][1] += ' ' + headStr.strip()
            return

        if 'cookie' in self.headerMap:
            self.addCookie(headStr)
            return

        try:
            key, val = headStr.split(':', 1)
        except:
            raise ValueError("malformed header line: "
                             "[{0}]".format(headStr))


        key = key.strip()
        val = val.strip()

        if key.lower() == "host":
            for host_pair in cf.HostReplace:
                val = val.replace(host_pair[0], host_pair[1])

        headerList = [key, val]

        self.headers.append(headerList)
        self.headerMap[key.lower()] = headerList

        if key.lower() == 'content-length':
            self.postLen = int(val)

    def addCookie(self, cookieStr):
        """
        >>> req = HTTPRequest()
        >>> req.addCookie("asdf=a cookie")
        >>> req.cookieMap['asdf']
        ['asdf', 'a cookie']
        """
	try:
            key, val = cookieStr.split('=', 1)
        except:
            raise ValueError("malformed cookie line: "
                             "[{0}]".format(headStr))

        key = key.strip()
        val = val.strip()

        cookieList = [key, val]

        self.cookies.append(cookieList)
        self.cookieMap[key.lower()] = cookieList


    def addBody(self, s):
        self.body += s


    def buildRequest(self):
        """
        >>> req = HTTPRequest()
        >>> req.addRequest("GET / HTTP/1.0")
        >>> req.buildRequest()
        'GET / HTTP/1.0\\r\\n'
        """

        return self.request + '\r\n'


    def buildHeaders(self, updateLength=False):
        """
        >>> req = HTTPRequest()
        >>> req.addHeader("abc: a header")
        >>> req.addHeader("def: z header")
        >>> req.buildHeaders()
        'abc: a header\\r\\ndef: z header\\r\\n'
        """

        if not self.headers:
            return ''

        if updateLength:
            self.adjustLength()

        hdrStrings = []
        for hdr in self.headers:
            if hdr[0].lower() == 'cookie':
                continue
            hdrStrings.append(': '.join(hdr))

        if self.cookies:
            hdrStrings.append('Cookie:')

            for cook in self.cookies:
                hdrStrings.append('='.join(cook))

        hdrStrings.append('')
        return '\r\n'.join(hdrStrings)


    def buildBody(self):
        """
        >>> req = HTTPRequest()
        >>> req.addBody('asdf\\n')
        >>> req.addBody('abooga')
        >>> req.buildBody()
        'asdf\\nabooga'
        """

        return self.body


    def adjustLength(self):
        """
        >>> req = HTTPRequest()
        >>> req.addHeader("Content-Length: 0")
        >>> req.addBody('abooga')
        >>> req.adjustLength()
        >>> req.buildHeaders()
        'Content-Length: 6\\r\\n'
        """

        self.postLen = len(self.body)

        if 'content-length' in self.headerMap:
            self.headerMap['content-length'][1] = str(self.postLen)


def makeFileIfNecessary(conn):
    """return a file object associated with conn.

    if it's already a file, just return it.

    >>> makeFileIfNecessary(sys.stdin) is sys.stdin
    True
    >>> import socket
    >>> s = socket.socket()
    >>> makeFileIfNecessary(s) is s
    False
    """

    if 'readline' in dir(conn):
        return conn
    else:
        return conn.makefile()


def readerWriter(me):
    req = HTTPRequest()

    lfile = makeFileIfNecessary(me.lconn)
    rfile = makeFileIfNecessary(me.rconn)

    #rfile.write("GET / HTTP/1.0\r\n\r\n")
    #while True:
    #    dat = rfile.read()
    #    if not dat: return
    #    lfile.write(dat)

    empty=0
    while True:
        ln = lfile.readline().rstrip()
        if not len(ln):
            if req.request:
                break
            else:
                # wtf? bug with a silverlight app?
                empty += 1
                if empty > 4:
                    raise IOError("Empty lines without request")

                #print >>sys.stderr, "hmm... empty line without request."
                continue

        if not req.request:
            req.addRequest(ln)
            #if ln.find(".xap ") > 0:
            #    cf.CERT_FILE = "cert.pem.2"
            #    print "reset cert file after request for", ln
            continue

        try:
            req.addHeader(ln)
        except Exception:
            print >>sys.stderr, "addHeader:", sys.exc_info()[1]



    #print "finished reading headers"

    if req.postLen:
        print "reading postLen of " + str(req.postLen)
        req.addBody(lfile.read(req.postLen))


    for dat in (
            req.buildRequest(),
            req.buildHeaders(),
            '\r\n',
            req.buildBody() ):
        if dat:
            rfile.write(dat)
            if me.logfile:
                me.logfile.write(dat)

    #rfile.write(req.buildRequest())
    #rfile.write(req.buildHeaders())
    #rfile.write('\r\n')
    #rfile.write(req.buildBody())

    if me.logfile:
        me.logfile.write('\n' + cf.RW_SEPARATOR + '\n')
        me.logfile.flush()
    rfile.flush()


    remainder = 0
    while True:
        if not select.select([rfile], [], [], cf.TIMEOUT_SECS)[0]:
            raise IOError(
                    "Timeout after {0!s} seconds".format(cf.TIMEOUT_SECS))

        while True:
            ln = rfile.readline()
            if ln.lower().startswith("content-length:"):
                clen = ln.split(":", 1)[1].strip()
                try:
                    remainder = int(clen)

                except:
                    print >>sys.stderr, "Content-Length error:", clen

            if me.logfile:
                me.logfile.write(ln)
                me.logfile.flush()

            lfile.write(ln)
            lfile.flush()

            if len(ln) < 3 and len(ln.strip()) == 0:
                break

        while remainder > 0:
            dat = rfile.read(remainder)
            if not len(dat):
                break
            remainder -= len(dat)

            if me.logfile:
                me.logfile.write(dat)
                me.logfile.flush()

            lfile.write(dat)
            lfile.flush()

        if remainder:
            raise IOError("Remote connection closed unexpectedly")

        if select.select([rfile], [], [], 0)[0]:
            # either the connection closed or it's a protocol error, so...
            return False
        return True


