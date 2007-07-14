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

    def test_file_seek(self):
        a = arfile.ArFile("test.ar")
        m = a.getmember(self.testmembers[0])

        for i in [10,100,10000,100000]:
            m.seek(i, 0)
            self.assertEqual(m.tell(), i, "failed tell()")
            
            m.seek(-i, 1)
            self.assertEqual(m.tell(), 0L, "failed tell()")

        m.seek(0)
        self.assertRaises(IOError, m.seek, -1, 0)
        self.assertRaises(IOError, m.seek, -1, 1)
        m.seek(0)
    
    def test_file_read(self):
        a = arfile.ArFile("test.ar")
        m = a.getmember(self.testmembers[0])
        f = open(self.testmembers[0])
        
        #self.assertEqual(m.readlines(), f.readlines())
       
        for i in [10, 100, 10000]:
            self.assertEqual(m.read(i), f.read(i))
        
        f.close()

if __name__ == '__main__':
    unittest.main()

# vim:set ts=4 sw=4 expandtab:
