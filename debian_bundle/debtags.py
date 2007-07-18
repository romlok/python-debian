
# debtags.py -- Access and manipulate Debtags information
# Copyright (C) 2006-2007  Enrico Zini <enrico@enricozini.org>
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

import math, re, cPickle

def parseTags(input):
	lre = re.compile(r"^(.+?)(?::?\s*|:\s+(.+?)\s*)$")
	for line in input:
		# Is there a way to remove the last character of a line that does not
		# make a copy of the entire line?
		m = lre.match(line)
		pkgs = set(m.group(1).split(', '))
		if m.group(2):
			tags = set(m.group(2).split(', '))
		else:
			tags = set()
		yield pkgs, tags

def readTagDatabase(input):
	"Read the tag database, returning a pkg->tags dictionary"
	db = {}
	for pkgs, tags in parseTags(input):
		# Create the tag set using the native set
		for p in pkgs:
			db[p] = tags.copy()
	return db;

def readTagDatabaseReversed(input):
	"Read the tag database, returning a tag->pkgs dictionary"
	db = {}
	for pkgs, tags in parseTags(input):
		# Create the tag set using the native set
		for tag in tags:
			if db.has_key(tag):
				db[tag] |= pkgs
			else:
				db[tag] = pkgs.copy()
	return db;

def readTagDatabaseBothWays(input, tagFilter = None):
	"Read the tag database, returning a pkg->tags and a tag->pkgs dictionary"
	db = {}
	dbr = {}
	for pkgs, tags in parseTags(input):
		# Create the tag set using the native set
		if tagFilter == None:
			tags = set(tags)
		else:
			tags = set(filter(tagFilter, tags))
		for pkg in pkgs:
			db[pkg] = tags.copy()
		for tag in tags:
			if dbr.has_key(tag):
				dbr[tag] |= pkgs
			else:
				dbr[tag] = pkgs.copy()
	return db, dbr;


def reverse(db):
	"Reverse a tag database, from package -> tags to tag->packages"
	res = {}
	for pkg, tags in db.items():
		for tag in tags:
			if not res.has_key(tag):
				res[tag] = set()
			res[tag].add(pkg)
	return res


def output(db):
	"Write the tag database"
	for pkg, tags in db.items():
		# Using % here seems awkward to me, but if I use calls to
		# sys.stdout.write it becomes a bit slower
		print "%s:" % (pkg), ", ".join(tags)


def relevanceIndexFunction(full, sub):
	#return (float(sub.card(tag)) / float(sub.tagCount())) / \
	#       (float(full.card(tag)) / float(full.tagCount()))
	#return sub.card(tag) * full.card(tag) / sub.tagCount()

	# New cardinality divided by the old cardinality
	#return float(sub.card(tag)) / float(full.card(tag))

	## Same as before, but weighted by the relevance the tag had in the
	## full collection, to downplay the importance of rare tags
	#return float(sub.card(tag) * full.card(tag)) / float(full.card(tag) * full.tagCount())
	# Simplified version:
	#return float(sub.card(tag)) / float(full.tagCount())
	
	# Weighted by the square root of the relevance, to downplay the very
	# common tags a bit
	#return lambda tag: float(sub.card(tag)) / float(full.card(tag)) * math.sqrt(full.card(tag) / float(full.tagCount()))
	#return lambda tag: float(sub.card(tag)) / float(full.card(tag)) * math.sqrt(full.card(tag) / float(full.packageCount()))
	# One useless factor removed, and simplified further, thanks to Benjamin Mesing
	return lambda tag: float(sub.card(tag)**2) / float(full.card(tag))

	# The difference between how many packages are in and how many packages are out
	# (problems: tags that mean many different things can be very much out
	# as well.  In the case of 'image editor', for example, there will be
	# lots of editors not for images in the outside group.
	# It is very, very good for nonambiguous keywords like 'image'.
	#return lambda tag: 2 * sub.card(tag) - full.card(tag)
	# Same but it tries to downplay the 'how many are out' value in the
	# case of popular tags, to mitigate the 'there will always be popular
	# tags left out' cases.  Does not seem to be much of an improvement.
	#return lambda tag: sub.card(tag) - float(full.card(tag) - sub.card(tag))/(math.sin(float(full.card(tag))*3.1415/full.packageCount())/4 + 0.75)


