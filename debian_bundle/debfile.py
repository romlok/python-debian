# DebFile: a Python representation of Debian .deb binary packages.
# Copyright (C) 2007    Stefano Zacchiroli  <zack@debian.org>
# Copyright (C) 2007    Filippo Giunchedi   <filippo@debian.org>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import gzip
import tarfile
import zlib

from arfile import ArFile, ArError
from changelog import Changelog
from deb822 import Deb822

DATA_PART = 'data.tar.gz'
CTRL_PART = 'control.tar.gz'
INFO_PART = 'debian-binary'
MAINT_SCRIPTS = ['preinst', 'postinst', 'prerm', 'postrm', 'config']

CONTROL_FILE = 'control'
CHANGELOG_NATIVE = 'usr/share/doc/%s/changelog.gz'  # with package stem
CHANGELOG_DEBIAN = 'usr/share/doc/%s/changelog.Debian.gz'
MD5_FILE = 'md5sums'

class DebError(ArError):
    pass


class DebPart(object):
    """'Part' of a .deb binary package.
    
    A .deb package is considered as made of 2 parts: a 'data' part
    (corresponding to the 'data.tar.gz' archive embedded in a .deb) and a
    'control' part (the 'control.tar.gz' archive)."""

    def __init__(self, member):
        self.__member = member  # arfile.ArMember file member
        self.__tgz = None

    def tgz(self):
        """Return a TarFile object corresponding to this part of a .deb
        package."""

        if self.__tgz is None:
            gz = gzip.GzipFile(fileobj=self.__member, mode='r')
            self.__tgz = tarfile.TarFile(fileobj=gz, mode='r')
        return self.__tgz

    def has_file(self, fname):
        """Check if this part contains a given file name."""

        return (fname in self.tgz().getnames())

    def get_file(self, fname):
        """Return a file object corresponding to a given file name."""

        return (self.tgz().extractfile(fname))

    def get_content(self, fname):
        """Return the string content of a given file, or None (e.g. for
        directories)."""

        f = self.tgz().extractfile(fname)
        content = None
        if f:   # can be None for non regular or link files
            content = f.read()
            f.close()
        return content

    # container emulation

    def __iter__(self):
        return iter(self.tgz().getnames())

    def __contains__(self, fname):
        return self.has_file(fname)

    def __getitem__(self, fname):
        return self.get_content(fname)


class DebData(DebPart):

    pass

class DebControl(DebPart):

    def scripts(self):
        """ Return a dictionary of maintainer scripts (postinst, prerm, ...)
        mapping script names to script text. """

        scripts = {}
        for fname in MAINT_SCRIPTS:
            if self.has_file(fname):
                scripts[fname] = self.get_content(fname)

        return scripts

    def debcontrol(self):
        """ Return the debian/control as a Deb822 (a Debian-specific dict-like
        class) object.
        
        For a string representation of debian/control try
        .get_content('control') """

        return Deb822(self.get_content(CONTROL_FILE))

    def md5sums(self):
        """ Return a dictionary mapping filenames (of the data part) to
        md5sums. Fails if the control part does not contain a 'md5sum' file. """

        if not self.has_file(MD5_FILE):
            raise DebError("'%s' file not found, can't list MD5 sums" %
                    MD5_FILE)

        md5_file = self.get_file(MD5_FILE)
        sums = {}
        for line in md5_file:
            md5, fname = line.split()
            sums[fname] = md5
        md5_file.close()
        return sums

class DebFile(ArFile):
    """Representation of a .deb file (a Debian binary package)

    DebFile objects have the following (read-only) properties:
        - version       debian .deb file format version (not related with the
                        contained package version), 2.0 at the time of writing
                        for all .deb packages in the Debian archive
        - data          DebPart object corresponding to the data.tar.gz
                        archive contained in the .deb file
        - control       DebPart object corresponding to the control.tar.gz
                        archive contained in the .deb file
    """

    def __init__(self, filename=None, mode='r', fileobj=None):
        ArFile.__init__(self, filename, mode, fileobj)
        if set(self.getnames()) != set([INFO_PART, CTRL_PART, DATA_PART]):
            raise DebError('unexpected .deb content')

        self.__parts = {}
        self.__parts[CTRL_PART] = DebControl(self.getmember(CTRL_PART))
        self.__parts[DATA_PART] = DebData(self.getmember(DATA_PART))
        self.__pkgname = None   # updated lazily by __updatePkgName

        f = self.getmember(INFO_PART)
        self.__version = f.read().strip()
        f.close()

    def __updatePkgName(self):
        self.__pkgname = self.debcontrol()['package']

    version = property(lambda self: self.__version)
    data = property(lambda self: self.__parts[DATA_PART])
    control = property(lambda self: self.__parts[CTRL_PART])

    # proxy methods for the appropriate parts

    def debcontrol(self):
        """ See .control.debcontrol() """
        return self.control.debcontrol()

    def scripts(self):
        """ See .control.scripts() """
        return self.control.scripts()

    def md5sums(self):
        """ See .control.md5sums() """
        return self.control.md5sums

    def changelog(self):
        """ Return a Changelog object for the changelog.Debian.gz of the
        present .deb package. Return None if no changelog can be found. """

        if self.__pkgname is None:
            self.__updatePkgName()

        for fname in [ CHANGELOG_DEBIAN % self.__pkgname,
                CHANGELOG_NATIVE % self.__pkgname ]:
            if self.data.has_file(fname):
                gz = gzip.GzipFile(fileobj=self.data.get_file(fname))
                raw_changelog = gz.read()
                gz.close()
                return Changelog(raw_changelog)
        return None

if __name__ == '__main__':
    import sys
    deb = DebFile(filename=sys.argv[1])
    tgz = deb.control.tgz()
    print tgz.getmember('control')

