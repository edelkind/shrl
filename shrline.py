#!/usr/bin/env python

import sys

from BaseHTTPServer import BaseHTTPRequestHandler
from StringIO import StringIO

def addDict(target, data):
    k,v = data.split('=', 1)
    target[k] = v

class HTTPRequest(BaseHTTPRequestHandler):
    def __init__(self, request_io):
        self.rfile = request_io
        self.error_code = self.error_message = None

        self.parse_cookies()
        self.parse_params_get()
        self.parse_params_post()

    def send_error(self, code, message):
        self.error_code = code
        self.error_message = message

    def parse_http(self):
        self.raw_requestline = self.rfile.readline()
        self.parse_request()

    def parse_byLine(self):
        self.headers.clear()
        self.params_get  = {}
        self.params_post = {}
        self.cookies     = {}

        for line in self.rfile:
            tag,data = line.strip().split(':',1)
            if tag == "CMD":
                self.command = data
            else if tag == "PATH":
                self.path = data
            else if tag == "HOST":
                self.headers['host'] = data
            else if tag == "HEAD":
                addDict(self.headers, data)
            else if tag == "G_PARAM":
                addDict(self.params_get, data)
            else if tag == 'P_PARAM':
                addDict(self.params_post, data)
            else if tag == 'COOKIE':
                addDict(self.cookies, data)

        if len(self.params_get):
            gp = []
            for k,v in self.params_get.iteritems():
                gp.append(k + '=' + v)
            self.path = self.path + '?' + '&'.join(gp)

        if len(self.params_post):
            pp = []
            [ pp.append(k + '=' + v) for k,v in self.params_post ]
            #for k,v in self.params_post.iteritems():
            #    pp.append(k + '=' + v)
            self.path = self.path + '?' + '&'.join(gp)

        if len(self.cookies):
            ckl = []
            [ ckl.append(k + '=' + v) for k,v in self.cookies ]
            self.headers['cookie'] = '; '.join(ckl)





    def parse_cookies(self):
        self.cookies = {}

        if 'cookie' in self.headers:
            for ck in self.headers['cookie'].split(';'):
                addDict(self.cookies, ck)


    def parse_params_get(self):
        self.params_get = {}

        base_path, get_params = self.path.split('?', 1)
        if get_params:
            for param in get_params.split('&'):
                addDict(self.params_get, param)
                self.params_get.append(param.strip())

        self.path = base_path


    def parse_params_post(self):
        self.params_post = []

        if 'content-length' in self.headers and self.command == "POST":

            data = self.rfile.read(int(self.headers['content-length']))
            for param in data.split('&'):
                self.params_post.append(param.strip())


    def byLine(self, dest):
	print >>dest, "CMD:" + self.command
	print >>dest, "PATH:" + self.path
        try:
            print >>dest, "HOST:" + self.headers['host']
        except KeyError:
            pass
	for hdr in self.headers.keys():
            if  hdr == 'content-length' or \
                hdr == 'cookie' or \
                hdr == 'host':
                    continue
            print >>dest, "HEAD:" + hdr + '=' + self.headers[hdr]

        for ck in self.cookies:
            print >>dest, "COOKIE:" + ck

        for param in self.params_get:
            print >>dest, "G_PARAM:" + param

        for param in self.params_post:
            print >>dest, "P_PARAM:" + param

    def write_request(self, dest):
        self.wfile = dest


if __name__ == "__main__":
    req = HTTPRequest(sys.stdin)
    if req.error_code:
	print >>sys.stderr, "ERROR:", req.error_message
	sys.exit(1)

    req.byLine(sys.stdout)

