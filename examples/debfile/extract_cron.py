#!/usr/bin/python

"""Script that extracts all cron-related files from a (list of) .deb
package(s)."""

import os
import re
import sys

import debfile

def is_cron(fname):
    return re.match(r'^etc/cron\.(d|daily|hourly|monthly|weekly)\b', fname)

if __name__ == '__main__':
    if not sys.argv[1:]:
        print "Usage: extract_cron DEB ..."
        sys.exit(1)

    for fname in sys.argv[1:]:
        deb = debfile.DebFile(fname)
        cron_files = filter(is_cron, list(deb.data))
        for cron_file in cron_files:
            print 'Extracting cron-related file %s ...' % cron_file
            path = os.path.join('.', cron_file)
            dir = os.path.dirname(path)
            if not os.path.exists(dir):
                os.mkdir(dir)
            out = file(path, 'w')
            out.write(deb.data.get_content(cron_file))
            out.close()

