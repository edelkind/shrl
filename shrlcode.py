#!/usr/bin/env python

import sys
import argparse, urllib

import cf

parser = argparse.ArgumentParser(
        description="encode/decode strings or streams to/from url (percent) encoding")

parser.add_argument('-d', action="store_true", help='decode url-encoded data')
parser.add_argument('args', nargs=argparse.REMAINDER)

def shrldecode(src):
    return urllib.unquote(src)

def shrlencode(src):
    return urllib.quote(src)


if __name__ == "__main__":
    args = parser.parse_args()

    if args.d:
        shrlfunc = shrldecode
    else:
        shrlfunc = shrlencode

    if args.args:
        for arg in args.args:
            print shrlfunc(arg)
    else:
        for line in sys.stdin:
            # don't just blindly strip all trailing ws
            if line[-1:] == '\n':
                line = line[:-1]
            print shrlfunc(line)

