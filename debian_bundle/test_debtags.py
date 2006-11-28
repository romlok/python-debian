#! /usr/bin/python
## vim: fileencoding=utf-8

# Copyright (C) 2006 Enrico Zini <enrico@enricozini.org>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# dated June, 1991.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import debtags
import unittest

class TestDebtags(unittest.TestCase):
    def mkdb(self):
        db = debtags.DB()
        db.read(open("test_tagdb", "r"))
        return db

    def test_insert(self):
        db = debtags.DB()
        db.insert("test", set(("a", "b")));
        assert db.hasPackage("test")
        assert not db.hasPackage("a")
        assert not db.hasPackage("b")
        assert db.hasTag("a")
        assert db.hasTag("b")
        assert not db.hasTag("test")
        self.assertEqual(db.tagsOfPackage("test"), set(("a", "b")))
        self.assertEqual(db.packagesOfTag("a"), set(("test")))
        self.assertEqual(db.packagesOfTag("b"), set(("test")))
        self.assertEqual(db.packageCount(), 1)
        self.assertEqual(db.tagCount(), 2)

    def test_reverse(self):
        db = debtags.DB()
        db.insert("test", set(("a", "b")));
        db = db.reverse()
        assert db.hasPackage("a")
        assert db.hasPackage("b")
        assert not db.hasPackage("test")
        assert db.hasTag("test")
        assert not db.hasTag("a")
        assert not db.hasTag("b")
        self.assertEqual(db.packagesOfTag("test"), set(("a", "b")))
        self.assertEqual(db.tagsOfPackage("a"), set(("test")))
        self.assertEqual(db.tagsOfPackage("b"), set(("test")))
        self.assertEqual(db.packageCount(), 2)
        self.assertEqual(db.tagCount(), 1)

    def test_read(self):
        db = self.mkdb()
        self.assertEqual(db.tagsOfPackage("polygen"), set(("devel::interpreter", "game::toys", "interface::commandline", "works-with::text")))
        assert "polygen" in db.packagesOfTag("interface::commandline")
        self.assertEqual(db.packageCount(), 144)
        self.assertEqual(db.tagCount(), 94)

if __name__ == '__main__':
    unittest.main()

# vim:set ts=4 sw=4 expandtab:
