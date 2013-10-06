#-*- coding: utf-8 -*-

# Copyright 2010 Bastian Bowe
#
# This file is part of JayDeBeApi.
# JayDeBeApi is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# JayDeBeApi is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with JayDeBeApi.  If not, see
# <http://www.gnu.org/licenses/>.

import jaydebeapi

import os
import sys
import threading

import unittest2 as unittest

this_dir = os.path.dirname(os.path.abspath(__file__))

def jar(jar_file):
    return os.path.abspath(os.path.join(this_dir, '..', '..', 'build', 'lib',
                                        jar_file))

_DRIVERS = {
    #http://bitbucket.org/xerial/sqlite-jdbc
    'sqlite_xerial': ( 'org.sqlite.JDBC', 'jdbc:sqlite::memory:',
                       jar('sqlite-jdbc-3.7.2.jar'), None),
    # http://hsqldb.org/
    'hsqldb': ( 'org.hsqldb.jdbcDriver', ['jdbc:hsqldb:mem:.', 'SA', ''],
                jar('hsqldb.jar'), None),
    'db2jcc': ( 'com.ibm.db2.jcc.DB2Driver',
                ['jdbc:db2://4.100.73.81:50000/db2t', 'user', 'passwd'],
                jar('jarfile.jar'), None),
    # driver from http://www.ch-werner.de/javasqlite/ seems to be
    # crap as it returns decimal values as VARCHAR type
    'sqlite_werner': ( 'SQLite.JDBCDriver', 'jdbc:sqlite:/:memory:',
                       jar('sqlite.jar'), None),
    # Oracle Thin Driver
    'oracle_thin': ('oracle.jdbc.OracleDriver',
                    ['jdbc:oracle:thin:@//hh-cluster-scan:1521/HH_TPP',
                     'user', 'passwd'],
                    jar('jarfile.jar'), None)
    }

def is_jython():
    return sys.platform.lower().startswith('java')

def driver_name():
    try:
        return os.environ['INTEGRATION_TEST_DRIVER']
    except KeyError:
        return 'sqlite_xerial'

