#! /usr/bin/python
## vim: fileencoding=utf-8

# Copyright (C) 2006 Adeodato Simó <dato@net.com.org.es>
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

import re
import deb822
import unittest
from StringIO import StringIO

# Keep the test suite compatible with python2.3 for now
try:
    sorted
except NameError:
    def sorted(iterable, cmp=None):
        tmp = iterable[:]
        tmp.sort(cmp)
        return tmp


UNPARSED_PACKAGE = '''\
Package: mutt
Priority: standard
Section: mail
Installed-Size: 4471
Maintainer: Adeodato Simó <dato@net.com.org.es>
Architecture: i386
Version: 1.5.12-1
Replaces: mutt-utf8
Provides: mail-reader, imap-client
Depends: libc6 (>= 2.3.6-6), libdb4.4, libgnutls13 (>= 1.4.0-0), libidn11 (>= 0.5.18), libncursesw5 (>= 5.4-5), libsasl2 (>= 2.1.19.dfsg1), exim4 | mail-transport-agent
Recommends: locales, mime-support
Suggests: urlview, aspell | ispell, gnupg, mixmaster, openssl, ca-certificates
Conflicts: mutt-utf8
Filename: pool/main/m/mutt/mutt_1.5.12-1_i386.deb
Size: 1799444
MD5sum: d4a9e124beea99d8124c8e8543d22e9a
SHA1: 5e3c295a921c287cf7cb3944f3efdcf18dd6701a
SHA256: 02853602efe21d77cd88056a4e2a4350f298bcab3d895f5f9ae02aacad81442b
Description: text-based mailreader supporting MIME, GPG, PGP and threading
 Mutt is a sophisticated text-based Mail User Agent. Some highlights:
 .
  * MIME support (including RFC1522 encoding/decoding of 8-bit message
    headers and UTF-8 support).
  * PGP/MIME support (RFC 2015).
  * Advanced IMAP client supporting SSL encryption and SASL authentication.
  * POP3 support.
  * Mailbox threading (both strict and non-strict).
  * Default keybindings are much like ELM.
  * Keybindings are configurable; Mush and PINE-like ones are provided as
    examples.
  * Handles MMDF, MH and Maildir in addition to regular mbox format.
  * Messages may be (indefinitely) postponed.
  * Colour support.
  * Highly configurable through easy but powerful rc file.
Tag: interface::text-mode, made-of::lang:c, mail::imap, mail::pop, mail::user-agent, protocol::imap, protocol::ipv6, protocol::pop, protocol::ssl, role::sw:client, uitoolkit::ncurses, use::editing, works-with::mail
Task: mail-server
'''
        

PARSED_PACKAGE = deb822.Deb822Dict([
    ('Package', 'mutt'),
    ('Priority', 'standard'),
    ('Section', 'mail'),
    ('Installed-Size', '4471'),
    ('Maintainer', 'Adeodato Simó <dato@net.com.org.es>'),
    ('Architecture', 'i386'),
    ('Version', '1.5.12-1'),
    ('Replaces', 'mutt-utf8'),
    ('Provides', 'mail-reader, imap-client'),
    ('Depends', 'libc6 (>= 2.3.6-6), libdb4.4, libgnutls13 (>= 1.4.0-0), libidn11 (>= 0.5.18), libncursesw5 (>= 5.4-5), libsasl2 (>= 2.1.19.dfsg1), exim4 | mail-transport-agent'),
    ('Recommends', 'locales, mime-support'),
    ('Suggests', 'urlview, aspell | ispell, gnupg, mixmaster, openssl, ca-certificates'),
    ('Conflicts', 'mutt-utf8'),
    ('Filename', 'pool/main/m/mutt/mutt_1.5.12-1_i386.deb'),
    ('Size', '1799444'),
    ('MD5sum', 'd4a9e124beea99d8124c8e8543d22e9a'),
    ('SHA1', '5e3c295a921c287cf7cb3944f3efdcf18dd6701a'),
    ('SHA256', '02853602efe21d77cd88056a4e2a4350f298bcab3d895f5f9ae02aacad81442b'),
    ('Description', '''text-based mailreader supporting MIME, GPG, PGP and threading
 Mutt is a sophisticated text-based Mail User Agent. Some highlights:
 .
  * MIME support (including RFC1522 encoding/decoding of 8-bit message
    headers and UTF-8 support).
  * PGP/MIME support (RFC 2015).
  * Advanced IMAP client supporting SSL encryption and SASL authentication.
  * POP3 support.
  * Mailbox threading (both strict and non-strict).
  * Default keybindings are much like ELM.
  * Keybindings are configurable; Mush and PINE-like ones are provided as
    examples.
  * Handles MMDF, MH and Maildir in addition to regular mbox format.
  * Messages may be (indefinitely) postponed.
  * Colour support.
  * Highly configurable through easy but powerful rc file.'''),
    ('Tag', 'interface::text-mode, made-of::lang:c, mail::imap, mail::pop, mail::user-agent, protocol::imap, protocol::ipv6, protocol::pop, protocol::ssl, role::sw:client, uitoolkit::ncurses, use::editing, works-with::mail'),
    ('Task', 'mail-server'), ])


