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

class ChangelogParseError(StandardError):
  """Indicates that the changelog could not be parsed"""
  is_user_error = True

  def __init__(self, line):
    self._line=line

  def __str__(self):
    return "Could not parse changelog: "+self._line

class ChangelogCreateError(StandardError):
  """Indicates that changelog could not be created, as all the information
  required was not given"""

class VersionError(StandardError):
  """Indicates that the version does not conform to the required format"""

  is_user_error = True

  def __init__(self, version):
    self._version=version

  def __str__(self):
    return "Could not parse version: "+self._version

class Version(object):
  """Represents a version of a Debian package."""

  def __init__(self, version):
    
    self.full_version = version
    p = re.compile(r'^(?:(\d+):)?([A-Za-z0-9.+:~-]+?)'
                   + r'(?:-([A-Za-z0-9.~+]+))?$')
    m = p.match(version)
    if m is None:
      raise VersionError(version)
    (epoch, upstream, debian) = m.groups()
    self.epoch = epoch
    self.upstream_version = upstream
    self.debian_version = debian

  def __str__(self):
    return self.full_version

class ChangeBlock(object):
  """Holds all the information about one block from the changelog."""

  def __init__(self, package=None, version=None, distributions=None, 
                urgency=None, changes=None, author=None, date=None):
    self.version = version
    self.package = package
    self.distributions = distributions
    self.urgency = urgency
    self._changes = changes
    self.author = author
    self.date = date
    self._trailing = 0

  def changes(self):
    return self._changes

  def add_trailing_newline(self):
    self._trailing += 1

  def del_trailing_newline(self):
    self._trailing -= 1

  def add_change(self, change):
    if self._changes is None:
      self._changes = [change]
    else:
#Bit of trickery to keep the formatting nicer with a blank line at the end if there is one
      changes = self._changes
      changes.reverse()
      added = False
      for i in range(len(changes)):
        m = blankline.match(changes[i])
        if m is None:
          changes.insert(i, change)
          added = True
          break
      changes.reverse()
      if not added:
        changes.append(change)
      self._changes = changes

  def __str__(self):
    block = ""
    if self.package is None:
      raise ChangelogCreateError("Package not specified")
    block += self.package + " "
    if self.version is None:
      raise ChangelogCreateError("Version not specified")
    block += "(" + str(self.version) + ") "
    if self.distributions is None:
      raise ChangelogCreateError("Distribution not specified")
    block += self.distributions + "; "
    if self.urgency is None:
      raise ChangelogCreateError("Urgency not specified")
    block += "urgency=" + self.urgency + "\n"
    if self.changes() is None:
      raise ChangelogCreateError("Changes not specified")
    for change in self.changes():
      block += change + "\n"
    if self.author is None:
      raise ChangelogCreateError("Author not specified")
    if self.date is None:
      raise ChangelogCreateError("Date not specified")
    block += " -- " + self.author + "  " + self.date + "\n"
    if self._trailing > 0:
      for i in range(self._trailing):
        block += "\n"
    return block

topline = re.compile('^([a-z0-9][-a-z0-9.+]+) \(([-0-9a-z.:~+]+)\) '
      +'([-a-zA-Z ]+); urgency=([a-z]+)')
blankline = re.compile('^[ \t]*$')
change = re.compile('^[ ][ ]+.*$')
endline = re.compile('^ -- (.*)  (\w\w\w, [ \d]\d \w\w\w \d\d\d\d '+
      '\d\d:\d\d:\d\d [-+]\d\d\d\d( \(.*\))?)$')

class Changelog(object):
  """Represents a debian/changelog file. You can ask it several things about
  the file."""


  def __init__(self, file=None):
    """Set up the Changelog for use. file is the contects of the changelog.
    """
    
    self._blocks = []
    if file is not None:
      before = 1
      inblock = 2

      package = None
      version = None
      distributions = None
      urgency = None
      changes = []
      author = None
      date = None

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
              raise ChangelogParseError(line)
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
                raise ChangelogParseError(line)
              #TODO: maybe try and parse these more intelligently
              changes.append(line)
        else:
          assert(False), "Unknown state: "+state


      if state == inblock:
        raise ChangelogParseError("Unexpected EOF")

      #TODO: shouldn't be required should it?
      self._blocks[-1].del_trailing_newline()

  def full_version(self):
    """Returns the full version number of the last version."""
    return self._blocks[0].version.full_version

  def debian_version(self):
    """Returns the debian part of the version number of the last version. 
    Will be None if it is a native package"""
    return self._blocks[0].version.debian_version

  def upstream_version(self):
    """Returns the upstream part of the version number of the last version"""
    return self._blocks[0].version.upstream_version

  def epoch(self):
    """Returns the epoch number of the last revision, or None if no epoch was
    used"""
    return self._blocks[0].version.epoch

  def package(self):
    """Returns the name of the package in the last version."""
    return self._blocks[0].package

  def versions(self):
    """Returns a list of version objects that the package went through."""
    versions = []
    for block in self._blocks:
      versions.append[block.version]
    return versions

  def __str__(self):
    cl = ""
    for block in self._blocks:
      cl += str(block)
    return cl

  def set_package(self, package):
    self._blocks[0].package = package

  def set_version(self, version):
    self._blocks[0].version = version

  def set_distributions(self, distributions):
    self._blocks[0].distributions = distributions

  def set_urgency(self, urgency):
    self._blocks[0].urgency = urgency

  def add_change(self, change):
    self._blocks[0].add_change(change)

  def set_author(self, author):
    self._blocks[0].author = author

  def set_date(self, date):
    self._blocks[0].date = date

  def new_block(self, package=None, version=None, distributions=None,
                urgency=None, changes=None, author=None, date=None):
    block = ChangeBlock(package, version, distributions, urgency,
                        changes, author, date)
    block.add_trailing_newline()
    self._blocks.insert(0, block)

def _test():
  import doctest
  doctest.testmod()

  unittest.main()

class ChangelogTests(unittest.TestCase):

  def test_create_changelog(self):

    c = open('test_changelog').read()
    cl = Changelog(c)
    cs = str(cl)
    clines = c.split('\n')
    cslines = cs.split('\n')
    for i in range(len(clines)):
      self.assertEqual(clines[i], cslines[i])
    self.assertEqual(len(clines), len(cslines), "Different lengths")

  def test_modify_changelog(self):

    c = open('test_modify_changelog1').read()
    cl = Changelog(c)
    cl.set_package('gnutls14')
    cl.set_version(Version('1:1.4.1-2'))
    cl.set_distributions('experimental')
    cl.set_urgency('medium')
    cl.add_change('  * Add magic foo')
    cl.set_author('James Westby <jw+debian@jameswestby.net>')
    cl.set_date('Sat, 16 Jul 2008 11:11:08 -0200')
    c = open('test_modify_changelog2').read()
    clines = c.split('\n')
    cslines = str(cl).split('\n')
    for i in range(len(clines)):
      self.assertEqual(clines[i], cslines[i])
    self.assertEqual(len(clines), len(cslines), "Different lengths")

  def test_add_changelog_section(self):
    c = open('test_modify_changelog2').read()
    cl = Changelog(c)
    cl.new_block('gnutls14', Version('1:1.4.1-3'), 'experimental', 'low',
                    None, 'James Westby <jw+debian@jameswestby.net>')

    self.assertRaises(ChangelogCreateError, cl.__str__)

    cl.set_date('Sat, 16 Jul 2008 11:11:08 +0200')
    cl.add_change('')
    cl.add_change('  * Foo did not work, let us try bar')
    cl.add_change('')

    c = open('test_modify_changelog3').read()
    clines = c.split('\n')
    cslines = str(cl).split('\n')
    for i in range(len(clines)):
      self.assertEqual(clines[i], cslines[i])
    self.assertEqual(len(clines), len(cslines), "Different lengths")

class VersionTests(unittest.TestCase):

  def _test_version(self, full_version, epoch, upstream, debian):
    v = Version(full_version)
    self.assertEqual(v.full_version, full_version, "Full version broken")
    self.assertEqual(v.epoch, epoch, "Epoch broken")
    self.assertEqual(v.upstream_version, upstream, "Upstram broken")
    self.assertEqual(v.debian_version, debian, "Debian broken")

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

