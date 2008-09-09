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

import unittest
import os
import re
import stat
import sys
import tempfile
import uu

sys.path.insert(0, '../debian_bundle/')

import arfile
import debfile

class TestArFile(unittest.TestCase):

    def setUp(self):
        os.system("ar r test.ar test_debfile.py test_changelog test_deb822.py >/dev/null 2>&1") 
        assert os.path.exists("test.ar")
        self.testmembers = [ x.strip()
                for x in os.popen("ar t test.ar").readlines() ]
        self.a = arfile.ArFile("test.ar")

    def tearDown(self):
        if os.path.exists('test.ar'):
            os.unlink('test.ar')
    
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

            self.assertEqual(m.size, mstat[stat.ST_SIZE])
            self.assertEqual(m.owner, mstat[stat.ST_UID])
            self.assertEqual(m.group, mstat[stat.ST_GID])

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
        def uudecode(infile, outfile):
            uu_deb = open(infile, 'r')
            bin_deb = open(outfile, 'w')
            uu.decode(uu_deb, bin_deb)
            uu_deb.close()
            bin_deb.close()

        self.debname = 'test.deb'
        self.broken_debname = 'test-broken.deb'
        self.bz2_debname = 'test-bz2.deb'
        uudecode('test.deb.uu', self.debname)
        uudecode('test-broken.deb.uu', self.broken_debname)
        uudecode('test-bz2.deb.uu', self.bz2_debname)

        self.debname = 'test.deb'
        uu_deb = open('test.deb.uu', 'r')
        bin_deb = open(self.debname, 'w')
        uu.decode(uu_deb, bin_deb)
        uu_deb.close()
        bin_deb.close()
        self.d = debfile.DebFile(self.debname)

    def tearDown(self):
        os.unlink(self.debname)
        os.unlink(self.broken_debname)
        os.unlink(self.bz2_debname)

    def test_missing_members(self):
        self.assertRaises(debfile.DebError,
                lambda _: debfile.DebFile(self.broken_debname), None)

    def test_tar_bz2(self):
        bz2_deb = debfile.DebFile(self.bz2_debname)
        # random test on the data part (which is bzipped), just to check if we
        # can access its content
        self.assertEqual(bz2_deb.data.tgz().getnames()[10],
                './usr/share/locale/bg/')

    def test_data_names(self):
        """ test for file list equality """ 
        strip_dot_slash = lambda s: re.sub(r'^\./', '', s)
        tgz = self.d.data.tgz()
        dpkg_names = map(strip_dot_slash,
                [ x.strip() for x in
                    os.popen("dpkg-deb --fsys-tarfile %s | tar t" %
                        self.debname).readlines() ])
        debfile_names = map(strip_dot_slash, tgz.getnames())
        
        # skip the root
        self.assertEqual(debfile_names[1:], dpkg_names[1:])

    def test_control(self):
        """ test for control equality """
        filecontrol = "".join(os.popen("dpkg-deb -f %s" %
            self.debname).readlines())

        self.assertEqual(self.d.control.get_content("control"), filecontrol)

    def test_md5sums(self):
        """test md5 extraction from .debs"""
        md5 = self.d.md5sums()
        self.assertEqual(md5['usr/bin/hello'],
                '9c1a72a78f82216a0305b6c90ab71058')
        self.assertEqual(md5['usr/share/locale/zh_TW/LC_MESSAGES/hello.mo'],
                'a7356e05bd420872d03cd3f5369de42f')

if __name__ == '__main__':
    unittest.main()

