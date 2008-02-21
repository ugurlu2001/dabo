# -*- coding: utf-8 -*-
"""Contains helper functions for dealing with dates and datetimes.

For example, getting a date from a string in various formats.
"""
import datetime
import re
import time
import dabo

_dregex = {}
_dtregex = {}
_tregex = {}


def _getDateRegex(format):
	elements = {}
	elements["year"] = "(?P<year>[0-9]{4,4})"              ## year 0000-9999
	elements["shortyear"] = "(?P<shortyear>[0-9]{2,2})"    ## year 00-99
	elements["month"] = "(?P<month>0[1-9]|1[012])"         ## month 01-12
	elements["day"] = "(?P<day>0[1-9]|[1-2][0-9]|3[0-1])"  ## day 01-31
	
	if format == "ISO8601":
		exp = "^%(year)s-%(month)s-%(day)s$"
	elif format == "YYYYMMDD":
		exp = "^%(year)s%(month)s%(day)s$"
	elif format == "YYMMDD":
		exp = "^%(shortyear)s%(month)s%(day)s$"
	elif format == "MMDD":
		exp = "^%(month)s%(day)s$"
	else:
		conv = {"%d": "%(day)s",
		        "%m": "%(month)s",
		        "%y": "%(shortyear)s",
		        "%Y": "%(year)s"}
		if "%d" in format and "%m" in format and ("%y" in format or "%Y" in format):
			for k in conv.keys():
				format = format.replace(k, conv[k])
				format.replace(".", "\.")
				exp = "^%s$" % format
		else:
			return None

	return re.compile(exp % elements)

		
def _getDateTimeRegex(format):
	elements = {}
	elements["year"] = "(?P<year>[0-9]{4,4})"              ## year 0000-9999
	elements["shortyear"] = "(?P<shortyear>[0-9]{2,2})"    ## year 00-99
	elements["month"] = "(?P<month>0[1-9]|1[012])"         ## month 01-12
	elements["day"] = "(?P<day>0[1-9]|[1-2][0-9]|3[0-1])"  ## day 01-31
	elements["hour"] = "(?P<hour>[0-1][0-9]|2[0-3])"       ## hour 00-23
	elements["minute"] = "(?P<minute>[0-5][0-9])"          ## minute 00-59
	elements["second"] = "(?P<second>[0-5][0-9])"          ## second 00-59
	elements["ms"] = "\.{0,1}(?P<ms>[0-9]{0,6})"           ## optional ms
	elements["sep"] = "(?P<sep> |T)"                       ## separator between date and time
	
	if format == "ISO8601":
		exp = "^%(year)s-%(month)s-%(day)s%(sep)s%(hour)s:%(minute)s:%(second)s%(ms)s$"
	elif format == "YYYYMMDDHHMMSS":
		exp = "^%(year)s%(month)s%(day)s%(hour)s%(minute)s%(second)s%(ms)s$"
	elif format == "YYMMDDHHMMSS":
		exp = "^%(shortyear)s%(month)s%(day)s%(hour)s%(minute)s%(second)s%(ms)s$"
	elif format == "YYYYMMDD":
		exp = "^%(year)s%(month)s%(day)s$"
	elif format == "YYMMDD":
		exp = "^%(shortyear)s%(month)s%(day)s$"
	else:
		return None
	return re.compile(exp % elements)


def _getTimeRegex(format):
	elements = {}
	elements["hour"] = "(?P<hour>[0-1][0-9]|2[0-3])"       ## hour 00-23
	elements["minute"] = "(?P<minute>[0-5][0-9])"          ## minute 00-59
	elements["second"] = "(?P<second>[0-5][0-9])"          ## second 00-59
	elements["ms"] = "\.{0,1}(?P<ms>[0-9]{0,6})"           ## optional ms
	elements["sep"] = "(?P<sep> |T)"

	if format == "ISO8601":
		exp = "^%(hour)s:%(minute)s:%(second)s%(ms)s$"
	else:
		return None
	return re.compile(exp % elements)


def getStringFromDate(d):
	"""Given a datetime.date, convert to string in dabo.settings.dateFormat style."""
	fmt = dabo.settings.dateFormat
	if fmt is None:
		# Delegate formatting to the time module, which will take the
		# user's locale into account.
		fmt = "%x"
	## note: don't use d.strftime(), as it doesn't handle < 1900
	return time.strftime(fmt, d.timetuple())


