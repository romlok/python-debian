# debian_support.py -- Python module for Debian metadata
# Copyright (C) 2005 Florian Weimer <fw@deneb.enyo.de>
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""This module implements facilities to deal with Debian-specific metadata."""

import os
import re
import sha
import types

import apt_pkg
apt_pkg.init()

class ParseError(Exception):
    """An exception which is used to signal a parse failure.

    Attributes:

    filename - name of the file
    lineno - line number in the file
    msg - error message

    """
    
    def __init__(self, filename, lineno, msg):
        assert type(lineno) == types.IntType
        self.filename = filename
        self.lineno = lineno
        self.msg = msg

    def __str__(self):
        return self.msg

    def __repr__(self):
        return "ParseError(%s, %d, %s)" % (`self.filename`,
                                           self.lineno,
                                           `self.msg`)

    def printOut(self, file):
        """Writes a machine-parsable error message to file."""
        file.write("%s:%d: %s\n" % (self.filename, self.lineno, self.msg))
        file.flush()

class Version:
    """Version class which uses the original APT comparison algorithm."""

    def __init__(self, version):
        """Creates a new Version object."""
        t = type(version)
        if t == types.UnicodeType:
            version = version.encode('UTF-8')
        else:
            assert t == types.StringType, `version`
        assert version <> ""
        self.__asString = version

    def __str__(self):
        return self.__asString

    def __repr__(self):
        return 'Version(%s)' % `self.__asString`

    def __cmp__(self, other):
        return apt_pkg.VersionCompare(self.__asString, other.__asString)


version_compare = apt_pkg.VersionCompare

class PackageFile:
    """A Debian package file.

    Objects of this class can be used to read Debian's Source and
    Packages files."""

    re_field = re.compile(r'^([A-Za-z][A-Za-z0-9-]+):(?:\s*(.*?))?\s*$')
    re_continuation = re.compile(r'^\s+(?:\.|(\S.*?)\s*)$')

    def __init__(self, name, fileObj=None):
        """Creates a new package file object.

        name - the name of the file the data comes from
        fileObj - an alternate data source; the default is to open the
                  file with the indicated name.
        """
        if fileObj is None:
            fileObj = file(name)
        self.name = name
        self.file = fileObj
        self.lineno = 0

    def __iter__(self):
        line = self.file.readline()
        self.lineno += 1
        pkg = []
        while line:
            if line == '\n':
                if len(pkg) == 0:
                    self.raiseSyntaxError('expected package record')
                yield pkg
                pkg = []
                line = self.file.readline()
                self.lineno += 1
                continue
            
            match = self.re_field.match(line)
            if not match:
                self.raiseSyntaxError("expected package field")
            (name, contents) = match.groups()
            contents = contents or ''

            while True:
                line = self.file.readline()
                self.lineno += 1
                match = self.re_continuation.match(line)
                if match:
                    (ncontents,) = match.groups()
                    if ncontents is None:
                        ncontents = ""
                    contents = "%s\n%s" % (contents, ncontents)
                else:
                    break
            pkg.append((name, contents))
        if pkg:
            yield pkg

    def raiseSyntaxError(self, msg, lineno=None):
        if lineno is None:
            lineno = self.lineno
        raise ParseError(self.name, lineno, msg)

class PseudoEnum:
    """A base class for types which resemble enumeration types."""
    def __init__(self, name, order):
        self._name = name
        self._order = order
    def __repr__(self):
        return '%s(%s)'% (self.__class__._name__, `name`)
    def __str__(self):
        return self._name
    def __cmp__(self, other):
        return cmp(self._order, other._order)
    def __hash__(self):
        return hash(self._order)

class Release(PseudoEnum): pass

def listReleases():
    releases = {}
    rels = ("potato", "woody", "sarge", "etch", "lenny", "sid")
    for r in range(len(rels)):
        releases[rels[r]] = Release(rels[r], r)
    Release.releases = releases
    return releases
def internRelease(name, releases=listReleases()):
    if releases.has_key(name):
        return releases[name]
    else:
        return None
del listReleases

def readLinesSHA1(lines):
    m = sha.new()
    for l in lines:
        m.update(l)
    return m.hexdigest()

def patchesFromEdScript(source,
                        re_cmd=re.compile(r'^(\d+)(?:,(\d+))?([acd])$')):
    """Converts source to a stream of patches.

    Patches are triples of line indexes:

    - number of the first line to be replaced
    - one plus the number of the last line to be replaced
    - list of line replacements

    This is enough to model arbitrary additions, deletions and
    replacements.
    """

    i = iter(source)
    
    for line in i:
        match = re_cmd.match(line)
        if match is None:
            raise ValueError, "invalid patch command: " + `line`

        (first, last, cmd) = match.groups()
        first = int(first)
        if last is not None:
            last = int(last)

        if cmd == 'd':
            first = first - 1
            if last is None:
                last = first + 1
            yield (first, last, [])
            continue

        if cmd == 'a':
            if last is not None:
                raise ValueError, "invalid patch argument: " + `line`
            last = first
        else:                           # cmd == c
            first = first - 1
            if last is None:
                last = first + 1

        lines = []
        for l in i:
            if l == '':
                raise ValueError, "end of stream in command: " + `line`
            if l == '.\n' or l == '.':
                break
            lines.append(l)
        yield (first, last, lines)

def patchLines(lines, patches):
    """Applies patches to lines.  Updates lines in place."""
    for (first, last, args) in patches:
        lines[first:last] = args

def replaceFile(lines, local):

    import os.path

    local_new = local + '.new'
    new_file = file(local_new, 'w+')

    try:
        for l in lines:
            new_file.write(l)
        new_file.close()
        os.rename(local_new, local)
    finally:
        if os.path.exists(local_new):
            os.unlink(local_new)

def downloadGunzipLines(remote):
    """Downloads a file from a remote location and gunzips it.

    Returns the lines in the file."""

    # The implementation is rather crude, but it seems that the gzip
    # module needs a real file for input.

    import gzip
    import tempfile
    import urllib

    (handle, fname) = tempfile.mkstemp()
    try:
        os.close(handle)
        (filename, headers) = urllib.urlretrieve(remote, fname)
        gfile = gzip.GzipFile(filename)
        lines = gfile.readlines()
        gfile.close()
    finally:
        os.unlink(fname)
    return lines
        
def downloadFile(remote, local):
    """Copies a gzipped remote file to the local system.

    remote - URL, without the .gz suffix
    local - name of the local file
    """
    
    lines = downloadGunzipLines(remote + '.gz')
    replaceFile(lines, local)
    return lines

def updateFile(remote, local, verbose=None):
    """Updates the local file by downloading a remote patch.

    Returns a list of lines in the local file.
    """

    try:
        local_file = file(local)
    except IOError:
        if verbose:
            print "updateFile: no local copy, downloading full file"
        return downloadFile(remote, local)

    lines = local_file.readlines()
    local_file.close()
    local_hash = readLinesSHA1(lines)
    patches_to_apply = []
    patch_hashes = {}
    
    import urllib
    index_name = remote + '.diff/Index'

    re_whitespace=re.compile('\s+')

    try:
        index_url = urllib.urlopen(index_name)
        index_fields = list(PackageFile(index_name, index_url))
    except ParseError:
        # FIXME: urllib does not raise a proper exception, so we parse
        # the error message.
        if verbose:
            print "updateFile: could not interpret patch index file"
        return downloadFile(remote, local)
    except IOError:
        if verbose:
            print "updateFile: could not download patch index file"
        return downloadFile(remote, local)

    for fields in index_fields:
        for (field, value) in fields:
            if field == 'SHA1-Current':
                (remote_hash, remote_size) = re_whitespace.split(value)
                if local_hash == remote_hash:
                    if verbose:
                        print "updateFile: local file is up-to-date"
                    return lines
                continue

            if field =='SHA1-History':
                for entry in value.splitlines():
                    if entry == '':
                        continue
                    (hist_hash, hist_size, patch_name) \
                                = re_whitespace.split(entry)

                    # After the first patch, we have to apply all
                    # remaining patches.
                    if patches_to_apply or  hist_hash == local_hash:
                        patches_to_apply.append(patch_name)
                        
                continue
            
            if field == 'SHA1-Patches':
                for entry in value.splitlines():
                    if entry == '':
                        continue
                    (patch_hash, patch_size, patch_name) \
                                 = re_whitespace.split(entry)
                    patch_hashes[patch_name] = patch_hash
                continue
            
            if verbose:
                print "updateFile: field %s ignored" % `field`
        
    if not patches_to_apply:
        if verbose:
            print "updateFile: could not find historic entry", local_hash
        return downloadFile(remote, local)

    for patch_name in patches_to_apply:
        print "updateFile: downloading patch " + `patch_name`
        patch_contents = downloadGunzipLines(remote + '.diff/' + patch_name
                                          + '.gz')
        if readLinesSHA1(patch_contents ) <> patch_hashes[patch_name]:
            raise ValueError, "patch %s was garbled" % `patch_name`
        patchLines(lines, patchesFromEdScript(patch_contents))
        
    new_hash = readLinesSHA1(lines)
    if new_hash <> remote_hash:
        raise ValueError, ("patch failed, got %s instead of %s"
                           % (new_hash, remote_hash))

    replaceFile(lines, local)
    return lines

def mergeAsSets(*args):
    """Create an order set (represented as a list) of the objects in
    the sequences passed as arguments."""
    s = {}
    for x in args:
        for y in x:
            s[y] = True
    l = s.keys()
    l.sort()
    return l

def test():
    # Version
    assert Version('0') < Version('a')
    assert Version('1.0') < Version('1.1')
    assert Version('1.2') < Version('1.11')
    assert Version('1.0-0.1') < Version('1.1')
    assert Version('1.0-0.1') < Version('1.0-1')
    assert Version('1.0-0.1') == Version('1.0-0.1')
    assert Version('1.0-0.1') < Version('1.0-1')
    assert Version('1.0final-5sarge1') > Version('1.0final-5') \
           > Version('1.0a7-2')
    assert Version('0.9.2-5') < Version('0.9.2+cvs.1.0.dev.2004.07.28-1.5')
    assert Version('1:500') < Version('1:5000')
    assert Version('100:500') > Version('11:5000')
    assert Version('1.0.4-2') > Version('1.0pre7-2')
    assert Version('1.5~rc1') < Version('1.5')
    assert Version('1.5~rc1') < Version('1.5+b1')
    assert Version('1.5~rc1') < Version('1.5~rc2')
    assert Version('1.5~rc1') > Version('1.5~dev0')

    # Release
    assert internRelease('sarge') < internRelease('etch')

    # PackageFile
    # for p in PackageFile('../../data/packages/sarge/Sources'):
    #     assert p[0][0] == 'Package'
    # for p in PackageFile('../../data/packages/sarge/Packages.i386'):
    #     assert p[0][0] == 'Package'

    # Helper routines
    assert readLinesSHA1([]) == 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
    assert readLinesSHA1(['1\n', '23\n']) \
           == '14293c9bd646a15dc656eaf8fba95124020dfada'

    file_a = map(lambda x: "%d\n" % x, range(1, 18))
    file_b = ['0\n', '1\n', '<2>\n', '<3>\n', '4\n', '5\n', '7\n', '8\n',
              '11\n', '12\n', '<13>\n', '14\n', '15\n', 'A\n', 'B\n', 'C\n',
              '16\n', '17\n',]
    patch = ['15a\n', 'A\n', 'B\n', 'C\n', '.\n', '13c\n', '<13>\n', '.\n',
             '9,10d\n', '6d\n', '2,3c\n', '<2>\n', '<3>\n', '.\n', '0a\n',
             '0\n', '.\n']
    patchLines(file_a, patchesFromEdScript(patch))
    assert ''.join(file_b) == ''.join(file_a)

    assert len(mergeAsSets([])) == 0
    assert ''.join(mergeAsSets("abc", "cb")) == "abc"

if __name__ == "__main__":
    test()
