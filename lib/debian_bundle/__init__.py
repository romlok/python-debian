import os
import sys

sys.stderr.write("WARNING: the 'debian_bundle' package is *DEPRECATED*; "
                 "use the 'debian' package\n")

# Support "from debian_bundle import foo"
parent_dir = os.path.dirname(__path__[0])
__path__.append(os.path.join(parent_dir, "debian"))
