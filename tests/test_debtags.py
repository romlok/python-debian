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

import sys
import unittest

sys.path.insert(0, '../debian_bundle/')
import debtags

class TestDebtags(unittest.TestCase):
    def mkdb(self):
        db = debtags.DB()
        db.read(open("test_tagdb", "r"))
        return db

    def test_insert(self):
        db = debtags.DB()
        db.insert("test", set(("a", "b")));
        assert db.has_package("test")
        assert not db.has_package("a")
        assert not db.has_package("b")
        assert db.has_tag("a")
        assert db.has_tag("b")
        assert not db.has_tag("test")
        self.assertEqual(db.tags_of_package("test"), set(("a", "b")))
        self.assertEqual(db.packages_of_tag("a"), set(("test")))
        self.assertEqual(db.packages_of_tag("b"), set(("test")))
        self.assertEqual(db.package_count(), 1)
        self.assertEqual(db.tag_count(), 2)

    def test_reverse(self):
        db = debtags.DB()
        db.insert("test", set(("a", "b")));
        db = db.reverse()
        assert db.has_package("a")
        assert db.has_package("b")
        assert not db.has_package("test")
        assert db.has_tag("test")
        assert not db.has_tag("a")
        assert not db.has_tag("b")
        self.assertEqual(db.packages_of_tag("test"), set(("a", "b")))
        self.assertEqual(db.tags_of_package("a"), set(("test")))
        self.assertEqual(db.tags_of_package("b"), set(("test")))
        self.assertEqual(db.package_count(), 2)
        self.assertEqual(db.tag_count(), 1)

    def test_read(self):
        db = self.mkdb()
        self.assertEqual(db.tags_of_package("polygen"), set(("devel::interpreter", "game::toys", "interface::commandline", "works-with::text")))
        assert "polygen" in db.packages_of_tag("interface::commandline")
        self.assertEqual(db.package_count(), 144)
        self.assertEqual(db.tag_count(), 94)

if __name__ == '__main__':
    unittest.main()

# vim:set ts=4 sw=4 expandtab:
