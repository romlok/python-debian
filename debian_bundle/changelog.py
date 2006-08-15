import os
import re

class ChangelogError(StandardError):

  is_user_error = True

  def __string__(self):
    return "Could not parse changelog"


class Changelog(object):
  """Represents a debian/changelog file. You can ask it several things about
  the file."""

  def __init__(self, file=None):
    """Set up the Changelog for use. file is the contects of the changelog.
    If it is None, then the module will attempt to open 'debian/changelog'
    and use it's contents.
    
    >>> c = 'python-debian (0.1.0) unstable; urgency=low'
    >>> cl = Changelog(c)
    >>> cl.versions()
    ['0.1.0']
    >>> cl.full_version()
    '0.1.0'
    >>> cl.upstream_version()
    '0.1.0'
    >>> cl.debian_version()
    >>> cl.package()
    'python-debian'
    >>> c = 'python-debian (0.1.0-1) unstable; urgency=low'
    >>> cl = Changelog(c)
    >>> cl.full_version()
    '0.1.0-1'
    >>> cl.upstream_version()
    '0.1.0'
    >>> cl.debian_version()
    '1'
    >>> c += '\\np-d (0.0.1-1) unstable; urgency=low'
    >>> cl = Changelog(c)
    >>> cl.versions()
    ['0.1.0-1', '0.0.1-1']
    >>> cl.full_version()
    '0.1.0-1'
    >>> cl.upstream_version()
    '0.1.0'
    >>> cl.debian_version()
    '1'
    >>> cl.package()
    'python-debian'
    >>> c = '(0.1.0-1) unstable; urgency=low'
    >>> cl = Changelog(c)
    Traceback (most recent call last):
        ...
    ChangelogError
    """

    self._full_version = None
    self._package = None
    self._versions = []
    if file is None:
      f = open(os.path.join("debian","changelog"), 'r')
      contents = f.read()
      f.close()
      self._file = contents
    else:
      self._file = file
    p = re.compile('([a-z0-9][-a-z0-9.+]+) \(([-0-9a-z.:]+)\) '
        +'[-a-zA-Z]+( [-a-zA-Z]+)*; urgency=[a-z]+')
    for line in self._file.split('\n'):
      m = p.match(line)
      if m is not None:
        if self._package is None:
          self._package = m.group(1)
          self._full_version = m.group(2)
        self._versions.append(m.group(2))

    if self._full_version is None:
      raise ChangelogError()

    p = re.compile('(.+)-([^-]+)')
    m = p.match(self._full_version)
    if m is not None:
      self._upstream_version = m.group(1)
      self._debian_version = m.group(2)
    else:
      self._upstream_version = self._full_version
      self._debian_version = None


  def full_version(self):
    """Returns the full version number of the last version."""
    return self._full_version

  def debian_version(self):
    """Returns the debian part of the version number of the last version. 
    Will be None if it is a native package"""
    return self._debian_version

  def upstream_version(self):
    """Returns the upstream part of the version number of the last version"""
    return self._upstream_version

  def package(self):
    """Returns the name of the package in the last version."""
    return self._package

  def versions(self):
    """Returns a list of versions that the package went through."""
    return self._versions

def _test():
  import doctest
  doctest.testmod()

if __name__ == "__main__":
  _test()

