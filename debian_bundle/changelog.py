# changelog.py -- Python module for Debian changelogs
# Copyright (C) 2006-7 James Westby <jw+debian@jameswestby.net>
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

import debian_support

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

class Version(debian_support.Version, object):
  """Represents a version of a Debian package."""
  # Subclassing debian_support.Version for its rich comparison

  def __init__(self, version):
    version = str(version)
    debian_support.Version.__init__(self, version)

    self.full_version = version

  def __setattr__(self, attr, value):
    """Update all the attributes, given a particular piece of the version

    Allowable values for attr, hopefully self-explanatory:
      full_version
      epoch
      upstream_version
      debian_version

    Any attribute starting with __ is given to object's __setattr__ method.
    """

    attrs = ('full_version', 'epoch', 'upstream_version', 'debian_version')

    if attr.startswith('_Version__'):
      object.__setattr__(self, attr, value)
      return
    elif attr not in attrs:
      raise AttributeError("Cannot assign to attribute " + attr)

    if attr == 'full_version':
      version = value
      p = re.compile(r'^(?:(?P<epoch>\d+):)?'
                     + r'(?P<upstream_version>[A-Za-z0-9.+:~-]+?)'
                     + r'(?:-(?P<debian_version>[A-Za-z0-9.~+]+))?$')
      m = p.match(version)
      if m is None:
        raise VersionError(version)
      for key, value in m.groupdict().items():
        object.__setattr__(self, key, value)
      self.__asString = version
    
    else:
      # Construct a full version from what was given and pass it back here
      d = {}
      for a in attrs[1:]:
        if a == attr:
          d[a] = value
        else:
          d[a] = getattr(self, a)

      version = ""
      if d['epoch'] and d['epoch'] != '0':
        version += d['epoch'] + ":"
      version += d['upstream_version']
      if d['debian_version']:
        version += '-' + d['debian_version']

      self.full_version = version

  full_version = property(lambda self: self.__asString)

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

topline = re.compile('^([a-z0-9][-a-z0-9.+]+) \(([-0-9a-zA-Z.:~+]+)\) '
      +'([-a-zA-Z ]+); urgency=([a-z]+)')
blankline = re.compile('^[ \t]*$')
change = re.compile('^[ ][ ]+.*$')
endline = re.compile('^ -- (.*)  (\w\w\w, +(\d| \d|\d\d) \w\w\w \d\d\d\d '+
      '\d\d:\d\d:\d\d [-+]\d\d\d\d( \(.*\))?)\s*$')

class Changelog(object):
  """Represents a debian/changelog file. You can ask it several things about
  the file."""


  def __init__(self, file=None, max_blocks=None):
    """Set up the Changelog for use. file is the contects of the changelog.
    """
    self._blocks = []
    if file is not None:
      try:
        self.parse_changelog(file, max_blocks)
      except ChangelogParseError:
        pass


  def parse_changelog(self, file, max_blocks=None):
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
              if max_blocks is not None and len(self._blocks) >= max_blocks:
                break
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

  def get_version(self):
    """Return a Version object for the last version"""
    return self._blocks[0].version

  def set_version(self, version):
    """Set the version of the last changelog block

    version can be a full version string, or a Version object
    """
    self._blocks[0].version = Version(version)

  version = property(get_version, set_version,
                     doc="Version object for last changelog block""")

  ### For convenience, let's expose some of the version properties
  full_version = property(lambda self: self.version.full_version,
                  lambda self, v: setattr(self.version, 'full_version', v))
  epoch = property(lambda self: self.version.epoch,
                  lambda self, v: setattr(self.version, 'epoch', v))
  debian_version = property(lambda self: self.version.debian_version,
                  lambda self, v: setattr(self.version, 'debian_version', v))
  upstream_version = property(lambda self: self.version.upstream_version,
                  lambda self, v: setattr(self.version, 'upstream_version', v))

  def get_package(self):
    """Returns the name of the package in the last version."""
    return self._blocks[0].package
  
  def set_package(self, package):
    self._blocks[0].package = package

  package = property(get_package, set_package,
                     doc="Name of the package in the last version")

  def get_versions(self):
    """Returns a list of version objects that the package went through."""
    return [block.version for block in self._blocks]

  versions = property(get_versions,
                      doc="List of version objects the package went through")

  def __str__(self):
    cl = ""
    for block in self._blocks:
      cl += str(block)
    return cl

  def set_distributions(self, distributions):
    self._blocks[0].distributions = distributions
  distributions = property(lambda self: self._blocks[0].distributions,
                           set_distributions)

  def set_urgency(self, urgency):
    self._blocks[0].urgency = urgency
  urgency = property(lambda self: self._blocks[0].urgency, set_urgency)

  def add_change(self, change):
    self._blocks[0].add_change(change)

  def set_author(self, author):
    self._blocks[0].author = author
  author = property(lambda self: self._blocks[0].author, set_author)

  def set_date(self, date):
    self._blocks[0].date = date
  date = property(lambda self: self._blocks[0].date, set_date)

  def new_block(self, package=None, version=None, distributions=None,
                urgency=None, changes=None, author=None, date=None):
    block = ChangeBlock(package, version, distributions, urgency,
                        changes, author, date)
    block.add_trailing_newline()
    self._blocks.insert(0, block)

  def write_to_open_file(self, file):
    file.write(self.__str__())

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

  def test_create_changelog_single_block(self):

    c = open('test_changelog').read()
    cl = Changelog(c, max_blocks=1)
    cs = str(cl)
    self.assertEqual(cs,
    """gnutls13 (1:1.4.1-1) unstable; urgency=low

  [ James Westby ]
  * New upstream release.
  * Remove the following patches as they are now included upstream:
    - 10_certtoolmanpage.diff
    - 15_fixcompilewarning.diff
    - 30_man_hyphen_*.patch
  * Link the API reference in /usr/share/gtk-doc/html as gnutls rather than
    gnutls-api so that devhelp can find it.

 -- Andreas Metzler <ametzler@debian.org>  Sat, 15 Jul 2006 11:11:08 +0200
""")

  def test_modify_changelog(self):

    c = open('test_modify_changelog1').read()
    cl = Changelog(c)
    cl.package = 'gnutls14'
    cl.version = '1:1.4.1-2'
    cl.distributions = 'experimental'
    cl.urgency = 'medium'
    cl.add_change('  * Add magic foo')
    cl.author = 'James Westby <jw+debian@jameswestby.net>'
    cl.date = 'Sat, 16 Jul 2008 11:11:08 -0200'
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

  def test_strange_changelogs(self):
    """ Just opens and parses a strange changelog """
    c = open('test_strange_changelog').read()
    cl = Changelog(c)

  def test_set_version_with_string(self):
    c1 = Changelog(open('test_modify_changelog1').read())
    c2 = Changelog(open('test_modify_changelog1').read())

    c1.version = '1:2.3.5-2'
    c2.version = Version('1:2.3.5-2')
    self.assertEqual(c1.version, c2.version)
    self.assertEqual((c1.full_version, c1.epoch, c1.upstream_version,
                      c1.debian_version),
                     (c2.full_version, c2.epoch, c2.upstream_version,
                      c2.debian_version))

  def test_magic_version_properties(self):
    c = Changelog(open('test_changelog').read())

    c.debian_version = '2'
    self.assertEqual(c.debian_version, '2')
    self.assertEqual(c.full_version, '1:1.4.1-2')

    c.upstream_version = '1.4.2'
    self.assertEqual(c.upstream_version, '1.4.2')
    self.assertEqual(c.full_version, '1:1.4.2-2')

    c.epoch = '2'
    self.assertEqual(c.epoch, '2')
    self.assertEqual(c.full_version, '2:1.4.2-2')

    self.assertEqual(str(c.version), c.full_version)

    c.full_version = '1:1.4.1-1'
    self.assertEqual(c.full_version, '1:1.4.1-1')
    self.assertEqual(c.epoch, '1')
    self.assertEqual(c.upstream_version, '1.4.1')
    self.assertEqual(c.debian_version, '1')

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
    self._test_version('1.1.0+cvs20060620-1+1.0', None, '1.1.0+cvs20060620',
                       '1+1.0')
    self._test_version('4.2.0a+stable-2sarge1', None, '4.2.0a+stable',
                       '2sarge1')
    self._test_version('1.8RC4b', None, '1.8RC4b', None)
    self._test_version('0.9~rc1-1', None, '0.9~rc1', '1')
    self._test_version('2:1.0.4+svn26-1ubuntu1', '2', '1.0.4+svn26',
                       '1ubuntu1')
    self._test_version('2:1.0.4~rc2-1', '2', '1.0.4~rc2', '1')

  def test_version_updating(self):
    v = Version('1:1.4.1-1')

    v.debian_version = '2'
    self.assertEqual(v.debian_version, '2')
    self.assertEqual(v.full_version, '1:1.4.1-2')

    v.upstream_version = '1.4.2'
    self.assertEqual(v.upstream_version, '1.4.2')
    self.assertEqual(v.full_version, '1:1.4.2-2')

    v.epoch = '2'
    self.assertEqual(v.epoch, '2')
    self.assertEqual(v.full_version, '2:1.4.2-2')

    self.assertEqual(str(v), v.full_version)

    v.full_version = '1:1.4.1-1'
    self.assertEqual(v.full_version, '1:1.4.1-1')
    self.assertEqual(v.epoch, '1')
    self.assertEqual(v.upstream_version, '1.4.1')
    self.assertEqual(v.debian_version, '1')

if __name__ == "__main__":
  _test()

# vim:softtabstop=2 shiftwidth=2 expandtab
