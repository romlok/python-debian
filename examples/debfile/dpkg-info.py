#!/usr/bin/python

""" (An approximation of) a 'dpkg --info' implementation relying on DebFile
class. """

import os
import stat
import string
import sys

import debfile

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print "Usage: dpkg-info DEB"
        sys.exit(1)
    fname = sys.argv[1]

    deb = debfile.DebFile(fname)
    if deb.version == '2.0':
        print ' new debian package, version %s.' % deb.version
    print ' size %d bytes: control archive= %d bytes.' % (
            os.stat(fname)[stat.ST_SIZE], deb['control.tar.gz'].size)
    for fname in deb.control:   # print info about control part contents
        content = deb.control[fname]
        if not content:
            continue
        lines = content.split('\n')
        ftype = ''
        try:
            if lines[0].startswith('#!'):
                ftype = lines[0].split()[0]
        except IndexError:
            pass
        print '  %d bytes, %d lines, %s, %s' % (len(content), len(lines),
                fname, ftype)
    for n, v in deb.debcontrol().iteritems(): # print DEBIAN/control fields
        if n.lower() == 'description':  # increase indentation of long dsc
            lines = v.split('\n')
            shortDsc = lines[0]
            longDsc = string.join(map(lambda l: ' ' + l, lines[1:]), '\n')
            print ' %s: %s\n%s' % (n, shortDsc, longDsc)
        else:
            print ' %s: %s' % (n, v)