class IntegrationTest(unittest.TestCase):

    def sql_file(self, filename):
        f = open(filename, 'r')
        try:
            lines = f.readlines()
        finally:
            f.close()
        stmt = []
        stmts = []
        for i in lines:
            stmt.append(i)
            if ";" in i:
                stmts.append(" ".join(stmt))
                stmt = []
        cursor = self.conn.cursor()
        for i in stmts:
            cursor.execute(i)

    def connect(self):
        # rename the latter connect method to run tests against
        # pysqlite
        msg = "Warinng: Your are not running the tests against JayDeBeApi."
        print >> sys.stderr, msg
        import sqlite3
        return sqlite3, sqlite3.connect(':memory:')

    def connect(self):
        driver = driver_name()
        driver_class, driver_args, driver_jars, driver_libs = _DRIVERS[driver]
        conn = jaydebeapi.connect(driver_class, driver_args, driver_jars,
                                  driver_libs)
        return jaydebeapi, conn

    def _driver_specific_sql(self, data_file):
        driver = driver_name()
        sql_file = os.path.join(this_dir, 'data', '%s_%s.sql' % (data_file,
                                                                 driver))
        if os.path.exists(sql_file):
            return sql_file
        else:
            return os.path.join(this_dir, 'data', '%s.sql' % data_file)

    def setUp(self):
        (self.dbapi, self.conn) = self.connect() 
        create_sql = self._driver_specific_sql('create')
        self.sql_file(create_sql)
        insert_sql = self._driver_specific_sql('insert')
        self.sql_file(insert_sql)

    def tearDown(self):
        cursor = self.conn.cursor()
        cursor.execute("drop table ACCOUNT");
        self.conn.close()

    def test_execute_and_fetch_no_data(self):
        cursor = self.conn.cursor()
        stmt = "select * from ACCOUNT where ACCOUNT_ID is null"
        cursor.execute(stmt)
        assert [] == cursor.fetchall()

    def test_execute_and_fetch(self):
        cursor = self.conn.cursor()
        cursor.execute("select ACCOUNT_ID, ACCOUNT_NO, BALANCE, BLOCKING " \
                       "from ACCOUNT")
        result = cursor.fetchall()
        assert [(u'2009-09-10 14:15:22.123456', 18, 12.4, None),
         (u'2009-09-11 14:15:22.123456', 19, 12.9, 1)] == result

    def test_execute_and_fetch_parameter(self):
        cursor = self.conn.cursor()
        cursor.execute("select ACCOUNT_ID, ACCOUNT_NO, BALANCE, BLOCKING " \
                       "from ACCOUNT where ACCOUNT_NO = ?", (18,))
        result = cursor.fetchall()
        assert [(u'2009-09-10 14:15:22.123456', 18, 12.4, None)] == result

    def test_execute_and_fetchone(self):
        cursor = self.conn.cursor()
        cursor.execute("select ACCOUNT_ID, ACCOUNT_NO, BALANCE, BLOCKING " \
                       "from ACCOUNT order by ACCOUNT_NO")
        result = cursor.fetchone()
        assert (u'2009-09-10 14:15:22.123456', 18, 12.4, None) == result
        cursor.close()

    def test_execute_reset_description_without_execute_result(self):
        """Excpect the descriptions property being reset when no query
        has been made via execute method.
        """
        cursor = self.conn.cursor()
        cursor.execute("select * from ACCOUNT")
        assert None != cursor.description
        cursor.fetchone()
        cursor.execute("delete from ACCOUNT")
        assert None == cursor.description

    def test_execute_and_fetchone_after_end(self):
        cursor = self.conn.cursor()
        cursor.execute("select * from ACCOUNT where ACCOUNT_NO = ?", (18,))
        cursor.fetchone()
        result = cursor.fetchone()
        assert None is result

    def test_execute_and_fetchmany(self):
        cursor = self.conn.cursor()
        cursor.execute("select ACCOUNT_ID, ACCOUNT_NO, BALANCE, BLOCKING " \
                       "from ACCOUNT order by ACCOUNT_NO")
        result = cursor.fetchmany()
        assert [(u'2009-09-10 14:15:22.123456', 18, 12.4, None)] == result
        # TODO: find out why this cursor has to be closed in order to
        # let this test work with sqlite if __del__ is not overridden
        # in cursor
        # cursor.close()

    def test_executemany(self):
        cursor = self.conn.cursor()
        stmt = "insert into ACCOUNT (ACCOUNT_ID, ACCOUNT_NO, BALANCE) " \
               "values (?, ?, ?)"
        parms = (
            ( '2009-09-11 14:15:22.123450', 20, 13.1 ),
            ( '2009-09-11 14:15:22.123451', 21, 13.2 ),
            ( '2009-09-11 14:15:22.123452', 22, 13.3 ),
            )
        cursor.executemany(stmt, parms)
        assert cursor.rowcount == 3

    def test_execute_types(self):
        cursor = self.conn.cursor()
        stmt = "insert into ACCOUNT (ACCOUNT_ID, ACCOUNT_NO, BALANCE, " \
               "BLOCKING, DBL_COL, OPENED_AT, VALID, PRODUCT_NAME) " \
               "values (?, ?, ?, ?, ?, ?, ?, ?)"
        d = self.dbapi
        account_id = d.Timestamp(2010, 01, 26, 14, 31, 59)
        account_no = 20
        balance = 1.2
        blocking = 10.0
        dbl_col = 3.5
        opened_at = d.Date(2008, 02, 27)
        valid = 1
        product_name = u'Savings account'
        parms = (account_id, account_no, balance, blocking, dbl_col,
                 opened_at, valid, product_name)
        cursor.execute(stmt, parms)
        stmt = "select ACCOUNT_ID, ACCOUNT_NO, BALANCE, BLOCKING, " \
               "DBL_COL, OPENED_AT, VALID, PRODUCT_NAME " \
               "from ACCOUNT where ACCOUNT_NO = ?"
        parms = (20, )
        cursor.execute(stmt, parms)
        result = cursor.fetchone()
        cursor.close()
        exp = ( '2010-01-26 14:31:59', account_no, balance, blocking,
                 dbl_col, '2008-02-27', valid, product_name )
        assert exp == result

    def test_execute_type_blob(self):
        cursor = self.conn.cursor()
        stmt = "insert into ACCOUNT (ACCOUNT_ID, ACCOUNT_NO, BALANCE, " \
               "STUFF) values (?, ?, ?, ?)"
        stuff = self.dbapi.Binary('abcdef')
        parms = ('2009-09-11 14:15:22.123450', 20, 13.1, stuff)
        cursor.execute(stmt, parms)
        stmt = "select STUFF from ACCOUNT where ACCOUNT_NO = ?"
        parms = (20, )
        cursor.execute(stmt, parms)
        result = cursor.fetchone()
        cursor.close()
        value = result[0]
        assert 'abcdef' == value

    def test_execute_different_rowcounts(self):
        cursor = self.conn.cursor()
        stmt = "insert into ACCOUNT (ACCOUNT_ID, ACCOUNT_NO, BALANCE) " \
               "values (?, ?, ?)"
        parms = (
            ( '2009-09-11 14:15:22.123450', 20, 13.1 ),
            ( '2009-09-11 14:15:22.123452', 22, 13.3 ),
            )
        cursor.executemany(stmt, parms)
        assert cursor.rowcount == 2
        parms = ( '2009-09-11 14:15:22.123451', 21, 13.2 )
        cursor.execute(stmt, parms)
        assert cursor.rowcount == 1
        cursor.execute("select * from ACCOUNT")
        assert cursor.rowcount == -1
