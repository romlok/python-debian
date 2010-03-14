import sys
print >> sys.stderr, "WARNING:",    \
        "the 'deb822' top-level module is *DEPRECATED*,",   \
        "please use 'debian.deb822'"

from debian.deb822 import *
