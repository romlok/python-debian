#
# A python interface for various rfc822-like formatted files used by Debian
# (.changes, .dsc, Packages, Sources, etc)
#
# Written by dann frazier <dannf@dannf.org>
# Copyright (C) 2005-2006  dann frazier <dannf@dannf.org>
# Copyright (C) 2006       John Wright <john@movingsucks.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# dated June, 1991.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#

import re
import StringIO

class Deb822(dict):
    def __init__(self, object):
        """Create a new Deb822 instance, using object for initial fields

        object may be a file-like object (i.e. having a readlines() method)
        containing the contents of an RFC822-formatted file, or it may be
        another Deb822 instance.
        """
        
        if isinstance(object, Deb822):
            fp = StringIO.StringIO()
            object.dump(fp)
            fp.seek(0)
        else:
            fp = object
        
        single = re.compile("^(?P<key>\S+):\s+(?P<data>\S.*)$")
        multi = re.compile("^(?P<key>\S+):\s*$")
        multidata = re.compile("^\s(?P<data>.*)$")
        ws = re.compile("^\s*$")

        # Storing keys here is redundant, but it allows us to keep track of the
        # original order.
        self._keys = []
        
        curkey = None
        content = ""
        for line in self.strip_gpg_readlines(fp):
            if ws.match(line):
                if curkey:
                    self[curkey] += content
                    curkey = None
                    content = ""
                continue

            m = single.match(line)
            if m:
                if curkey:
                    self[curkey] += content
                curkey = m.group('key')
                self[curkey] = m.group('data')
                self._keys.append(curkey)
                content = ""
                continue

            m = multi.match(line)
            if m:
                if curkey:
                    self[curkey] += content
                curkey = m.group('key')
                self[curkey] = ""
                self._keys.append(curkey)
                content = ""
                continue

            m = multidata.match(line)
            if m:
                content += '\n' + line[:-1]
                continue

        if curkey:
            self[curkey] += content

    def dump(self, fd=None):
        """Dump the the contents in the original format

        If fd is None, return a string.
        """
        
        if fd is None:
            fd = StringIO.StringIO()
            return_string = True
        else:
            return_string = False
        for key in self.keys():
            fd.write(key + ": " + self[key] + "\n")
        if return_string:
            return fd.getvalue()

    def isSingleLine(self, s):
        if s.count("\n"):
            return False
        else:
            return True

    def isMultiLine(self, s):
        return not self.isSingleLine(s)

    def _mergeFields(self, s1, s2):
        if not s2:
            return s1
        if not s1:
            return s2
        
        if self.isSingleLine(s1) and self.isSingleLine(s2):
            ## some fields are delimited by a single space, others
            ## a comma followed by a space.  this heuristic assumes
            ## that there are multiple items in one of the string fields
            ## so that we can pick up on the delimiter being used
            delim = ' '
            if (s1 + s2).count(', '):
                delim = ', '

            L = (s1 + delim + s2).split(delim)
            L.sort()

            prev = merged = L[0]
            
            for item in L[1:]:
                ## skip duplicate entries
                if item == prev:
                    continue
                merged = merged + delim + item
                prev = item
            return merged
            
        if self.isMultiLine(s1) and self.isMultiLine(s2):
            for item in s2.splitlines(True):
                if item not in s1.splitlines(True):
                    s1 = s1 + "\n" + item
            return s1

        raise ValueError
    
    def mergeFields(self, key, d1, d2 = None):
        ## this method can work in two ways - abstract that away
        if d2 == None:
            x1 = self
            x2 = d1
        else:
            x1 = d1
            x2 = d2

        ## we only have to do work if both objects contain our key
        ## otherwise, we just take the one that does, or raise an
        ## exception if neither does
        if key in x1 and key in x2:
            merged = self._mergeFields(x1[key], x2[key])
        elif key in x1:
            merged = x1[key]
        elif key in x2:
            merged = x2[key]
        else:
            raise KeyError

        ## back to the two different ways - if this method was called
        ## upon an object, update that object in place.
        ## return nothing in this case, to make the author notice a
        ## problem if she assumes the object itself will not be modified
        if d2 == None:
            self[key] = merged
            return None

        return merged

    def strip_gpg_readlines(fp):
        lines = []
        state = 'SAFE'
        gpgre = re.compile(r'^-----(?P<action>BEGIN|END) PGP (?P<what>[^-]+)-----$')
        ws = re.compile('^\s*$')
        for line in fp.readlines():
            m = gpgre.match(line)
            if not m:
                if state == 'SAFE':
                    lines.append(line)
                elif state == 'SIGNED MESSAGE' and ws.match(line):
                    state = 'SAFE'
            elif m.group('action') == 'BEGIN':
                state = m.group('what')
            elif m.group('action') == 'END':
                state = 'SAFE'

        return lines

    strip_gpg_readlines = staticmethod(strip_gpg_readlines)

    def keys(self):
        # Override keys so that we can give the correct order
        other_keys = dict.keys(self)
        for key in self._keys:
            other_keys.remove(key)
        return self._keys + other_keys

class _multivalued(Deb822):
    """A class with (R/W) support for multivalued fields."""
    def __init__(self, fp):
        Deb822.__init__(self, fp)

        for field, fields in self._multivalued_fields.items():
            contents = self.get(field, '')

            if self.isMultiLine(contents):
                self[field] = []
                updater_method = self[field].append
            else:
                self[field] = {}
                updater_method = self[field].update

            for line in filter(None, contents.splitlines()):
                updater_method(dict(zip(fields, line.split())))

    def dump(self, fd=None):
        """Dump the contents in the original format

        If fd is None, return a string.
        """
        
        if fd is None:
            fd = StringIO.StringIO()
            return_string = True
        else:
            return_string = False
        for key in self.keys():
            if key not in self._multivalued_fields:
                # normal behavior
                fd.write(key + ": " + self[key] + "\n")
            else:
                fd.write(key + ":")
                if isinstance(self[key], dict): # single-line
                    array = [ self[key] ]
                else: # multi-line
                    fd.write(" \n")
                    array = self[key]

                order = self._multivalued_fields[key]
                for item in array:
                    fd.write(" " + " ".join([item[x] for x in order]))
                    fd.write("\n")
        if return_string:
            return fd.getvalue()

class Dsc(_multivalued):
    _multivalued_fields = {
        "Files": [ "md5sum", "size", "name" ],
    }
# Sources files have the same multivalued format as dsc files
Sources = Dsc

class Changes(_multivalued):
    _multivalued_fields = {
        "Files": [ "md5sum", "size", "section", "priority", "name" ],
    }

class PdiffIndex(_multivalued):
    _multivalued_fields = {
        "SHA1-Current": [ "SHA1", "size" ],
        "SHA1-History": [ "SHA1", "size", "date" ],
        "SHA1-Patches": [ "SHA1", "size", "date" ],
    }


def xmultiple(f, cls=Deb822):
    """Return a generator for objects from, e.g., a Packages or Sources file

    Use cls as the class to construct objects from
    """
    
    ws = re.compile('^\s*$')
    
    s = StringIO.StringIO()
    line = f.readline()
    while line:
        if ws.match(line):
            s.seek(0)
            yield cls(s)
            s = StringIO.StringIO()
        else:
            s.write(line)
        line = f.readline()

def multiple(f, cls=Deb822):
    """Return a list of objects from, e.g., a Packages or Sources file

    Use cls as the class to construct objects from
    """
    return list(xmultiple(f, cls=cls))
