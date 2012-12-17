#!/usr/bin/env python

import sys, re
import argparse, urllib

import cf

DO_URLENCODE = True
IGNORE_CASE  = True
USE_REGEX    = False


parser = argparse.ArgumentParser(
        description="replace shrl by-line input as specified")

parser.add_argument('-c', '--cookie', action='append', metavar='N=V', default=[], help='replace a cookie (url-encoded)')
parser.add_argument('-H', '--header', action='append', metavar='N=V', default=[], help='replace a header')
parser.add_argument('-T', '--host', metavar='HOST', help='replace the target host')
parser.add_argument('-p', '--param', action='append', metavar='N=V', default=[], help='replace a parameter (url-encoded)')
parser.add_argument('-a', '--any', action='append', metavar='N=V', default=[], help='replace any type of variable')
parser.add_argument('-r', '--regex', action="store_true", help='use regular expressions for matching names')
parser.add_argument('-U', '--no-urlencode', action="store_true", help='never use percent-encoding')
parser.add_argument('-I', '--match-case', action="store_true", help='do not ignore case')

class subst:
    cookies = {}
    headers = {}
    params  = {}
    host    = None

def enforce_nv(s):
    if '=' not in s:
        print >>sys.stderr, "ERROR: not in name=value format:", s
        sys.exit(1)

def pencode(s):
    if not DO_URLENCODE:
        return s
    return urllib.quote(s)

def ds_lookup(ds, k):
    """
    Match a key in a dictionary store.  The match may be case insensitive
    depending on the value of IGNORE_CASE, and it may be a precise match or a
    regex, depending on the value of USE_REGEX.

    Returns the value if a match is found, or None otherwise.
    """

    if IGNORE_CASE:
        k = k.lower()

    if not USE_REGEX:
        if k not in ds:
            return None
        return ds[k]

    # cycle through all keys to test for regex
    for thiskey in ds:
        if re.search(thiskey, k):
            return ds[thiskey]

    return None

def r_data(cmd, data):
    """
    >>> subst.host='alice'
    >>> r_data('HOST', 'bob')
    'alice'

    >>> subst.cookies['cook'] = 'linguine'
    >>> r_data('COOKIE', 'cook=potatoes')
    'cook=linguine'
    """

    if cmd == "HOST":
        if subst.host:
            data = subst.host
    elif cmd == "COOKIE":
        k,v=data.split('=', 1)
        newval = ds_lookup(subst.cookies, k)
        if newval is not None:
            v = pencode(newval)
        data = '='.join((k,v))
    elif cmd == "HEAD":
        k,v=data.split('=', 1)
        newval = ds_lookup(subst.headers, k)
        if newval is not None:
            v = newval
        data = '='.join((k,v))
    elif cmd == "G_PARAM" or cmd == "P_PARAM":
        k,v=data.split('=', 1)
        newval = ds_lookup(subst.params, k)
        if newval is not None:
            v = pencode(newval)
        data = '='.join((k,v))

    return data

def replace_stream(istream, ostream):
    for line in istream:
        try:
            cmd, data = line.rstrip().split(':', 1)
        except ValueError:
            print >>sys.stderr, "malformed input:", line.rstrip()
            sys.exit(1)

        data = r_data(cmd, data)
        print >>ostream, cmd + ':' + data


if __name__ == "__main__":
    args = parser.parse_args()

    if args.no_urlencode:
        DO_URLENCODE = False

    if args.match_case:
        IGNORE_CASE = False

    if args.regex:
        USE_REGEX = True

    for c in args.cookie:
        enforce_nv(c)
        k,v = c.split('=', 1)
        if IGNORE_CASE:
            k = k.lower()
        subst.cookies[k] = v

    for h in args.header:
        enforce_nv(h)
        k,v = h.split('=', 1)
        if IGNORE_CASE:
            k = k.lower()
        subst.headers[k] = v

    for p in args.param:
        enforce_nv(p)
        k,v = p.split('=', 1)
        if IGNORE_CASE:
            k = k.lower()
        subst.params[k] = v

    for p in args.any:
        enforce_nv(p)
        k,v = p.split('=', 1)
        if IGNORE_CASE:
            k = k.lower()
        subst.cookies[k] = v
        subst.headers[k] = v
        subst.params[k]  = v

    if args.host:
        subst.host = args.host

    replace_stream(sys.stdin, sys.stdout)
