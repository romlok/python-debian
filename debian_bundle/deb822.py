# vim: fileencoding=utf-8
#
# A python interface for various rfc822-like formatted files used by Debian
# (.changes, .dsc, Packages, Sources, etc)
#
# Copyright (C) 2005-2006  dann frazier <dannf@dannf.org>
# Copyright (C) 2006       John Wright <john@movingsucks.org>
# Copyright (C) 2006       Adeodato Simó <dato@net.com.org.es>
# Copyright (C) 2008       Stefano Zacchiroli <zack@upsilon.cc>
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

import new
import re
import sys
import StringIO
import UserDict

class Deb822Dict(object, UserDict.DictMixin):
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

        # TODO Think about still using apt_pkg even if shared_storage is False,
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
                # XXX Uh, really print value if value == '\n'?
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

class PkgRelation(object):
    """Inter-package relationships

    Structured representation of the relationships of a package to another,
    i.e. of what can appear in a Deb882 field like Depends, Recommends,
    Suggests, ... (see Debian Policy 7.1).
    """

    # XXX *NOT* a real dependency parser, and that is not even a goal here, we
    # just parse as much as we need to split the various parts composing a
    # dependency, checking their correctness wrt policy is out of scope
    __dep_RE = re.compile( \
            r'^\s*(?P<name>[a-zA-Z0-9.+\-]{2,})(\s*\(\s*(?P<relop>[>=<]+)\s*(?P<version>[0-9a-zA-Z:\-+~.]+)\s*\))?(\s*\[(?P<archs>[\s!\w\-]+)\])?\s*$')
    __comma_sep_RE = re.compile(r'\s*,\s*')
    __pipe_sep_RE = re.compile(r'\s*\|\s*')
    __blank_sep_RE = re.compile(r'\s*')

    @classmethod
    def parse_relations(cls, raw):
        """Parse a package relationship string (i.e. the value of a field like
        Depends, Recommends, Build-Depends ...)
        """
        def parse_archs(raw):
            # assumption: no space beween '!' and architecture name
            archs = []
            for arch in cls.__blank_sep_RE.split(raw.strip()):
                if len(arch) and arch[0] == '!':
                    archs.append((False, arch[1:]))
                else:
                    archs.append((True, arch))
            return archs

        def parse_rel(raw):
            match = cls.__dep_RE.match(raw)
            if match:
                parts = match.groupdict()
                d = { 'name': parts['name'] }
                if not (parts['relop'] is None or parts['version'] is None):
                    d['version'] = (parts['relop'], parts['version'])
                else:
                    d['version'] = None
                if parts['archs'] is None:
                    d['arch'] = None
                else:
                    d['arch'] = parse_archs(parts['archs'])
                return d
            else:
                print >> sys.stderr, \
                        'deb822.py: WARNING: cannot parse package' \
                        ' relationship "%s", returning it raw' % raw
                return { 'name': raw, 'version': None, 'arch': None }

        tl_deps = cls.__comma_sep_RE.split(raw.strip()) # top-level deps
        cnf = map(cls.__pipe_sep_RE.split, tl_deps)
        return map(lambda or_deps: map(parse_rel, or_deps), cnf)


class _lowercase_dict(dict):
    """Dictionary wrapper which lowercase keys upon lookup."""

    def __getitem__(self, key):
        return dict.__getitem__(self, key.lower())


class _PkgRelationMixin(object):
    """Package relationship mixin

    Inheriting from this mixin you can extend a Deb882 object with attributes
    letting you access inter-package relationship in a structured way, rather
    than as strings. For example, while you can usually use pkg['depends'] to
    obtain the Depends string of package pkg, mixing in with this class you
    gain pkg.depends to access Depends as a Pkgrel instance

    To use, subclass _PkgRelationMixin from a class with a _relationship_fields
    attribute. It should be a list of field names for which structured access
    is desired; for each of them a method wild be added to the inherited class.
    The method name will be the lowercase version of field name; '-' will be
    mangled as '_'. The method would return relationships in the same format of
    the PkgRelation' relations property.

    See Packages and Sources as examples.
    """

    def __init__(self, *args, **kwargs):
        self.__relations = _lowercase_dict({})
        self.__parsed_relations = False
        for name in self._relationship_fields:
            # To avoid reimplementing Deb822 key lookup logic we use a really
            # simple dict subclass which just lowercase keys upon lookup. Since
            # dictionary building happens only here, we ensure that all keys
            # are in fact lowercase.
            # With this trick we enable users to use the same key (i.e. field
            # name) of Deb822 objects on the dictionary returned by the
            # relations property.
            keyname = name.lower()
            if self.has_key(name):
                self.__relations[keyname] = None   # lazy value
                    # all lazy values will be expanded before setting
                    # __parsed_relations to True
            else:
                self.__relations[keyname] = []

    @property
    def relations(self):
        """Return a dictionary of inter-package relationships among the current
        and other packages.

        Dictionary keys depend on the package kind. Binary packages have keys
        like 'depends', 'recommends', ... while source packages have keys like
        'build-depends', 'build-depends-indep' and so on. See the Debian policy
        for the comprehensive field list.

        Dictionary values are package relationships returned as lists of lists
        of dictionaries (see below for some examples).

        The encoding of package relationships is as follows:
        - the top-level lists corresponds to the comma-separated list of
          Deb822, their components form a conjuction, i.e. they have to be
          AND-ed together
        - the inner lists corresponds to the pipe-separated list of Deb822,
          their components form a disjunction, i.e. they have to be OR-ed
          together
        - member of the inner lists are dictionaries with the following keys:
          - name:       package (or virtual package) name
          - version:    A pair <operator, version> if the relationship is
                        versioned, None otherwise. operator is one of "<<",
                        "<=", "=", ">=", ">>"; version is the given version as
                        a string.
          - arch:       A list of pairs <polarity, architecture> if the
                        relationship is architecture specific, None otherwise.
                        Polarity is a boolean (false if the architecture is
                        negated with "!", true otherwise), architecture the
                        Debian archtiecture name as a string.

        Examples:

          "emacs | emacsen, make, debianutils (>= 1.7)"     becomes
          [ [ {'name': 'emacs'}, {'name': 'emacsen'} ],
            [ {'name': 'make'} ],
            [ {'name': 'debianutils', 'version': ('>=', '1.7')} ] ]

          "tcl8.4-dev, procps [!hurd-i386]"                 becomes
          [ [ {'name': 'tcl8.4-dev'} ],
            [ {'name': 'procps', 'arch': (false, 'hurd-i386')} ] ]
        """
        if not self.__parsed_relations:
            lazy_rels = filter(lambda n: self.__relations[n] is None,
                    self.__relations.keys())
            for n in lazy_rels:
                self.__relations[n] = PkgRelation.parse_relations(self[n])
            self.__parsed_relations = True
        return self.__relations

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
            keyl = key.lower()
            if keyl not in self._multivalued_fields:
                value = self[key]
                if not value or value[0] == '\n':
                    # XXX Uh, really print value if value == '\n'?
                    fd.write('%s:%s\n' % (key, value))
                else:
                    fd.write('%s: %s\n' % (key, value))
            else:
                fd.write(key + ":")
                if hasattr(self[key], 'keys'): # single-line
                    array = [ self[key] ]
                else: # multi-line
                    fd.write("\n")
                    array = self[key]

                order = self._multivalued_fields[keyl]
                try:
                    field_lengths = self._fixed_field_lengths
                except AttributeError:
                    field_lengths = {}
                for item in array:
                    for x in order:
                        raw_value = str(item[x])
                        try:
                            length = field_lengths[keyl][x]
                        except KeyError:
                            value = raw_value
                        else:
                            value = (length - len(raw_value)) * " " + raw_value
                        fd.write(" %s" % value)
                    fd.write("\n")
        if return_string:
            return fd.getvalue()


###

class Dsc(_multivalued):
    _multivalued_fields = {
        "files": [ "md5sum", "size", "name" ],
        "checksums-sha1": ["sha1", "size", "name"],
        "checksums-sha256": ["sha256", "size", "name"],
    }


class Changes(_multivalued):
    _multivalued_fields = {
        "files": [ "md5sum", "size", "section", "priority", "name" ],
        "checksums-sha1": ["sha1", "size", "name"],
        "checksums-sha256": ["sha256", "size", "name"],
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

    @property
    def _fixed_field_lengths(self):
        fixed_field_lengths = {}
        for key in self._multivalued_fields:
            if hasattr(self[key], 'keys'):
                # Not multi-line -- don't need to compute the field length for
                # this one
                continue
            length = self._get_size_field_length(key)
            fixed_field_lengths[key] = {"size": length}
        return fixed_field_lengths

    def _get_size_field_length(self, key):
        lengths = [len(str(item['size'])) for item in self[key]]
        return max(lengths)


class Release(_multivalued):
    """Represents a Release file

    Set the size_field_behavior attribute to "dak" to make the size field
    length only as long as the longest actual value.  The default,
    "apt-ftparchive" makes the field 16 characters long regardless.
    """
    # FIXME: Add support for detecting the behavior of the input, if
    # constructed from actual 822 text.

    _multivalued_fields = {
        "md5sum": [ "md5sum", "size", "name" ],
        "sha1": [ "sha1", "size", "name" ],
        "sha256": [ "sha256", "size", "name" ],
    }

    __size_field_behavior = "apt-ftparchive"
    def set_size_field_behavior(self, value):
        if value not in ["apt-ftparchive", "dak"]:
            raise ValueError("size_field_behavior must be either "
                             "'apt-ftparchive' or 'dak'")
        else:
            self.__size_field_behavior = value
    size_field_behavior = property(lambda self: self.__size_field_behavior,
                                   set_size_field_behavior)

    @property
    def _fixed_field_lengths(self):
        fixed_field_lengths = {}
        for key in self._multivalued_fields:
            length = self._get_size_field_length(key)
            fixed_field_lengths[key] = {"size": length}
        return fixed_field_lengths

    def _get_size_field_length(self, key):
        if self.size_field_behavior == "apt-ftparchive":
            return 16
        elif self.size_field_behavior == "dak":
            lengths = [len(str(item['size'])) for item in self[key]]
            return max(lengths)


class Sources(Dsc, _PkgRelationMixin):
    """Represent an APT source package list"""

    _relationship_fields = [ 'build-depends', 'build-depends-indep',
            'build-conflicts', 'build-conflicts-indep' ]

    def __init__(self, *args, **kwargs):
        Dsc.__init__(self, *args, **kwargs)
        _PkgRelationMixin.__init__(self, *args, **kwargs)


class Packages(Deb822, _PkgRelationMixin):
    """Represent an APT binary package list"""

    _relationship_fields = [ 'depends', 'pre-depends', 'recommends',
            'suggests', 'breaks', 'conflicts', 'provides', 'replaces',
            'enhances' ]

    def __init__(self, *args, **kwargs):
        Deb822.__init__(self, *args, **kwargs)
        _PkgRelationMixin.__init__(self, *args, **kwargs)

###

class _CaseInsensitiveString(str):
    """Case insensitive string.
    """

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
