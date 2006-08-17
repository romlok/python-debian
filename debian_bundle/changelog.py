# changelog.py -- Python module for Debian changelogs
# Copyright (C) 2006 James Westby <jw+debian@jameswestby.net>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""This module implements facilities to deal with Debian changelogs."""

import os
import re
import unittest

class ChangelogError(StandardError):

  is_user_error = True

  def __init__(self, line):
    self._line=line

  def __str__(self):
    return "Could not parse changelog: "+self._line

class VersionError(StandardError):

  is_user_error = True

  def __init__(self, version):
    self._version=version

  def __str__(self):
    return "Could not parse version: "+self._version

class Version(object):
  """Represents a version of a Debian package."""

  def __init__(self, version):
    
    self._full_version=version
    p = re.compile(r'^(?:(\d+):)?([A-Za-z0-9.+:~-]+?)'
                   + r'(?:-([A-Za-z0-9.~+]+))?$')
    m = p.match(version)
    if m is None:
      raise VersionError(version)
    (epoch, upstream, debian) = m.groups()
    self._epoch = epoch
    self._upstream = upstream
    self._debian = debian
  
  def full_version(self):
    return self._full_version

  def epoch(self):
    return self._epoch

  def upstream_version(self):
    return self._upstream

  def debian_version(self):
    return self._debian

  __str__ = full_version

class ChangeBlock(object):
  """Holds all the information about one block from the changelog."""

  def __init__(self, package, version, distributions, urgency, changes,
                author, date):
    self._version = version
    self._package = package
    self._distributions = distributions
    self._urgency = urgency
    self._changes = changes
    self._author = author
    self._date = date
    self._trailing = 0

  def package(self):
    return self._package

  def version(self):
    return self._version

  def distributions(self):
    return self._distributions

  def urgency(self):
    return self._urgency

  def changes(self):
    return self._changes

  def author(self):
    return self._author

  def date(self):
    return self._date

  def add_trailing_newline(self):
    self._trailing += 1

  def __str__(self):
    block = ""
    block += self.package() + " "
    block += "(" + str(self.version()) + ") "
    block += self.distributions() + "; "
    block += "urgency=" + self.urgency() + "\n"
    for change in self.changes():
      block += change + "\n"
    block += " -- " + self.author() + "  " + self.date() + "\n"
    for i in range(self._trailing):
      block += "\n"
    return block

topline = re.compile('^([a-z0-9][-a-z0-9.+]+) \(([-0-9a-z.:~+]+)\) '
      +'([-a-zA-Z ]+); urgency=([a-z]+)')
blankline = re.compile('^[ \t]*$')
change = re.compile('^[ ][ ]+.*$')
endline = re.compile('^ -- (.*)  (\w\w\w, [ \d]\d \w\w\w \d\d\d\d '+
      '\d\d:\d\d:\d\d \+\d\d\d\d( \(.*\))?)$')

class Changelog(object):
  """Represents a debian/changelog file. You can ask it several things about
  the file."""


  def __init__(self, file=None):
    """Set up the Changelog for use. file is the contects of the changelog.
    If it is None, then the module will attempt to open 'debian/changelog'
    and use it's contents.
    """
    
    self._blocks = []
    before = 1
    inblock = 2

    package = None
    version = None
    distributions = None
    urgency = None
    changes = []
    author = None
    date = None

    if file is None:
      f = open(os.path.join("debian","changelog"), 'r')
      contents = f.read()
      f.close()
      self._file = contents
    else:
      self._file = file
    state = before
    for line in self._file.split('\n'):
      if state == before:
        m = topline.match(line)
        if m is not None:
          state = inblock
          package = m.group(1)
          version = Version(m.group(2))
          distributions = m.group(3)
          urgency = m.group(4)
        else:
          m = blankline.match(line)
          if m is None:
            raise ChangelogError(line)
          elif len(self._blocks) > 0:
            self._blocks[-1].add_trailing_newline()
      elif state == inblock:
        m = blankline.match(line)
        if m is not None:
          changes.append(line)
        else:
          m = endline.match(line)
          if m is not None:
            state = before
            author = m.group(1)
            date = m.group(2)
            block = ChangeBlock(package, version, distributions, urgency,
                changes, author, date)
            self._blocks.append(block)
            (package, version, distributions, urgency, author, date) = \
                (None, None, None, None, None, None)
            changes = []
          else:
            m = change.match(line)
            if m is None:
              raise ChangelogError(line)
            #TODO: maybe try and parse these more intelligently
            changes.append(line)
      else:
        assert(False), "Unknown state: "+state


    if state == inblock:
      raise ChangelogError("Unexpected EOF")

  def full_version(self):
    """Returns the full version number of the last version."""
    return self._blocks[0].version().full_version()

  def debian_version(self):
    """Returns the debian part of the version number of the last version. 
    Will be None if it is a native package"""
    return self._blocks[0].version().debian_version()

  def upstream_version(self):
    """Returns the upstream part of the version number of the last version"""
    return self._blocks[0].version().upstream_version()

  def epoch(self):
    """Returns the epoch number of the last revision, or None if no epoch was
    used"""
    return self.blocks[0].version().epoch()

  def package(self):
    """Returns the name of the package in the last version."""
    return self.blocks[0].package()

  def versions(self):
    """Returns a list of version objects that the package went through."""
    versions = []
    for block in self._blocks:
      versions.append[block.version()]
    return versions

  def __str__(self):
    cl = ""
    for block in self._blocks:
      cl += str(block)
    return cl

def _test():
  import doctest
  doctest.testmod()

  unittest.main()

class ChangelogTests(unittest.TestCase):

  def testchangelog(self):

    c = open('test_changelog').read()
    cl = Changelog(c)
    cs = str(cl)
    clines = c.split('\n')
    cslines = cs.split('\n')
    for i in range(len(clines)):
      self.assertEqual(clines[i], cslines[i])

class VersionTests(unittest.TestCase):

  def _test_version(self, full_version, epoch, upstream, debian):
    v = Version(full_version)
    self.assertEqual(v.full_version(), full_version, "Full version broken")
    self.assertEqual(v.epoch(), epoch, "Epoch broken")
    self.assertEqual(v.upstream_version(), upstream, "Upstram broken")
    self.assertEqual(v.debian_version(), debian, "Debian broken")

  def testversions(self):
    self._test_version('1:1.4.1-1', '1', '1.4.1', '1')
    self._test_version('7.1.ds-1', None, '7.1.ds', '1')
    self._test_version('10.11.1.3-2', None, '10.11.1.3', '2')
    self._test_version('4.0.1.3.dfsg.1-2', None, '4.0.1.3.dfsg.1', '2')
    self._test_version('0.4.23debian1', None, '0.4.23debian1', None)
    self._test_version('1.2.10+cvs20060429-1', None, '1.2.10+cvs20060429', '1')
    self._test_version('0.2.0-1+b1', None, '0.2.0', '1+b1')
    self._test_version('4.3.90.1svn-r21976-1', None, '4.3.90.1svn-r21976', '1')
    self._test_version('1.5+E-14', None, '1.5+E', '14')
    self._test_version('20060611-0.0', None, '20060611', '0.0')
    self._test_version('0.52.2-5.1', None, '0.52.2', '5.1')
    self._test_version('7.0-035+1', None, '7.0', '035+1')
    self._test_version('1.1.0+cvs20060620-1+2.6.15-8', None, 
        '1.1.0+cvs20060620-1+2.6.15', '8')
    self._test_version('1.1.0+cvs20060620-1+1.0', None, '1.1.0+cvs20060620', '1+1.0')
    self._test_version('4.2.0a+stable-2sarge1', None, '4.2.0a+stable', '2sarge1')
    self._test_version('1.8RC4b', None, '1.8RC4b', None)
    self._test_version('0.9~rc1-1', None, '0.9~rc1', '1')


if __name__ == "__main__":
  _test()

