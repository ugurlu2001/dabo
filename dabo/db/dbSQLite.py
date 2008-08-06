# -*- coding: utf-8 -*-
import sys
import os
import re
import dabo
from dabo.dLocalize import _
from dabo.dException import dException
from dBackend import dBackend
from dNoEscQuoteStr import dNoEscQuoteStr as dNoEQ
from dCursorMixin import dCursorMixin


class SQLite(dBackend):
	"""Class providing SQLite connectivity. Uses sqlite3 or pysqlite2 package."""
	def __init__(self):
		dBackend.__init__(self)
		self.dbModuleName = "pysqlite2"
		try:
			from pysqlite2 import dbapi2 as dbapi
		except ImportError:
			import sqlite3 as dbapi
		self.dbapi = dbapi
		self._alreadyCorrectedFieldTypes = True
		

	def getConnection(self, connectInfo, **kwargs):
		## Mods to sqlite to return DictCursors by default, so that dCursor doesn't
		## need to do the conversion:
		dbapi = self.dbapi

		def dict_factory(cursor, row):
			_types = getattr(cursor, "_types", {})
			ret = {}
			fieldNames = (fld[0] for fld in cursor.description)
			for idx, field_name in enumerate(fieldNames):
				if _types:
					ret[field_name] = cursor._correctFieldType(row[idx], field_name, _newQuery=True)
				else:
					ret[field_name] = row[idx]
			return ret

		class DictCursor(self.dbapi.Cursor):
			def __init__(self, *args, **kwargs):
				dbapi.Cursor.__init__(self, *args, **kwargs)
				self.row_factory = dict_factory

		class DictConnection(self.dbapi.Connection):
			def __init__(self, *args, **kwargs):
				dbapi.Connection.__init__(self, *args, **kwargs)

			def cursor(self):
				return DictCursor(self)

		self._dictCursorClass = DictCursor
		pth = os.path.expanduser(connectInfo.Database)
		pth = pth.decode(sys.getfilesystemencoding()).encode("utf-8")
		# Need to specify "isolation_level=None" to have transactions working correctly.
		self._connection = self.dbapi.connect(pth, factory=DictConnection, isolation_level=None)
		return self._connection
		

	def getDictCursorClass(self):
		return self._dictCursorClass
		

	def formatForQuery(self, val):
		if isinstance(val, bool):
			return str(int(val))
		else:
			return super(SQLite, self).formatForQuery(val)


	def escQuote(self, val):			
		sl = "\\"
		qt = "\'"
		val = self._stringify(val)
		return qt + val.replace(sl, sl+sl).replace(qt, qt+qt) + qt
	
	
	def beginTransaction(self, cursor):
		""" Begin a SQL transaction. Since pysqlite does an implicit
		'begin' all the time, simply do nothing.
		"""
		cursor.execute("BEGIN")
		dabo.dbActivityLog.write("SQL: begin")
		return True


	def commitTransaction(self, cursor):
		""" Commit a SQL transaction."""
		opError = self.dbapi.OperationalError
		try:
			cursor.execute("COMMIT", errorClass=opError)
			dabo.dbActivityLog.write("SQL: commit")
			return True
		except opError, e:
			# There is no transaction active in this case, so ignore the error.
			pass
		except Exception, e:
			dabo.dbActivityLog.write("SQL: commit failed: %s" % e)
			raise dException.DBQueryException, e			


	def rollbackTransaction(self, cursor):
		""" Rollback a SQL transaction."""
		cursor.execute("ROLLBACK")
		dabo.dbActivityLog.write("SQL: rollback")
		return True

	
	def flush(self, crs):
		dabo.dbActivityLog.write("SQL: flush")
		self._connection.commit()


	def formatDateTime(self, val):
		""" We need to wrap the value in quotes. """
		sqt = "'"		# single quote
		val = self._stringify(val)
		return "%s%s%s" % (sqt, val, sqt)
		
	
	def _isExistingTable(self, tablename, cursor):
		cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=%s" % self.escQuote(tablename))
		rs = cursor.getDataSet()
		return len(rs) > 0
	
	
	def getTables(self, cursor, includeSystemTables=False):
		cursor.execute("select * from sqlite_master")
		rs = cursor.getDataSet()
		if includeSystemTables:
			tables = [rec["name"] for rec in rs 
					if rec["type"] == "table"]
		else:
			tables = [rec["name"] for rec in rs
					if rec["type"] == "table"
					and not rec["name"].startswith("sqlite_")]
		return tuple(tables)
		
		
	def getTableRecordCount(self, tableName, cursor):
		cursor.execute("select count(*) as ncount from %s" % tableName)
		return cursor.getDataSet(rows=1)["ncount"]


	def getFields(self, tableName, cursor):
		cursor.execute("pragma table_info('%s')" % tableName)
		rs = cursor.getDataSet()
		fields = []
		for rec in rs:
			typ = rec["type"].lower()
			if typ[:3] == "int":	
				fldType = "I"
			elif typ[:3] == "dec" or typ[:4] == "real":
				fldType = "N"
			elif typ == "blob":
				fldType = "L"
			elif typ[:4] == "clob" or typ[:8] == "longtext":
				fldType = "M"
			elif "bool" in typ:
				fldType = "B"
			else:
				# SQLite treats everything else as text
				fldType = "C"
			# Adi J. Sieker pointed out that the 'pk' column of the pragma command
			# returns a value indicating whether the field is the PK or not. This simplifies 
			# the routine over having to parse the CREATE TABLE code.
			fields.append( (rec["name"], fldType, bool(rec['pk'])) )
		return tuple(fields)


	def setNonUpdateFields(self, cursor):
		# Use an alternative, since grabbing an empty cursor, as is done in the 
		# default method, doesn't provide a  description. Assume that any field with 
		# the same name as the fields in the base table will be updatable.
		if not cursor.Table:
			# No table specified, so no update checking is possible
			return None
		# This is the current description of the cursor.
		descFlds = cursor.FieldDescription
		# Get the field info for the table
		auxCrs = cursor._getAuxCursor()
		auxCrs.execute("pragma table_info('%s')" % cursor.Table)
		rs = auxCrs._records

		stdFlds = [ff["name"] for ff in rs]
		# Get all the fields that are not in the table.
		return [d[0] for d in descFlds 
				if d[0] not in stdFlds ]
		
		
	def getUpdateTablePrefix(self, table, autoQuote=True):
		"""Table name prefixes are not allowed."""
		return ""
		
		
	def getWhereTablePrefix(self, table, autoQuote=True):
		"""Table name prefixes are not allowed."""
		return ""


	def noResultsOnSave(self):
		""" SQLite does not return anything on a successful update"""
		pass
		
		
	def createTableAndIndexes(self, tabledef, cursor, createTable=True, 
			createIndexes=True):
		if not tabledef.Name:
			raise
			
		#Create the table
		if createTable:
			if not tabledef.IsTemp:
				sql = "CREATE TABLE "
			else:
				sql = "CREATE TEMP TABLE "
			sql = sql + tabledef.Name + " ("
			
			for fld in tabledef.Fields:
				dont_esc = False
				sql = sql + fld.Name + " "
				
				if fld.DataType == "Numeric":
					sql = sql + "INTEGER "					
				elif fld.DataType == "Float":
					sql = sql + "REAL "
				elif fld.DataType == "Decimal":
					sql = sql + "TEXT "
				elif fld.DataType == "String":
					sql = sql + "TEXT "
				elif fld.DataType == "Date":
					sql = sql + "TEXT "
				elif fld.DataType == "Time":
					sql = sql + "TEXT "
				elif fld.DataType == "DateTime":
					sql = sql + "TEXT "
				elif fld.DataType == "Stamp":
					sql = sql + "TEXT "
					fld.Default = dNoEQ("CURRENT_TIMESTAMP")
				elif fld.DataType == "Binary":
					sql = sql + "BLOB "
				
				if fld.IsPK:
					sql = sql + "PRIMARY KEY "
					if fld.IsAutoIncrement:
						sql = sql + "AUTOINCREMENT "
				
				if not fld.AllowNulls:
					sql = sql + "NOT NULL "
				sql = "%sDEFAULT %s," % (sql, self.formatForQuery(fld.Default))
			if sql[-1:] == ",":
				sql = sql[:-1]
			sql = sql + ")"
			
			cursor.execute(sql)
			
	
		if createIndexes:
			#Create the indexes
			for idx in tabledef.Indexes:
				if idx.Name.lower() != "primary":
					sql = "CREATE INDEX " + idx.Name + " ON " + tabledef.Name + "("
					for fld in idx.Fields:
						sql = sql + fld + ","
					if sql[-1:] == ",":
						sql = sql[:-1]
					sql = sql + ")"
				
				cursor.execute(sql)