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
import unittest
import os

from stat import * 

class TestArFile(unittest.TestCase):

    def setUp(self):
        os.system("ar r test.ar test_debfile.py arfile.py debfile.py") 
        assert os.path.exists("test.ar")
        self.testmembers = [ x.strip()
                for x in os.popen("ar t test.ar").readlines() ]
        a = arfile.ArFile("test.ar")
    
    def test_getnames(self):
        a = arfile.ArFile("test.ar")
        self.assertEqual(a.getnames(), self.testmembers)

    def test_getmember(self):
        a = arfile.ArFile("test.ar")

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