GPG_SIGNED = [ '''\
-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA1

%s

-----BEGIN PGP SIGNATURE-----
Version: GnuPG v1.4.3 (GNU/Linux)
Comment: Signed by Adeodato Simó <dato@net.com.org.es>

iEYEARECAAYFAkRqYxkACgkQgyNlRdHEGIKccQCgnnUgfwYjQ7xd3zGGS2y5cXKt
CcYAoOLYDF5G1h3oR1iDNyeCI6hRW03S
=Um8T
-----END PGP SIGNATURE-----
''', '''\
-----BEGIN PGP SIGNED MESSAGE-----
Hash: SHA1

%s

-----BEGIN PGP SIGNATURE-----

iEYEARECAAYFAkRqYxkACgkQgyNlRdHEGIKccQCgnnUgfwYjQ7xd3zGGS2y5cXKt
CcYAoOLYDF5G1h3oR1iDNyeCI6hRW03S
=Um8T
-----END PGP SIGNATURE-----
''',
    ]


class TestDeb822Dict(unittest.TestCase):
    def make_dict(self):
        d = deb822.Deb822Dict()
        d['TestKey'] = 1
        d['another_key'] = 2

        return d

    def test_case_insensitive_lookup(self):
        d = self.make_dict()

        self.assertEqual(1, d['testkey'])
        self.assertEqual(2, d['Another_keY'])

    def test_case_insensitive_assignment(self):
        d = self.make_dict()
        d['testkey'] = 3

        self.assertEqual(3, d['TestKey'])
        self.assertEqual(3, d['testkey'])

        d.setdefault('foo', 4)
        self.assertEqual(4, d['Foo'])

    def test_case_preserved(self):
        d = self.make_dict()

        self.assertEqual(sorted(['another_key', 'TestKey']), sorted(d.keys()))

    def test_order_preserved(self):
        d = self.make_dict()
        d['Third_key'] = 3
        d['another_Key'] = 2.5

        keys = ['TestKey', 'another_key', 'Third_key']

        self.assertEqual(keys, d.keys())
        self.assertEqual(keys, list(d.iterkeys()))
        self.assertEqual(zip(keys, d.values()), d.items())

        keys2 = []
        for key in d:
            keys2.append(key)

        self.assertEqual(keys, keys2)

    def test_derived_dict_equality(self):
        d1 = self.make_dict()
        d2 = dict(d1)

        self.assertEqual(d1, d2)


class TestDeb822(unittest.TestCase):
    def assertWellParsed(self, deb822_, dict_):
        """Check that the given Deb822 object has the very same keys and
           values as the given dict.
        """

        self.assertEqual(deb822_.keys(), dict_.keys())

        for k, v in dict_.items():
            self.assertEqual(v, deb822_[k])
        self.assertEqual(0, deb822_.__cmp__(dict_))

    def gen_random_string(length=20):
        from random import choice
        import string
        chars = string.letters + string.digits
        return ''.join([choice(chars) for i in range(length)])
    gen_random_string = staticmethod(gen_random_string)

    def deb822_from_format_string(self, string, dict_=PARSED_PACKAGE, cls=deb822.Deb822):
        """Construct a Deb822 object by formatting string with % dict.
        
        Returns the formatted string, and a dict object containing only the
        keys that were used for the formatting."""

        dict_subset = DictSubset(dict_)
        string = string % dict_subset
        parsed = cls(string.splitlines())
        return parsed, dict_subset

    def test_parser(self):
        deb822_ = deb822.Deb822(UNPARSED_PACKAGE.splitlines())
        self.assertWellParsed(deb822_, PARSED_PACKAGE)

    def test_parser_with_newlines(self):
        deb822_ = deb822.Deb822([ l+'\n' for l in UNPARSED_PACKAGE.splitlines()])
        self.assertWellParsed(deb822_, PARSED_PACKAGE)

    def test_strip_initial_blanklines(self):
        deb822_ = deb822.Deb822(['\n'] * 3 + UNPARSED_PACKAGE.splitlines())
        self.assertWellParsed(deb822_, PARSED_PACKAGE)

    def test_gpg_stripping(self):
        for string in GPG_SIGNED:
            unparsed_with_gpg = string % UNPARSED_PACKAGE
            deb822_ = deb822.Deb822(unparsed_with_gpg.splitlines())
            self.assertWellParsed(deb822_, PARSED_PACKAGE)

    def test_iter_paragraphs_array(self):
        text = (UNPARSED_PACKAGE + '\n\n\n' + UNPARSED_PACKAGE).splitlines()

        for d in deb822.Deb822.iter_paragraphs(text):
            self.assertWellParsed(d, PARSED_PACKAGE)

    def test_iter_paragraphs_file(self):
        text = StringIO(UNPARSED_PACKAGE + '\n\n\n' + UNPARSED_PACKAGE)

        for d in deb822.Deb822.iter_paragraphs(text):
            self.assertWellParsed(d, PARSED_PACKAGE)

    def test_iter_paragraphs_with_gpg(self):
        for string in GPG_SIGNED:
            string = string % UNPARSED_PACKAGE
            text = (string + '\n\n\n' + string).splitlines()

            for d in deb822.Deb822.iter_paragraphs(text):
                self.assertWellParsed(d, PARSED_PACKAGE)

    def test_parser_empty_input(self):
        self.assertEqual({}, deb822.Deb822([]))

    def test_iter_paragraphs_empty_input(self):
        generator = deb822.Deb822.iter_paragraphs([])
        self.assertRaises(StopIteration, generator.next)

    def test_parser_limit_fields(self):
        wanted_fields = [ 'Package', 'MD5sum', 'Filename', 'Description' ]
        deb822_ = deb822.Deb822(UNPARSED_PACKAGE.splitlines(), wanted_fields)

        self.assertEquals(sorted(wanted_fields), sorted(deb822_.keys()))

        for key in wanted_fields:
            self.assertEquals(PARSED_PACKAGE[key], deb822_[key])

    def test_iter_paragraphs_limit_fields(self):
        wanted_fields = [ 'Package', 'MD5sum', 'Filename', 'Tag' ]

        for deb822_ in deb822.Deb822.iter_paragraphs(
                UNPARSED_PACKAGE.splitlines(), wanted_fields):

            self.assertEquals(sorted(wanted_fields), sorted(deb822_.keys()))

            for key in wanted_fields:
                self.assertEquals(PARSED_PACKAGE[key], deb822_[key])

    def test_dont_assume_trailing_newline(self):
        deb822a = deb822.Deb822(['Package: foo'])
        deb822b = deb822.Deb822(['Package: foo\n'])

        self.assertEqual(deb822a['Package'], deb822b['Package'])

        deb822a = deb822.Deb822(['Description: foo\n', 'bar'])
        deb822b = deb822.Deb822(['Description: foo', 'bar\n'])

        self.assertEqual(deb822a['Description'], deb822b['Description'])

    def test__delitem__(self):
        parsed = deb822.Deb822(UNPARSED_PACKAGE.splitlines())
        dict_ = PARSED_PACKAGE.copy()

        for key in ('Package', 'MD5sum', 'Description'):
            del parsed[key]
            del dict_[key]

            parsed.keys() # ensure this does not raise error
            self.assertWellParsed(parsed, dict_)

    def test_policy_compliant_whitespace(self):
        string = (
            'Package: %(Package)s\n'
            'Version :%(Version)s \n'
            'Priority:%(Priority)s\t \n'
            'Section \t :%(Section)s \n'
            'Empty-Field:        \t\t\t\n'
            'Multiline-Field : a \n b\n c\n'
        ) % PARSED_PACKAGE

        deb822_ = deb822.Deb822(string.splitlines())
        dict_   = PARSED_PACKAGE.copy()

        dict_['Empty-Field'] = ''
        dict_['Multiline-Field'] = 'a\n b\n c' # XXX should be 'a\nb\nc'?

        for k, v in deb822_.items():
            self.assertEquals(dict_[k], v)
    
    def test_case_insensitive(self):
        # PARSED_PACKAGE is a deb822.Deb822Dict object, so we can test
        # it directly
        self.assertEqual(PARSED_PACKAGE['Architecture'],
                         PARSED_PACKAGE['architecture'])

        c_i_dict = deb822.Deb822Dict()

        test_string = self.gen_random_string()
        c_i_dict['Test-Key'] = test_string
        self.assertEqual(test_string, c_i_dict['test-key'])

        test_string_2 = self.gen_random_string()
        c_i_dict['TeSt-KeY'] = test_string_2
        self.assertEqual(test_string_2, c_i_dict['Test-Key'])

        deb822_ = deb822.Deb822(StringIO(UNPARSED_PACKAGE))
        # deb822_.keys() will return non-normalized keys
        for k in deb822_.keys():
            self.assertEqual(deb822_[k], deb822_[k.lower()])

    def test_multiline_trailing_whitespace_after_colon(self):
        """Trailing whitespace after the field name on multiline fields

        If the field's value starts with a newline (e.g. on MD5Sum fields in
        Release files, or Files field in .dsc's, the dumped string should not
        have a trailing space after the colon.  If the value does not start
        with a newline (e.g. the control file Description field), then there
        should be a space after the colon, as with non-multiline fields.
        """
        
        dsc_string = """Format: 1.0
Source: python-debian
Binary: python-debian
Architecture: all
Version: 0.1.4
Maintainer: Debian python-debian Maintainers <pkg-python-debian-maint@lists.alioth.debian.org>
Uploaders: Adeodato Simó <dato@net.com.org.es>, Enrico Zini <enrico@debian.org>, James Westby <jw+debian@jameswestby.net>, Reinhard Tartler <siretart@tauware.de>, Stefano Zacchiroli <zack@debian.org>, John Wright <john@movingsucks.org>
Standards-Version: 3.7.2
Build-Depends: debhelper (>= 5.0.37.2), python, m4
Build-Depends-Indep: python-support (>= 0.3)
Files:
 065aa27943a4fc9e7020f324fed57b65 68575 python-debian_0.1.4.tar.gz
Vcs-Bzr: http://bzr.debian.org/pkg-python-debian/trunk/
"""
        parsed_dsc = deb822.Deb822(dsc_string.splitlines())

        # bad_re: match a line that starts with a "Field:", and ends in
        # whitespace
        bad_re = re.compile(r"^\S+:\s+$")
        for line in parsed_dsc.dump().splitlines():
            self.assert_(bad_re.match(line) is None,
                         "There should not be trailing whitespace after the "
                         "colon in a multiline field starting with a newline")

        
        control_paragraph = """Package: python-debian
Architecture: all
Depends: ${python:Depends}
Suggests: python-apt
Provides: python-deb822
Conflicts: python-deb822
Replaces: python-deb822
Description: python modules to work with Debian-related data formats
 This package provides python modules that abstract many formats of Debian
 related files. Currently handled are:
  * Debtags information (debian_bundle.debtags module)
  * debian/changelog (debian_bundle.changelog module)
  * Packages files, pdiffs (debian_bundle.debian_support module)
  * Control files of single or multple RFC822-style paragraphs, e.g
    debian/control, .changes, .dsc, Packages, Sources, Release, etc.
    (debian_bundle.deb822 module)
"""
        parsed_control = deb822.Deb822(control_paragraph.splitlines())
        field_re = re.compile(r"^\S+:")
        field_with_space_re = re.compile(r"^\S+: ")
        for line in parsed_control.dump().splitlines():
            if field_re.match(line):
                self.assert_(field_with_space_re.match(line),
                             "Multiline fields that do not start with newline "
                             "should have a space between the colon and the "
                             "beginning of the value")
        

if __name__ == '__main__':
    unittest.main()