def getDateFromString(strVal, formats=None):
	"""Given a string in a defined format, return a date object or None."""
	global _dregex

	dateFormat = dabo.settings.dateFormat
	ret = None

	if formats is None:
		formats = ["ISO8601"]

	if dateFormat is not None:
		# Take the date format as set in dabo into account, when trying 
		# to make a date out of the string.
		formats.append(dateFormat)

	# Try each format in order:
	for format in formats:
		try:
			regex = _dregex[format]
		except KeyError:
			regex = _getDateRegex(format)
			if regex is None:
				continue
			_dregex[format] = regex
		m = regex.match(strVal)
		if m is not None:
			groups = m.groupdict()
			if not groups.has_key("year"):
				curYear = datetime.date.today().year
				if groups.has_key("shortyear"):
					groups["year"] = int("%s%s" % (str(curYear)[:2], 
							groups["shortyear"]))
				else:
					groups["year"] = curYear
			try:		
				ret = datetime.date(int(groups["year"]), 
					int(groups["month"]),
					int(groups["day"]))
			except ValueError:
				# Could be that the day was out of range for the particular month
				# (Sept. only has 30 days but the regex will allow 31, etc.)
				pass
		if ret is not None:
			break	
	if ret is None:
		if dateFormat is None:
			# Fall back to the current locale setting in user's os account:
			try:
				ret = datetime.date(*time.strptime(strVal, "%x")[:3])
			except:
				pass
	return ret


def getStringFromDateTime(dt):
	"""Given a datetime.datetime, convert to string in dabo.settings.dateTimeFormat style."""
	fmt = dabo.settings.dateTimeFormat
	if fmt is None:
		# Delegate formatting to the time module, which will take the
		# user's locale into account.
		fmt = "%x %X"
	## note: don't use dt.strftime(), as it doesn't handle < 1900
	return time.strftime(fmt, (dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second, dt.microsecond, 0, 0))


def getDateTimeFromString(strVal, formats=None):
	"""Given a string in a defined format, return a datetime object or None."""
	global _dtregex

	dtFormat = dabo.settings.dateTimeFormat
	ret = None

	if formats is None:
		formats = ["ISO8601"]

	if dtFormat is not None:
		formats.append(dtFormat)
	
	for format in formats:
		regex = _dtregex.get(format, None)
		if regex is None:
			regex = _getDateTimeRegex(format)
			if regex is None:
				continue
			_dtregex[format] = regex
		m = regex.match(strVal)
		if m is not None:
			groups = m.groupdict()
			for skip_group in ["ms", "second", "minute", "hour"]:
				if not groups.has_key(skip_group) or len(groups[skip_group]) == 0:
					# group not in the expression: default to 0
					groups[skip_group] = 0
			if not groups.has_key("year"):
				curYear = datetime.date.today().year
				if groups.has_key("shortyear"):
					groups["year"] = int("%s%s" % (str(curYear)[:2], 
							groups["shortyear"]))
				else:
					groups["year"] = curYear

			try:		
				return datetime.datetime(int(groups["year"]), 
					int(groups["month"]),
					int(groups["day"]),
					int(groups["hour"]),
					int(groups["minute"]),
					int(groups["second"]),
					int(groups["ms"]))
			except ValueError:
				raise
				# Could be that the day was out of range for the particular month
				# (Sept. only has 30 days but the regex will allow 31, etc.)
				pass
		if ret is not None:
			break
	if ret is None:
		if dtFormat is None:
			# Fall back to the current locale setting in user's os account:
			try:
				ret = datetime.datetime(*time.strptime(strVal, "%x %X"))
			except:
				pass
	return ret


def getTimeFromString(strVal, formats=None):
	"""Given a string in a defined format, return a	time object."""
	global _tregex

	ret = None
	if formats is None:
		formats = ["ISO8601"]

	for format in formats:
		regex = _tregex.get(format, None)
		if regex is None:
			regex = _getTimeRegex(format)
			if regex is None:
				continue
			_tregex[format] = regex
		m = regex.match(strVal)
		if m is not None:
			groups = m.groupdict()
			if len(groups["ms"]) == 0:
				# no ms in the expression
				groups["ms"] = 0
			return datetime.time(int(groups["hour"]),
				int(groups["minute"]),
				int(groups["second"]),
				int(groups["ms"]))
		if ret is not None:
			break	
	return ret


def goDate(date_datetime_exp, days):
	"""Given a date or datetime, return the date or datetime that is <days> away."""
	tt = date_datetime_exp.timetuple()
	seconds = time.mktime(tt)
	one_day = 60*60*24
	offset = (one_day * days)
	new_time = list(time.localtime(seconds + offset))
	new_time = tuple(new_time[:-3])
	if isinstance(date_datetime_exp, datetime.datetime):
		return datetime.datetime(*new_time)
	return datetime.date(new_time[0], new_time[1], new_time[2])


if __name__ == "__main__":
	print "testing converting strings to dates:"
	formats = ["ISO8601", "YYYYMMDD", "YYMMDD", "MMDD"]
	tests = ["0503", "20060503", "2006-05-03", "060503"]
	for test in tests:
		for format in formats:
			print "%s (%s) -> %s" % (test, format, repr(getDateFromString(test, [format])))

	dt = datetime.datetime.now()
	print goDate(dt, -30)
	d = datetime.date.today()
	print goDate(d, -30)
