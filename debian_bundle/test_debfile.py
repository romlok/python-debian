#! /usr/bin/python

import arfile 
import unittest
import os

class TestArFile(unittest.TestCase):
#    def setUp(self):
    def setUp(self):
        os.system("ar r test.ar test_debfile.py arfile.py debfile.py") 
        assert os.path.exists("test.ar")
        self.testmembers = [x.strip() for x in os.popen("ar t test.ar").readlines()]
        a = arfile.ArFile("test.ar")
    
    def test_getnames(self):
        a = arfile.ArFile("test.ar")
        self.assertEqual(a.getnames(), self.testmembers)

    def test_getmember(self):
        a = arfile.ArFile("test.ar")
        from stat import * 

        for member in self.testmembers:
            m = a.getmember(member)
            assert m
            self.assertEqual(m.name, member)
            
            mstat = os.stat(member)

            self.assertEqual(m.size, mstat[ST_SIZE])
            self.assertEqual(m.owner, mstat[ST_UID])
            self.assertEqual(m.group, mstat[ST_GID])

    #def mkdb(self):
        #db = debtags.DB()
        #db.read(open("test_tagdb", "r"))
        #return db

    #def test_insert(self):
        #db = debtags.DB()
        #db.insert("test", set(("a", "b")));
        #assert db.hasPackage("test")
        #assert not db.hasPackage("a")
        #assert not db.hasPackage("b")
        #assert db.hasTag("a")
        #assert db.hasTag("b")
        #assert not db.hasTag("test")
        #self.assertEqual(db.tagsOfPackage("test"), set(("a", "b")))
        #self.assertEqual(db.packagesOfTag("a"), set(("test")))
        #self.assertEqual(db.packagesOfTag("b"), set(("test")))
        #self.assertEqual(db.packageCount(), 1)
        #self.assertEqual(db.tagCount(), 2)

    #def test_reverse(self):
        #db = debtags.DB()
        #db.insert("test", set(("a", "b")));
        #db = db.reverse()
        #assert db.hasPackage("a")
        #assert db.hasPackage("b")
        #assert not db.hasPackage("test")
        #assert db.hasTag("test")
        #assert not db.hasTag("a")
        #assert not db.hasTag("b")
        #self.assertEqual(db.packagesOfTag("test"), set(("a", "b")))
        #self.assertEqual(db.tagsOfPackage("a"), set(("test")))
        #self.assertEqual(db.tagsOfPackage("b"), set(("test")))
        #self.assertEqual(db.packageCount(), 2)
        #self.assertEqual(db.tagCount(), 1)

    #def test_read(self):
        #db = self.mkdb()
        #self.assertEqual(db.tagsOfPackage("polygen"), set(("devel::interpreter", "game::toys", "interface::commandline", "works-with::text")))
        #assert "polygen" in db.packagesOfTag("interface::commandline")
        #self.assertEqual(db.packageCount(), 144)
        #self.assertEqual(db.tagCount(), 94)

if __name__ == '__main__':
    unittest.main()

# vim:set ts=4 sw=4 expandtab:
