import sys
print >> sys.stderr, "WARNING:",    \
        "the 'deb822' top-level module is *DEPRECATED*,",   \
        "please use 'debian_bundle.deb822'"

from debian_bundle.deb822 import *
