# vim: fileencoding=utf-8
#
# A python interface for various rfc822-like formatted files used by Debian
# (.changes, .dsc, Packages, Sources, etc)
#
# Copyright (C) 2005-2006  dann frazier <dannf@dannf.org>
# Copyright (C) 2006       John Wright <john@movingsucks.org>
# Copyright (C) 2006       Adeodato Simó <dato@net.com.org.es>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation, either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.


try:
    import apt_pkg
    _have_apt_pkg = True
except ImportError:
    _have_apt_pkg = False

import re
import StringIO
import UserDict

class Deb822Dict(UserDict.DictMixin):
    # Subclassing UserDict.DictMixin because we're overriding so much dict
    # functionality that subclassing dict requires overriding many more than
    # the four methods that DictMixin requires.
    """A dictionary-like object suitable for storing RFC822-like data.

    Deb822Dict behaves like a normal dict, except:
        - key lookup is case-insensitive
        - key order is preserved
        - if initialized with a _parsed parameter, it will pull values from
          that dictionary-like object as needed (rather than making a copy).
          The _parsed dict is expected to be able to handle case-insensitive
          keys.

    If _parsed is not None, an optional _fields parameter specifies which keys
    in the _parsed dictionary are exposed.
    """

    # See the end of the file for the definition of _strI

    def __init__(self, _dict=None, _parsed=None, _fields=None):
        self.__dict = {}
        self.__keys = []
        self.__parsed = None

        if _dict is not None:
            # _dict may be a dict or a list of two-sized tuples
            if hasattr(_dict, 'items'):
                items = _dict.items()
            else:
                items = list(_dict)

            try:
                for k, v in items:
                    self[k] = v
            except ValueError:
                this = len(self.__keys)
                len_ = len(items[this])
                raise ValueError('dictionary update sequence element #%d has '
                    'length %d; 2 is required' % (this, len_))
        
        if _parsed is not None:
            self.__parsed = _parsed
            if _fields is None:
                self.__keys.extend([ _strI(k) for k in self.__parsed.keys() ])
            else:
                self.__keys.extend([ _strI(f) for f in _fields if self.__parsed.has_key(f) ])

        
    ### BEGIN DictMixin methods

    def __setitem__(self, key, value):
        key = _strI(key)
        if not key in self:
            self.__keys.append(key)
        self.__dict[key] = value
        
    def __getitem__(self, key):
        key = _strI(key)
        try:
            return self.__dict[key]
        except KeyError:
            if self.__parsed is not None and key in self.__keys:
                return self.__parsed[key]
            else:
                raise
    
    def __delitem__(self, key):
        key = _strI(key)
        del self.__dict[key]
        self.__keys.remove(key)
    
    def keys(self):
        return [str(key) for key in self.__keys]
    
    ### END DictMixin methods

    def __repr__(self):
        return '{%s}' % ', '.join(['%r: %r' % (k, v) for k, v in self.items()])

    def __eq__(self, other):
        mykeys = self.keys(); mykeys.sort()
        otherkeys = other.keys(); otherkeys.sort()
        if not mykeys == otherkeys:
            return False

        for key in mykeys:
            if self[key] != other[key]:
                return False

        # If we got here, everything matched
        return True

    def copy(self):
        # Use self.__class__ so this works as expected for subclasses
        copy = self.__class__(self)
        return copy

    # TODO implement __str__() and make dump() use that?


class Deb822(Deb822Dict):

    def __init__(self, sequence=None, fields=None, _parsed=None):
        """Create a new Deb822 instance.

        :param sequence: a string, or any any object that returns a line of
            input each time, normally a file().  Alternately, sequence can
            be a dict that contains the initial key-value pairs.

        :param fields: if given, it is interpreted as a list of fields that
            should be parsed (the rest will be discarded).

        :param _parsed: internal parameter.
        """

        if hasattr(sequence, 'items'):
            _dict = sequence
            sequence = None
        else:
            _dict = None
        Deb822Dict.__init__(self, _dict=_dict, _parsed=_parsed, _fields=fields)

        if sequence is not None:
            try:
                self._internal_parser(sequence, fields)
            except EOFError:
                pass

    def iter_paragraphs(cls, sequence, fields=None, shared_storage=True):
        """Generator that yields a Deb822 object for each paragraph in sequence.

        :param sequence: same as in __init__.

        :param fields: likewise.

        :param shared_storage: if sequence is a file(), apt_pkg will be used 
            if available to parse the file, since it's much much faster. On the
            other hand, yielded objects will share storage, so they can't be
            kept across iterations. (Also, PGP signatures won't be stripped
            with apt_pkg.) Set this parameter to False to disable using apt_pkg. 
        """

        # TODO Think about still using apt_pkg evein if shared_storage is False,
        # by somehow instructing the constructor to make copy of the data. (If
        # this is still faster.)

        if _have_apt_pkg and shared_storage and isinstance(sequence, file):
            parser = apt_pkg.ParseTagFile(sequence)
            while parser.Step() == 1:
                yield cls(fields=fields, _parsed=parser.Section)
        else:
            iterable = iter(sequence)
            x = cls(iterable, fields)
            while len(x) != 0:
                yield x
                x = cls(iterable, fields)

    iter_paragraphs = classmethod(iter_paragraphs)

    ###

    def _internal_parser(self, sequence, fields=None):
        single = re.compile("^(?P<key>\S+)\s*:\s*(?P<data>\S.*?)\s*$")
        multi = re.compile("^(?P<key>\S+)\s*:\s*$")
        multidata = re.compile("^\s(?P<data>.+?)\s*$")

        wanted_field = lambda f: fields is None or f in fields

        if isinstance(sequence, basestring):
            sequence = sequence.splitlines()

        curkey = None
        content = ""
        for line in self.gpg_stripped_paragraph(sequence):
            m = single.match(line)
            if m:
                if curkey:
                    self[curkey] += content

                if not wanted_field(m.group('key')):
                    curkey = None
                    continue

                curkey = m.group('key')
                self[curkey] = m.group('data')
                content = ""
                continue

            m = multi.match(line)
            if m:
                if curkey:
                    self[curkey] += content

                if not wanted_field(m.group('key')):
                    curkey = None
                    continue

                curkey = m.group('key')
                self[curkey] = ""
                content = ""
                continue

            m = multidata.match(line)
            if m:
                content += '\n' + line # XXX not m.group('data')?
                continue

        if curkey:
            self[curkey] += content

    def __str__(self):
        return self.dump()

    # __repr__ is handled by Deb822Dict

    def dump(self, fd=None):
        """Dump the the contents in the original format

        If fd is None, return a string.
        """

        if fd is None:
            fd = StringIO.StringIO()
            return_string = True
        else:
            return_string = False
        for key, value in self.iteritems():
            if not value or value[0] == '\n':
                # Avoid trailing whitespace after "Field:" if it's on its own
                # line or the value is empty
                fd.write('%s:%s\n' % (key, value))
            else:
                fd.write('%s: %s\n' % (key, value))
        if return_string:
            return fd.getvalue()

    ###

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
    ###

    def gpg_stripped_paragraph(sequence):
        lines = []
        state = 'SAFE'
        gpgre = re.compile(r'^-----(?P<action>BEGIN|END) PGP (?P<what>[^-]+)-----$')
        blank_line = re.compile('^$')
        first_line = True

        for line in sequence:
            line = line.strip('\r\n')

            # skip initial blank lines, if any
            if first_line:
                if blank_line.match(line):
                    continue
                else:
                    first_line = False

            m = gpgre.match(line)

            if not m:
                if state == 'SAFE':
                    if not blank_line.match(line):
                        lines.append(line)
                    else:
                        break
                elif state == 'SIGNED MESSAGE' and blank_line.match(line):
                    state = 'SAFE'
            elif m.group('action') == 'BEGIN':
                state = m.group('what')
            elif m.group('action') == 'END':
                state = 'SAFE'

        if len(lines):
            return lines
        else:
            raise EOFError('only blank lines found in input')

    gpg_stripped_paragraph = staticmethod(gpg_stripped_paragraph)

###

class _multivalued(Deb822):
    """A class with (R/W) support for multivalued fields.
    
    To use, create a subclass with a _multivalued_fields attribute.  It should
    be a dictionary with *lower-case* keys, with lists of human-readable
    identifiers of the fields as the values.  Please see Dsc, Changes, and
    PdiffIndex as examples.
    """
    

    def __init__(self, *args, **kwargs):
        Deb822.__init__(self, *args, **kwargs)

        for field, fields in self._multivalued_fields.items():
            try:
                contents = self[field]
            except KeyError:
                continue

            if self.isMultiLine(contents):
                self[field] = []
                updater_method = self[field].append
            else:
                self[field] = Deb822Dict()
                updater_method = self[field].update

            for line in filter(None, contents.splitlines()):
                updater_method(Deb822Dict(zip(fields, line.split())))

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


###

class Dsc(_multivalued):
    _multivalued_fields = {
        "files": [ "md5sum", "size", "name" ],
    }


class Changes(_multivalued):
    _multivalued_fields = {
        "files": [ "md5sum", "size", "section", "priority", "name" ],
    }

    def get_pool_path(self):
        """Return the path in the pool where the files would be installed"""
    
        # This is based on the section listed for the first file.  While
        # it is possible, I think, for a package to provide files in multiple
        # sections, I haven't seen it in practice.  In any case, this should
        # probably detect such a situation and complain, or return a list...
        
        s = self['files'][0]['section']

        try:
            section, subsection = s.split('/')
        except ValueError:
            # main is implicit
            section = 'main'

        if self['source'].startswith('lib'):
            subdir = self['source'][:4]
        else:
            subdir = self['source'][0]

        return 'pool/%s/%s/%s' % (section, subdir, self['source'])


class PdiffIndex(_multivalued):
    _multivalued_fields = {
        "sha1-current": [ "SHA1", "size" ],
        "sha1-history": [ "SHA1", "size", "date" ],
        "sha1-patches": [ "SHA1", "size", "date" ],
    }


class Release(_multivalued):
    _multivalued_fields = {
        "md5sum": [ "md5sum", "size", "name" ],
        "sha1": [ "sha1", "size", "name" ],
        "sha256": [ "sha256", "size", "name" ],
    }

Sources = Dsc
Packages = Deb822

###

class _CaseInsensitiveString(str):
    """Case insensitive string.
    
    Created objects are cached as to not create the same object twice.
    """

    _cache = {}

    def __new__(cls, str_):
        if isinstance(str_, _CaseInsensitiveString):
            return str_

        try:
            lower = str_.lower()
        except AttributeError:
            raise TypeError('key must be a string')

        cache = _CaseInsensitiveString._cache

        try:
            return cache[lower]
        except KeyError:
            ret = cache[lower] = str.__new__(cls, str_)
            return ret

    def __init__(self, str_):
        str.__init__(self, str_)
        self.str_lower = str_.lower()
        self.str_lower_hash = hash(self.str_lower)

    def __hash__(self):
        return self.str_lower_hash

    def __eq__(self, other):
        return str.__eq__(self.str_lower, other.lower())

    def lower(self):
        return self.str_lower

_strI = _CaseInsensitiveString
