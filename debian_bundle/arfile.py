#!/usr/bin/python

GLOBAL_HEADER = "!<arch>\n"
GLOBAL_HEADER_LENGTH = 8

FILE_HEADER_LENGTH = 60
FILE_MAGIC = "`\n"

class ArFile(object):
# XXX trying to mimick the interface of TarFile in the standard library

    def __init__(self, fname, mode="r"):
# FIXME i membri possono avere anche lo stesso nome! meglio una lista di Member 
        self.__members = {}   # dict: member name -> File object
        self.__members_list = None
        self.__fname = fname
		
        if mode == "r":
            self.__index_archive()
        pass    # TODO

    def __index_archive(self):
        fp = open(self.__fname, "rb")

        if fp.read(GLOBAL_HEADER_LENGTH) != GLOBAL_HEADER:
            raise IOError

        while True:
            newmember = Member.from_file(fp, self.__fname)
            if not newmember:
                break
            self.__members.update( {newmember.getname() : newmember} )
            fp.seek(newmember.getsize(), 1) # skip to next header

        self.__updateMembersList() # XXX serve a qualcosa? 
        fp.close()



    def getmember(self, name):
        return self.__members[name]

    def __updateMembersList(self):
        if self.__members_list is None:
            self.__members_list = self.__members.values()
            self.__members_list.sort(lambda f1, f2: cmp(f1.seqno, f2.seqno))

    def getmembers(self):
        self.__updateMembersList()
        return self.__members_list

    def getnames(self):
        self.__updateMembersList()
        return map(lambda f: f.name, self.__members_list)

    def next():
        pass    # TODO

    def extractall():
        pass    # TODO

    def extract(self, member, path):
        pass    # TODO

    def extractfile(self, member):
        pass    # TODO

class Member(object):
    # XXX trying to mimick the interface of TarInfo in the standard library

    def __init__(self):
        self.__seqno = None     # sequential number in the archive
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
        Returns a new Member on success"""

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

        f = Member()
        f.__name = buf[0:16].split("/")[0]
        f.__mtime = int(buf[16:28])
        f.__owner = int(buf[28:34])
        f.__group = int(buf[34:40])
        f.__mode  = buf[40:48]  # XXX e' un ottale
        f.__size  = int(buf[48:58])
# XXX seqno a cosa serve? se e' solo per ordinarli si puo' usare l'offset

        f.__fname = fname
        f.__offset = fp.tell() # start-of-data

        return f

    from_file = staticmethod(_from_file) # o class method?

    def getseqno(self): return self.__seqno
    seqno = property(getseqno)

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

#    FINQUI

if __name__ == '__main__':
# test
# ar r test.ar <file1> <file2> .. <fileN>
	t = ArFile("test.ar")
	print t.getmembers()
	print t.getnames()


# vim:et:ts=4
