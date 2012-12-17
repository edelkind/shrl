import re
import sys
import select

import cf


PARAMTYPE_GET  = 1
PARAMTYPE_POST = 2
def validate_paramtype(prmType):
    if prmType != PARAMTYPE_GET and prmType != PARAMTYPE_POST:
        raise ValueError("invalid value for prmType: [{0}] (see source)".format(prmType));


class HTTPRequest:

    def __init__(self):
        # defaults; names made to match other modules
        self.command = "GET"
        self.path    = "/"
        self.request_version = "HTTP/1.1"

        self.headers=[]
        self.headerMap={}
        self.cookies=[]
        self.cookieMap={}

        self.params = []
        self.paramMap = {}

        self.body=''
        self.raw_request=None
        self.postLen=0


    def addRequest(self, reqStr):
        """
        Add the request line (i.e. the POST/GET/whatever line).

        >>> req = HTTPRequest()
        >>> req.addRequest("GET /url HTTP/1.1")
        >>> req.path
        '/url'

        >>> req = HTTPRequest()
        >>> req.addRequest("GET /url?var=x HTTP/1.1")
        >>> req.path
        '/url'
        >>> req.paramMap['var']
        ['var', 'x', 1]
        """

        self.command, self.path, self.request_version = \
                reqStr.rstrip().split(' ')

        for host_pair in cf.HostReplace:
            self.path = self.path.replace(host_pair[0], host_pair[1])

        self._parse_params_get()


    def _parse_params_get(self):
        if '?' not in self.path:
            return

        base_path, get_params = self.path.split('?', 1)
        for param in get_params.split('&'):
            self.addParam(param, PARAMTYPE_GET)
        self.path = base_path


    def parseParamsPost(self, data):

        assert self.command == "POST", "parseParamsPost() called for non-POST request (" + self.command + ")"

        for param in data.split('&'):
            self.addParam(param.strip(), PARAMTYPE_POST)



    def parseHeaderByLine(self, headStr):
        """
        Use this function to parse headers.  Cookies will be parsed
        automatically.

        Returns True if we're still in headers
        Returns False if headers are now over (i.e. a lone newline was reached)

        >>> req = HTTPRequest()
        >>> req.parseHeaderByLine("Asdf: a header")
        True
        >>> req.parseHeaderByLine("Cookie: asdf=stuff")
        True
        >>> req.parseHeaderByLine("\\r\\n")
        False
        >>> req.cookieMap['asdf']
        ['asdf', 'stuff']
        """

        headStr = headStr.rstrip()
        if not len(headStr):
            self.collectCookies()
            return False

        self.addHeader(headStr)
        return True


    def addHeader(self, headStr):
        """
        Add a header to the header list, in HTTP format.  Please note that this
        does not populate the cookie list; you'll need to use collectCookies()
        to accomplish this, or just use parseHeaderByLine() instead of this
        function.

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

        self.addHeaderKV(key, val)

    def addHeaderKV(self, key, val):
        """
        Add a header to the header list, with an explicit key, val pair.
        """
        headerList = [key, val]

        self.headers.append(headerList)
        self.headerMap[key.lower()] = headerList

        if key.lower() == 'content-length':
            self.postLen = int(val)


    def collectCookies(self):
        """
        Call after headers are parsed to collect any cookies within the header
        into the cookie map.
        """
        if 'cookie' not in self.headerMap:
            return

        cklist = self.headerMap['cookie'][1].split(';')
        for ck in cklist:
            self.addCookie(ck)


    def addCookie(self, cookieStr):
        """
        Add one cookie to the cookie map, in name=val format.  Case is not
        modified in the original cookie, but in the cookieMap dict, it will be
        lowercase.

        >>> req = HTTPRequest()
        >>> req.addCookie(" asdf=a cookie")
        >>> req.cookieMap['asdf']
        ['asdf', 'a cookie']
        """
	try:
            key, val = cookieStr.split('=', 1)
        except:
            raise ValueError("malformed cookie line: "
                             "[{0}]".format(cookieStr))

        key = key.strip()
        val = val.strip()

        cookieList = [key, val]

        self.cookies.append(cookieList)
        self.cookieMap[key.lower()] = cookieList


    def addBody(self, s):
        self.body += s


    def buildPath(self):
        """
        Builds the path with GET parameters.

        >>> req = HTTPRequest()
        >>> req.path = "/url"
        >>> req.addParam("param1=value1", PARAMTYPE_GET)
        >>> req.addParam("param2=value2", PARAMTYPE_GET)
        >>> req.addParam("param3=value3", PARAMTYPE_POST)
        >>> req.buildPath()
        '/url?param1=value1&param2=value2'
        """
        url = self.path
        getParams = self.getParamSet(PARAMTYPE_GET)

        if len(getParams):
            url += '?' + '&'.join(getParams)

        return url


    def buildRequest(self):
        """
        >>> req = HTTPRequest()
        >>> req.addRequest("GET / HTTP/1.0")
        >>> req.buildRequest()
        'GET / HTTP/1.0\\r\\n'
        >>> req.request_version
        'HTTP/1.0'

        >>> req = HTTPRequest()
        >>> req.command = "POST"
        >>> req.path = "/stuff"
        >>> req.request_version = "HTTP/1.0"
        >>> req.buildRequest()
        'POST /stuff HTTP/1.0\\r\\n'
        >>> req.raw_request = "XCMD /nowhere XHTTP/9"
        >>> req.buildRequest()
        'XCMD /nowhere XHTTP/9\\r\\n'
        """

        if self.raw_request is not None:
            return self.raw_request + '\r\n'

        getpath = self.buildPath()
        return self.command + ' ' + getpath + ' ' + self.request_version + '\r\n'


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
            #hdrStrings.append('Cookie:')
            ckStrings = []

            for cook in self.cookies:
                ckStrings.append('='.join(cook))

            hdrStrings.append('Cookie: ' + '; '.join(ckStrings))

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

        bodyLenInt   = len(self.body)
        bodyLenStr   = str(bodyLenInt)
        self.postLen = bodyLenInt

        if 'content-length' in self.headerMap:
            self.headerMap['content-length'][1] = bodyLenStr
        else:
            self.addHeaderKV('Content-Length', bodyLenStr)


    def getHeader(self, varName):
        """
        Retrieve the contents of a header with name varName (case-insensitive).
        """

        return self.headerMap[varName.lower()][1]

    def getCookie(self, varName):
        """
        Retrieve the contents of a cookie with name varName (case-insensitive).
        """

        return self.cookieMap[varName.lower()][1]


    def addParam(self, prmStr, prmType):
        """
        Add one parameter to the parameter map, in name=val format.  prmType is
        either PARAMTYPE_GET or PARAMTYPE_POST, and works as one might expect.

        >>> req = HTTPRequest()
        >>> req.addParam("asdf=a param", PARAMTYPE_GET)
        >>> req.paramMap['asdf']
        ['asdf', 'a param', 1]
        """
	try:
            key, val = prmStr.split('=', 1)
        except:
            raise ValueError("malformed parameter line: "
                             "[{0}]".format(prmStr))

        key = key.strip()
        val = val.strip()

        validate_paramtype(prmType)

        paramList = [key, val, prmType]

        self.params.append(paramList)
        self.paramMap[key.lower()] = paramList


    def getParamSet(self, prmType):
        """
        Returns a list of parameters for the specified prmType, in key=val format.

        Note that this is not a free operation -- the list is generated
        dynamically.
        """

        validate_paramtype(prmType)

        paramSet = []
        url = self.path
        for prm in self.params:
            if prm[2] == prmType:
                paramSet.append(prm[0] + '=' + prm[1])

        return paramSet


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


