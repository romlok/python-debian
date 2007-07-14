#!/usr/bin/python

GLOBAL_HEADER = "!<arch>\n"
GLOBAL_HEADER_LENGTH = 8

FILE_HEADER_LENGTH = 60
FILE_MAGIC = "`\n"

class ArError(Exception):
    pass

class ArFile(object):
# XXX trying to mimick the interface of TarFile in the standard library

    def __init__(self, filename=None, mode='r', fileobj=None):
        self.__members_list = [] 
        self.__fname = filename
        self.__fileobj = fileobj
	    
        if mode == "r":
            self.__index_archive()
        pass    # TODO write support

    def __index_archive(self):
        if self.__fname:
            fp = open(self.__fname, "rb")
        elif self.__fileobj:
            fp = self.__fileobj
        else:
            raise ArError

        if fp.read(GLOBAL_HEADER_LENGTH) != GLOBAL_HEADER:
            raise IOError

        while True:
            newmember = ArMember.from_file(fp, self.__fname)
            if not newmember:
                break
            self.__members_list.append(newmember)
            fp.seek(newmember.getsize(), 1) # skip to next header
        
        if self.__fname:
            fp.close()

    def getmember(self, name):
		for m in self.__members_list:
			if name == m.name:
				return m

		return None

    def __updateMembersList(self):
		self.__members_list.sort(lambda f1, f2: cmp(f1.offset, f2.offset))

    def getmembers(self):
# XXX non serve, sono gia' in ordine
#        self.__updateMembersList()
        return self.__members_list

    def getnames(self):
        self.__updateMembersList()
        return map(lambda f: f.name, self.__members_list)

	def __iter__(self):
		return self.__members_list.__iter__()

    def extractall():
        pass    # TODO

    def extract(self, member, path):
        pass    # TODO

    def extractfile(self, member):
		for m in self__members_list:
			if isinstance(member, ArMember) and m.name == member.name:
					return m
			if member == m.name:
				return m

		return None 

class ArMember(object):
    # XXX trying to mimick the interface of TarInfo in the standard library

    def __init__(self):
        self.__name = None      # member name (i.e. filename) in the archive
        self.__mtime = None 
        self.__owner = None 
        self.__group = None 
        self.__mode  = None 
        self.__size  = None     # member size in bytes
        self.__fname = None     # file name associated with this member
        self.__fp    = None     # XXX serve globale?
        self.__offset = None    # start-of-data offset
        pass    # TODO

    def _from_file(fp, fname):
        """fp is an open File object positioned to a valid file header or global header.
        Returns a new ArMember on success"""

        buf = fp.read(FILE_HEADER_LENGTH)

        if not buf:
            return False

# XXX testare
        # fp is an ar archive start
#		if buf[0:GLOBAL_HEADER_LENGTH] == GLOBAL_HEADER:
#			buf = buf[GLOBAL_HEADER_LENGTH:] + fp.read(GLOBAL_HEADER_LENGTH)

        # sanity checks
        if len(buf) < FILE_HEADER_LENGTH:
            raise IOError

        if buf[58:60] != FILE_MAGIC:
            raise IOError

# http://en.wikipedia.org/wiki/Ar_(Unix)	
#from   to 	Name 	   				 	Format
#0    	15 	File name 					ASCII
#16 	27 	File modification date 		Decimal
#28 	33 	Owner ID 					Decimal
#34 	39 	Group ID 					Decimal
#40 	47 	File mode 					Octal
#48 	57 	File size in bytes 			Decimal
#58 	59 	File magic 					\140\012

# XXX struct.unpack can be used as well here
        f = ArMember()
        f.__name = buf[0:16].split("/")[0]
        f.__mtime = int(buf[16:28])
        f.__owner = int(buf[28:34])
        f.__group = int(buf[34:40])
        f.__mode  = buf[40:48]  # XXX e' un ottale
        f.__size  = int(buf[48:58])

        f.__fname = fname
        f.__offset = fp.tell() # start-of-data

        return f

    from_file = staticmethod(_from_file)
    
# file interface
# XXX this is not a sequence like file objects
    def read(self, size=0):
        if self.__fp is None:
            self.__fp = open(self.__fname, "r")
            self.__fp.seek(self.__offset)

        end = self.__offset + self.__size
        cur = self.__fp.tell()

        if size > 0 and size <= end - cur: # there's room
            return self.__fp.read(size)

        if cur >= end:
            return ''

        return self.__fp.read(end - cur)

# XXX check corner cases for readline(s)
    def readline(self, size=None):
        if self.__fp is None:
            self.__fp = open(self.__fname, "r")
            self.__fp.seek(self.__offset)

        end = self.__offset + self.__size

        if size is not None: 
            buf = self.__fp.readline(size)
            if self.__fp.tell() > end:
                return ''

            return buf

        buf = self.__fp.readline()
        if self.__fp.tell() > end:
            return ''

        return buf

    def next(self):
        return self.readline()

    def readlines(self, sizehint=0):
        if self.__fp is None:
            self.__fp = open(self.__fname, "r")
            self.__fp.seek(self.__offset)
        
        buf = None
        lines = []
        while not buf == '':
            buf = self.readline()
            lines.append(buf)

        return lines

    def seek(self, offset, whence=0):
        if offset < 0:
            raise IOError

        if self.__fp is None:
            self.__fp = open(self.__fname, "r")

        end = self.__offset + self.__size
        cur = self.__fp.tell()

        if whence == 0: # absolute
            if self.__offset + offset > end: # out-of-bounds
                self.__fp.seek(end)
            else:
                self.__fp.seek(self.__offset + offset, 0)
        elif whence == 1: # relative
            if cur + offset > end: # out-of-bounds
                self.__fp.seek(end)
            else:
                self.__fp.seek(offset, 1)
        elif whence == 2: # relative to EOF
            self.__fp.seek(end)

    def tell(self):
        if self.__fp is None:
            self.__fp = open(self.__fname, "r")
            self.__fp.seek(self.__offset)

        return self.__fp.tell() - self.__offset

    def close(self):
        if self.__fp is not None:
            self.__fp.close()
   
    def __iter__(self):
        def nextline():
            line = self.readline()
            if line:
                yield line

        return iter(nextline())

    def getoffset(self): return self.__offset
    offset = property(getoffset)

    def getname(self): return self.__name
    name = property(getname)

    def getmtime(self): return self.__mtime
    mtime = property(getmtime)

    def getowner(self): return self.__owner
    owner = property(getowner)

    def getgroup(self): return self.__group
    group = property(getgroup)

    def getmode(self): return self.__mode
    mode = property(getmode)

    def getsize(self): return self.__size
    size = property(getsize)


    # ALTRE PROP da aggiungere: mtime, mode, ...

    def tobuf():
        pass    # TODO

	def tofile(self):
		return self

#    FINQUI

if __name__ == '__main__':
# test
# ar r test.ar <file1> <file2> .. <fileN>
    t = ArFile("test.ar")
    print t.getmembers()
    print t.getnames()
    a = t.getmember("gettimeofday.c")
    print a.readline()
    print a.readline()
    print a.readline()
# vim:et:ts=4
