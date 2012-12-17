#!/usr/bin/env python

import sys
import argparse

from connmojo import HTTPRequest, PARAMTYPE_GET, PARAMTYPE_POST
import cf

#def addDict(target, data):
#    k,v = data.split('=', 1)
#    target[k] = v

parser = argparse.ArgumentParser(
        description="process HTTP requests to/from line-based requests for shell script interaction")

parser.add_argument('-d', action="store_true", help='decode from line-based input and output HTTP')


class HTTPLineProto:

    def __init__(self, request_io=None, decode=False):
        self.req = HTTPRequest()

        self.rfile = request_io
        #self.error_code = self.error_message = None

        if request_io:
            if decode:
                self.parse_byLine(request_io)
            else:
                self.parse_http(request_io)


    #def parse_input(istream):
    def parse_http(self, istream):
        """
        Parse a stream for http headers
        """

        self.req.addRequest(istream.readline().rstrip())
        while self.req.parseHeaderByLine(istream.readline()):
            pass

        if self.req.command == "POST" and 'content-length' in self.req.headerMap:
            data = istream.read(int(self.req.getHeader('content-length')))
            self.req.parseParamsPost(data)


        #self.parse_params_get()
        #self.parse_params_post()

    #def send_error(self, code, message):
    #    self.error_code = code
    #    self.error_message = message

    #def parse_http(self):
    #    self.raw_requestline = self.rfile.readline()
    #    self.parse_request()

    def parse_byLine(self, istream):

        lineno=0
        for line in istream:
            lineno+=1
            try:
                tag,data = line.strip().split(':',1)
            except ValueError:
                print >>sys.stderr, "ERROR parsing line {0}: {1}".format(lineno, line.strip())
                sys.exit(1)
            if tag == "CMD":
                self.req.command = data
            if tag == "HTTPVER":
                self.req.request_version = data
            elif tag == "PATH":
                self.req.path = data
            elif tag == "HOST":
                self.req.addHeaderKV('Host', data)
            elif tag == "HEAD":
                kv = data.split('=')
                self.req.addHeaderKV(kv[0], kv[1])
            elif tag == "G_PARAM":
                self.req.addParam(data, PARAMTYPE_GET)
            elif tag == 'P_PARAM':
                self.req.addParam(data, PARAMTYPE_POST)
            elif tag == 'COOKIE':
                self.req.addCookie(data)



#    def parse_params_get(self):
#        self.params_get = {}
#
#        base_path, get_params = self.path.split('?', 1)
#        if get_params:
#            for param in get_params.split('&'):
#                addDict(self.params_get, param)
#                self.params_get.append(param.strip())
#
#        self.path = base_path


#    def parse_params_post(self):
#        self.params_post = []
#
#        if 'content-length' in self.req.headerMap and self.req.command == "POST":
#
#            data = self.rfile.read(int(self.req.getHeader('content-length')))
#            for param in data.split('&'):
#                self.params_post.append(param.strip())


    def byLine(self, dest):
	print >>dest, "CMD:" + self.req.command
	print >>dest, "PATH:" + self.req.path
        try:
            print >>dest, "HOST:" + self.req.getHeader('host')
        except KeyError:
            pass

	for varPair in self.req.headers:
            varName = varPair[0]
            varNameLow = varPair[0].lower()
            varVal  = varPair[1]

            if cf.HEADERS_LOWERCASE:
                varName = varNameLow

            if  varNameLow == 'cookie' or \
                varNameLow == 'host':
                    continue
            print >>dest, "HEAD:" + varName + '=' + varVal

        for varPair in self.req.cookies:
            varName = varPair[0]
            varNameLow = varPair[0].lower()
            varVal  = varPair[1]

            print >>dest, "COOKIE:" + varName + '=' + varVal

        for param in self.req.getParamSet(PARAMTYPE_GET):
            print >>dest, "G_PARAM:" + param

        for param in self.req.getParamSet(PARAMTYPE_POST):
            print >>dest, "P_PARAM:" + param

    def byHTTP(self, dest):
        postSet = self.req.getParamSet(PARAMTYPE_POST)
        if postSet:
            self.req.addBody('&'.join(postSet))

        dest.write(self.req.buildRequest())
        dest.write(self.req.buildHeaders(updateLength=True))
        dest.write('\r\n')
        dest.write(self.req.buildBody())
        dest.flush()


if __name__ == "__main__":
    args = parser.parse_args()

    if args.d:
        req = HTTPLineProto(sys.stdin, decode=True)
        req.byHTTP(sys.stdout)
    else:
        req = HTTPLineProto(sys.stdin)
        req.byLine(sys.stdout)

