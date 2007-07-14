#!/usr/bin/python

"""Like "head" for changelog entries, return last n-th entries of the changelog
shipped in a .deb file."""

import string
import sys

import debfile

if __name__ == '__main__':
    if len(sys.argv) > 3 or len(sys.argv) < 2:
        print "Usage: changelog_head DEB [ENTRIES]"
        print "  ENTRIES defaults to 10"
        sys.exit(1)

    entries = 10
    try:
        entries = int(sys.argv[2])
    except IndexError:
        pass

    deb = debfile.DebFile(sys.argv[1])
    chg = deb.changelog()
    entries = chg._blocks[:10]
    print string.join(map(str, entries), '')

