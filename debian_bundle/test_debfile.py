#! /usr/bin/python

# Tests for ArFile/DebFile
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

import arfile 
import debfile
import unittest
import os, sys

from stat import * 

deb_testfile = None

class TestArFile(unittest.TestCase):

    def setUp(self):
        os.system("ar r test.ar test_debfile.py arfile.py debfile.py") 
        assert os.path.exists("test.ar")
        self.testmembers = [ x.strip()
                for x in os.popen("ar t test.ar").readlines() ]
        self.a = arfile.ArFile("test.ar")
    
    def test_getnames(self):
        """ test for file list equality """
        self.assertEqual(self.a.getnames(), self.testmembers)

    def test_getmember(self):
        """ test for each member equality """
        for member in self.testmembers:
            m = self.a.getmember(member)
            assert m
            self.assertEqual(m.name, member)
            
            mstat = os.stat(member)

            self.assertEqual(m.size, mstat[ST_SIZE])
            self.assertEqual(m.owner, mstat[ST_UID])
            self.assertEqual(m.group, mstat[ST_GID])

    def test_file_seek(self):
        """ test for faked seek """
        m = self.a.getmember(self.testmembers[0])

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
        """ test for faked read """
        for m in self.a.getmembers():
            f = open(m.name)
        
            for i in [10, 100, 10000]:
                self.assertEqual(m.read(i), f.read(i))
       
            m.close()
            f.close()

    def test_file_readlines(self):
        """ test for faked readlines """

        for m in self.a.getmembers():
            f = open(m.name)
        
            self.assertEqual(m.readlines(), f.readlines())
            
            m.close()
            f.close()

class TestDebFile(unittest.TestCase):
    def setUp(self):
        self.d = debfile.DebFile(deb_testfile)

    def test_data_names(self):
        """ test for file list equality """ 
        tgz = self.d.data.tgz()
        filelist = [ x.strip()[2:] # remove "./"
                for x in
                os.popen("dpkg-deb --fsys-tarfile %s | tar t" % deb_testfile).readlines() ]
        
        # skip the root
        self.assertEqual(tgz.getnames()[1:], filelist[1:])

    def test_control(self):
        """ test for control equality """
        filecontrol = "".join(os.popen("dpkg-deb -f %s" % deb_testfile).readlines())

        self.assertEqual(self.d.control.get_content("control"), filecontrol)

if __name__ == '__main__':
    debfileSuite = [ unittest.TestLoader().loadTestsFromTestCase(TestArFile) ]
    
    if os.path.exists("hello_2.2-2_powerpc.deb"):
        deb_testfile = "hello_2.2-2_powerpc.deb"
    
    if len(sys.argv) > 1:
        deb_testfile = sys.argv[1]

    if deb_testfile:
        debfileSuite.append( unittest.TestLoader().loadTestsFromTestCase(TestDebFile) ) 
    
    unittest.TextTestRunner(verbosity=2).run(unittest.TestSuite(debfileSuite))
