import re, string

class deb822(dict):
    def __init__(self, fp):
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

    def dump(self, fd):
        for key in self._keys:
            fd.write(key + ": " + self[key] + "\n")

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

class _multivalued(deb822):
    """A class with (R/W) support for multivalued fields."""
    def __init__(self, fp):
        deb822.__init__(self, fp)

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

    def dump(self, fd):
        for key in self._keys:
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

class dsc(_multivalued):
    _multivalued_fields = {
        "Files": [ "md5sum", "size", "name" ],
    }

class changes(_multivalued):
    _multivalued_fields = {
        "Files": [ "md5sum", "size", "section", "priority", "name" ],
    }

class pdiff_index(_multivalued):
    _multivalued_fields = {
        "SHA1-Current": [ "SHA1", "size" ],
        "SHA1-History": [ "SHA1", "size", "date" ],
        "SHA1-Patches": [ "SHA1", "size", "date" ],
    }