class DB:
	"""
	In-memory database mapping packages to tags and tags to packages.
	"""

	def __init__(self):
		self.db = {}
		self.rdb = {}
	
	def read(self, input, tagFilter = None):
		"""
		Read the database from a file.

		Example::
			# Read the system Debtags database
			db.read(open("/var/lib/debtags/package-tags", "r"))
		"""
		self.db, self.rdb = readTagDatabaseBothWays(input, tagFilter)

	def qwrite(self, file):
		"Quickly write the data to a pickled file"
		cPickle.dump(self.db, file)
		cPickle.dump(self.rdb, file)

	def qread(self, file):
		"Quickly read the data from a pickled file"
		self.db = cPickle.load(file)
		self.rdb = cPickle.load(file)

	def insert(self, pkg, tags):
		self.db[pkg] = tags.copy()
		for tag in tags:
			if self.rdb.has_key(tag):
				self.rdb[tag].add(pkg)
			else:
				self.rdb[tag] = set((pkg))

	def dump(self):
		output(self.db)

	def dumpReverse(self):
		output(self.rdb)
	
	def reverse(self):
		"Return the reverse collection, sharing tagsets with this one"
		res = DB()
		res.db = self.rdb
		res.rdb = self.db
		return res

	def facetCollection(self):
		"""
		Return a copy of this collection, but replaces the tag names
		with only their facets.
		"""
		fcoll = DB()
		tofacet = re.compile(r"^([^:]+).+")
		for pkg, tags in self.iterPackagesTags():
			ftags = set([tofacet.sub(r"\1", t) for t in tags])
			fcoll.insert(pkg, ftags)
		return fcoll

	def copy(self):
		"""
		Return a copy of this collection, with the tagsets copied as
		well.
		"""
		res = DB()
		res.db = self.db.copy()
		res.rdb = self.rdb.copy()
		return res

	def reverseCopy(self):
		"""
		Return the reverse collection, with a copy of the tagsets of
		this one.
		"""
		res = DB()
		res.db = self.rdb.copy()
		res.rdb = self.db.copy()
		return res

	def choosePackages(self, packageIter):
		"""
		Return a collection with only the packages in packageIter,
		sharing tagsets with this one
		"""
		res = DB()
		db = {}
		for pkg in packageIter:
			if self.db.has_key(pkg): db[pkg] = self.db[pkg]
		res.db = db
		res.rdb = reverse(db)
		return res

	def choosePackagesCopy(self, packageIter):
		"""
		Return a collection with only the packages in packageIter,
		with a copy of the tagsets of this one
		"""
		res = DB()
		db = {}
		for pkg in packageIter:
			db[pkg] = self.db[pkg]
		res.db = db
		res.rdb = reverse(db)
		return res

	def filterPackages(self, packageFilter):
		"""
		Return a collection with only those packages that match a
		filter, sharing tagsets with this one.  The filter will match
		on the package.
		"""
		res = DB()
		db = {}
		for pkg in filter(packageFilter, self.db.iterkeys()):
			db[pkg] = self.db[pkg]
		res.db = db
		res.rdb = reverse(db)
		return res

	def filterPackagesCopy(self, filter):
		"""
		Return a collection with only those packages that match a
		filter, with a copy of the tagsets of this one.  The filter
		will match on the package.
		"""
		res = DB()
		db = {}
		for pkg in filter(filter, self.db.iterkeys()):
			db[pkg] = self.db[pkg].copy()
		res.db = db
		res.rdb = reverse(db)
		return res

	def filterPackagesTags(self, packageTagFilter):
		"""
		Return a collection with only those packages that match a
		filter, sharing tagsets with this one.  The filter will match
		on (package, tags).
		"""
		res = DB()
		db = {}
		for pkg, tags in filter(packageTagFilter, self.db.iteritems()):
			db[pkg] = self.db[pkg]
		res.db = db
		res.rdb = reverse(db)
		return res

	def filterPackagesTagsCopy(self, packageTagFilter):
		"""
		Return a collection with only those packages that match a
		filter, with a copy of the tagsets of this one.  The filter
		will match on (package, tags).
		"""
		res = DB()
		db = {}
		for pkg, tags in filter(packageTagFilter, self.db.iteritems()):
			db[pkg] = self.db[pkg].copy()
		res.db = db
		res.rdb = reverse(db)
		return res

	def filterTags(self, tagFilter):
		"""
		Return a collection with only those tags that match a
		filter, sharing package sets with this one.  The filter will match
		on the tag.
		"""
		res = DB()
		rdb = {}
		for tag in filter(tagFilter, self.rdb.iterkeys()):
			rdb[tag] = self.rdb[tag]
		res.rdb = rdb
		res.db = reverse(rdb)
		return res

	def filterTagsCopy(self, tagFilter):
		"""
		Return a collection with only those tags that match a
		filter, with a copy of the package sets of this one.  The
		filter will match on the tag.
		"""
		res = DB()
		rdb = {}
		for tag in filter(tagFilter, self.rdb.iterkeys()):
			rdb[tag] = self.rdb[tag].copy()
		res.rdb = rdb
		res.db = reverse(rdb)
		return res

	def hasPackage(self, pkg):
		"""Check if the collection contains the given package"""
		return self.db.has_key(pkg)

	def hasTag(self, tag):
		"""Check if the collection contains packages tagged with tag"""
		return self.rdb.has_key(tag)

	def tagsOfPackage(self, pkg):
		"""Return the tag set of a package"""
		return self.db.has_key(pkg) and self.db[pkg] or set()

	def packagesOfTag(self, tag):
		"""Return the package set of a tag"""
		return self.rdb.has_key(tag) and self.rdb[tag] or set()

	def tagsOfPackages(self, pkgs):
		"""Return the set of tags that have all the packages in pkgs"""
		res = None
		for p in pkgs:
			if res == None:
				res = set(self.tagsOfPackage(p))
			else:
				res &= self.tagsOfPackage(p)
		return res

	def packagesOfTags(self, tags):
		"""Return the set of packages that have all the tags in tags"""
		res = None
		for t in tags:
			if res == None:
				res = set(self.packagesOfTag(t))
			else:
				res &= self.packagesOfTag(t)
		return res

	def card(self, tag):
		"""
		Return the cardinality of a tag
		"""
		return self.rdb.has_key(tag) and len(self.rdb[tag]) or 0

	def discriminance(self, tag):
		"""
		Return the discriminance index if the tag.
		
		Th discriminance index of the tag is defined as the minimum
		number of packages that would be eliminated by selecting only
		those tagged with this tag or only those not tagged with this
		tag.
		"""
		n = self.card(tag)
		tot = self.packageCount()
		return min(n, tot - n)

	def iterPackages(self):
		"""Iterate over the packages"""
		return self.db.iterkeys()

	def iterTags(self):
		"""Iterate over the tags"""
		return self.rdb.iterkeys()

	def iterPackagesTags(self):
		"""Iterate over 2-tuples of (pkg, tags)"""
		return self.db.iteritems()

	def iterTagsPackages(self):
		"""Iterate over 2-tuples of (tag, pkgs)"""
		return self.rdb.iteritems()

	def packageCount(self):
		"""Return the number of packages"""
		return len(self.db)

	def tagCount(self):
		"""Return the number of tags"""
		return len(self.rdb)

	def idealTagset(self, tags):
		"""
		Return an ideal selection of the top tags in a list of tags.

		Return the tagset made of the highest number of tags taken in
		consecutive sequence from the beginning of the given vector,
		that would intersecate with the tagset of a comfortable amount
		of packages.

		Comfortable is defined in terms of how far it is from 7.
		"""

		# TODO: the scoring function is quite ok, but may need more
		# tuning.  I also center it on 15 instead of 7 since we're
		# setting a starting point for the search, not a target point
		def score_fun(x):
			return float((x-15)*(x-15))/x

		hits = []
		tagset = set()
		min_score = 3
		for i in range(len(tags)):
			pkgs = self.packagesOfTags(tags[:i+1])
			card = len(pkgs)
			if card == 0: break;
			score = score_fun(card)
			if score < min_score:
				min_score = score
				tagset = set(tags[:i+1])

		# Return always at least the first tag
		if len(tagset) == 0:
			return set(tags[:1])
		else:
			return tagset

	def correlations(self):
		"""
		Generate the list of correlation as a tuple (hastag, hasalsotag, score).

		Every touple will indicate that the tag 'hastag' tends to also
		have 'hasalsotag' with a score of 'score'.
		"""
		for pivot in self.iterTags():
			with_ = self.filterPackagesTags(lambda pt: pivot in pt[1])
			without = self.filterPackagesTags(lambda pt: pivot not in pt[1])
			for tag in with_.iterTags():
				if tag == pivot: continue
				has = float(with_.card(tag)) / float(with_.packageCount())
				hasnt = float(without.card(tag)) / float(without.packageCount())
				yield pivot, tag, has - hasnt
