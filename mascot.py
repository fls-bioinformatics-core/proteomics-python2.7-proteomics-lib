#!/bin/env python
#
# -*- coding: utf-8 -*-
#
# Copyright (C) University of Manchester 2011 
#               Julian Selley <j.selley@manchester.ac.uk>
################################################################################

"""
Mascot module
=============
This module contains code related to interpreting Mascot information
and files.  Mascot is a piece of software produced by U{Matrix
Science(R) <http://www.matrixscience.com/>}, which is used in
Proteomics to search Mass Spectrometry data for potential peptide
identifications.

Description
-----------
Mass spectrometers take a set of molecules that have been isolated by
mass and charge, and fragment it by a high charged field. The ions
generated from the fragmentation of those molecules can be further
fragmented. If the ions that are subjected to the second level of
fragmentation originate from a peptide, they will further fragment
revealing mass / charge information related to the peptide sequence.

The spectra (the fragmentation pattern) from the second level of
fragmentation are sent to software to provide identifications on
peptide sequences, and ultimately on the proteins they belong to. In
Europe, the accepted software for doing this is Mascot, produced by a
company U{Matrix Science <http://www.matrixscience.com/>}. This
library provides an input into processing Mascot-related data.

This library provides the following functionality:
- reading the User and Group configuration files
- reading the search logs

Dependancies
------------
- In order to provide some cross-operating system functionality, this
library depends on C{os.path}, to identify the location of defaults
for the files being loaded.
- The library provides the ability to load in the logs and in order to
do this it depends on the C{csv} (Comma Separated Values) library.
- In order to manipilate the time stamps in the logs, this library
depends on the C{time} library.
- The library provides clases to load and interpret the User and Group
information. These files are XML, and thereby depend on
C{xml.dom.minidom} to facilitate their loading.
- The library provides debugging information via the C{logging}
library.

"""

# Metadata
__version__   = '1.0.1'
__author__    = 'Julian Selley <j.selley@manchester.ac.uk>'
__copyright__ = 'Copyright 2011 University of Manchester, Julian Selley <j.selley@manchester.ac.uk>'
__license__   = 'The Artistic License 2.0 (see the file LICENSE included with the distribution)'

# Imports
from os.path import join as pjoin
import csv
import logging
import time
import xml.dom.minidom

# Setup the logger
logger = logging.getLogger(__name__)

class Group:
    """A Mascot Group represented as a struct.

    The C{struct} stores the group _ID_, _name_ and a _list of User
    ID's_ associated with that group.

    The C{struct} has one overridden method to facilitate a clear
    print out of the data via C{print Group}.

    """
    id   = None  #: The numerical identification for the Mascot Group
    name = None  #: The name of the Mascot Group
    uids = []    #: A list of the user identifiers in the Mascot Group

    def __repr__(self):
        """Overrides the print functionality"""
        return "Group({0}): {1}, {2}".format(self.id, self.name, self.uids)

class GroupXMLInputFileReader:
    """File Reader for Mascot Group file.

    This class reads the Mascot group file (an XML file), and allows for
    querying the data contained therein. As the Group file is an XML file, this
    code is dependent on the library xml.dom.minidom, and is also written as a
    File Reader rather than as a Stream Reader object that would enable a
    slightly more flexible approach to coding.

    The code contained here in uses the logging module to create debugging
    information.

        >>> import proteomics.mascot
        >>> grp_reader = proteomics.mascot.GroupXMLInputFileReader('test_data/group.xml')
        >>> groups = grp_reader.readfile()

    """
    def __init__(self, filename = pjoin('data', 'group.xml')):
        """Constructor.

        Takes a filename (optional) detailing where the group file exists, in
        order to create the object.

        @param   filename: the filename of the group XML to open (default: 'I{data/group.xml}')
        @type    filename: str

        """
        self._filename = filename

    def read_file(self):
        """Reads the Mascot Group file.

        Reads the Mascot group file in (the filename for which the object was
        created with) and obtains the information contained therein.

        C{>>> groups = grp_reader.read_file()}

        @return: the list of groups contained in the file.
        @rtype:  the list of Groups (L{Group})

        """
        _grps = []
        __group_doc = xml.dom.minidom.parse(self._filename)  # the group DOM
        __grp = None  # a representation (struct) of a group
        # for each "mss:group_data" node in the XML
        for node in __group_doc.getElementsByTagName('mss:group_data'):
            # get every child node
            for childNode in node.childNodes:
                # go to the next node if it isn't an ELEMENT_NODE and isn't one
                # the specific informaiton of interest relating to groups
                if (childNode.nodeType != childNode.ELEMENT_NODE and 
                    childNode.localName != 'group_id' and
                    childNode.localName != 'group_name' and
                    childNode.localName != 'users'):
                    continue

                # if the node is about the group id
                if childNode.localName == 'group_id':
                    # if there was a previous group information, store it in
                    # the object
                    if (__grp != None):
                        _grps.append(__grp)
                        logger.debug("gid {0} stored".format(__grp.id))
                        logger.debug("group uids length: {0}".format(len(__grp.uids)))
                    # create a new group and store the group id
                    __grp = Group()
                    __grp.uids = []  # required because uids is a pointer that needs resetting
                    __grp.id = int(childNode.childNodes[0].data)
                    logger.debug("setting gid: %s",
                                 childNode.childNodes[0].data)
                # elif the node is the group name, set the group name
                elif childNode.localName == 'group_name':
                    __grp.name = childNode.childNodes[0].data
                    logger.debug("(gid: %s) name defined: %s",
                                 __grp.id, childNode.childNodes[0].data)
                # elif the node is about the associated users
                elif childNode.localName == 'users':
                    # get all the user childNodes ("mss:user_id"), and store the
                    # uid's
                    for user in childNode.childNodes:
                        if user.nodeType == user.ELEMENT_NODE and user.localName == "user_id":
                            __grp.uids.append(int(user.childNodes[0].data))
                            logger.debug("(gid: %s) uid added: %s",
                                         __grp.id, user.childNodes[0].data)
        # store the last group
        _grps.append(__grp)
        logger.debug("gid {0} stored".format(__grp.id))

        # return the groups read in
        return _grps

class LogEntry:
    """A Mascot Log entry represented as a struct.

    A log entry (a row) from the Mascot log file, represented as each
    column of the row.
    """
    searchid   = None
    pid        = None
    database   = None
    username   = None
    useremail  = None
    title      = None
    filename   = None
    start      = None
    duration   = None
    status     = None
    priority   = None
    searchtype = None
    enzyme     = None
    ipaddr     = None
    uid        = None

class LogInputFileReader:
    """File Stream Reader for Mascot log files.

    Reads the log file as a "stream"-type reader. It opens up the file, reads
    it into memory and then uses the CSV module to parse through it. It returns
    each row of the log file as a LogEntry, and works by iteration through the
    file.

    When implementing code using this class, it is intended that the user
    implements it in a try ... except ... clause. The iteration will throw a
    StopIteration when it gets to the end of the log file.

    The code does some rudimentry checking on the data and casts data into
    relevant data types rather than keeping them all as str. The code has also
    been set up to record the number of log entries within the object. It works
    with the `len` function.

        >>> import proteomics.mascot
        >>> logs = []
        >>> log_reader = proteomics.mascot.LogInputFileReader('test_data/searches.log')
        >>> for log_entry in log_reader:
        ...     try:
        ...         logs.append(log_entry)
        ...     except StopIteration:
        ...         pass

    """
    def __init__(self, filename = pjoin('data', 'logs', 'searches.log')):
        """Constructor.

        Takes a filename (optional) detailing where the log file exists, in
        order to create the object. The constructor then loads the entire file
        and parses it using the CSV module. It is the list of elements for each
        row, that the module stores in memory. It also stores the number of
        rows in a private variable ('_len'). Finally, it closes the file.

        @param   filename: the filename of the log file to open (default: 'I{data/logs/searches.log}')
        @type    filename: str

        """
        self._rows = []
        self._len = 0
        self._rowi = 0
        file = open(filename, 'rb')
        _csv = csv.reader(file, delimiter = '\t')
        for _row in _csv:
            self._rows.append(_row)
            self._len += 1
        file.close()

    def __len__(self):
        """Returns the number of log entries (rows in the file).

        This method facilitates the use of the C{len} function with
        this object.

        """
        return self._len

    def __iter__(self):
        """Allows for iteration throught the rows of the log file.

        This allows a C{for} loop to be conducted on this object, as
        with a list. It basically is the equivilent of implementing an
        C{iterator} interface in Java.

        """
        return self

    def next(self):
        """Move on to the next row of the log file.

        Part of the iteration interface: this method passes back the
        next row of the log file, returning a LogEntry.

        @return: the next log entry
        @rtype:  L{LogEntry} struct

        """
        # check that the row index (_rowi) is not at the end of the file; raise
        # an exception if it is
        if self._rowi >= len(self):
            raise StopIteration
        # create the LogEntry object
        _logentry = LogEntry()
        # populate the log entry
        _logentry.searchid   = long(self._rows[self._rowi][0])
        _logentry.pid        = long(self._rows[self._rowi][1])
        _logentry.database   = self._rows[self._rowi][2]
        _logentry.username   = self._rows[self._rowi][3]
        _logentry.useremail  = self._rows[self._rowi][4]
        _logentry.title      = self._rows[self._rowi][5]
        _logentry.filename   = self._rows[self._rowi][6]
        _logentry.start      = time.strptime(self._rows[self._rowi][7], "%a %b %d %H:%M:%S %Y")
        _logentry.duration   = int(self._rows[self._rowi][8])
        _logentry.status     = self._rows[self._rowi][9]
        _logentry.priority   = int(self._rows[self._rowi][10])
        _logentry.searchtype = self._rows[self._rowi][11]
        _logentry.enzyme     = self._rows[self._rowi][12]
        _logentry.ipaddr     = self._rows[self._rowi][13]
        _logentry.uid        = int(self._rows[self._rowi][14])
        # increment the current row index to allow us to move to the next line
        # next iteration
        self._rowi += 1

        # return the log entry
        return _logentry

    def read_file(self):
        """Reads the log file.

        Reads the Mascot Log file and returns a list of log entries.

        C{>>> logs = log_reader.read_file()}

        @return: the list of log entries
        @rtype:  list of LogEntries (L{LogEntry})

        """
        # sets up a list of logs
        _logs = []
        # iterate through and append the log_entries to the list of logs
        for _log_entry in self:
            # do in a try: ... except ...: loop to catch the StopIteration
            try:
                _logs.append(_log_entry)
            except StopIteration:
                pass

        # return the log entries
        return _logs

    def reset(self, idx = 0):
        """Reset the search log row pointer.

        Reset the search log pointer (back to 0 by default).

        @param   idx: the index to reset the pointer to (default: 0).
        @type    idx: int

        """
        self._rowi = idx

class User:
    """A Mascot User represented as a struct.

    The C{struct} stores the user _ID_, _username_, _full name_, and
    _e-mail_ address.

    The C{struct} has one overridden method to facilitate a clear
    print out of the data via C{print User}.

    """
    id       = None
    username = None
    fullname = None
    email    = None

    def __repr__(self):
        """Overrides the print functionality"""
        return "User({0}): {1} ({2} <{3}>)".format(self.id, self.username,
                                                   self.fullname, self.email)

class UserXMLInputFileReader:
    """File Reader for Mascot User file.

    This class reads the Mascot user file (an XML file), and allows for
    querying the data contained therein. As the User file is an XML file, this
    code is dependent on the library xml.dom.minidom, and is also written as a
    File Reader rather than as a Stream Reader object that would enable a
    slightly more flexible approach to coding.

    The code contained here in uses the logging module to create debugging
    information.

        >>> import proteomics.mascot
        >>> usr_reader = proteomics.mascot.UserXMLInputFileReader('test_data/user.xml')
        >>> users = usr_reader.readfile()

    """
    def __init__(self, filename = pjoin('data', 'user.xml')):
        """Constructor.

        Takes a filename (optional) detailing where the user file exists, in
        order to create the object.

        @param   filename: the filename of the user XML to open (default: 'I{data/user.xml}').
        @type    filename: str

        """
        self._filename = filename

    def read_file(self):
        """Reads the Mascot User file.

        Reads the Mascot user file in (the filename for which the object was
        created with) and obtains the information contained therein.

        C{>>> users = usr_reader.read_file()}

        @return: the list of users contained in the file.
        @rtype:  list of Users (L{User})

        """
        _usrs = []
        __user_doc = xml.dom.minidom.parse(self._filename)  # the user DOM
        __usr = None  # a representation (struct) of a user

        # for each "mss:user_data" node in the XML
        for node in __user_doc.getElementsByTagName('mss:user_data'):
            # get every child node
            for childNode in node.childNodes:
                # go to the next node if it isn't an ELEMENT_NODE and isn't one
                # the specific informaiton of interest relating to userss
                if (childNode.nodeType != childNode.ELEMENT_NODE and 
                    childNode.localName != 'userID' and
                    childNode.localName != 'userName' and
                    childNode.localName != 'fullName' and
                    childNode.localName != 'emailAddress'):
                    continue

                # if the node is about the user id
                if childNode.localName == 'userID':
                    # if there was a previous user information, store it in
                    # the object
                    if (__usr != None):
                        _usrs.append(__usr)
                        logger.debug("uid {0} stored".format(__usr.id))
                    # create a new user and store the user id
                    __usr = User()
                    __usr.id = int(childNode.childNodes[0].data)
                    logger.debug("setting uid: %s",
                                 childNode.childNodes[0].data)
                # elif the node is the user name, set the user name
                elif childNode.localName == 'userName':
                    __usr.username = childNode.childNodes[0].data
                    logger.debug("(uid: %s) name defined: %s",
                                 __usr.id, childNode.childNodes[0].data)
                # elif the node is the full name, set the user's full name
                elif childNode.localName == 'fullName':
                    __usr.fullname = childNode.childNodes[0].data
                    logger.debug("(uid: %s) fullname defined: %s",
                                 __usr.id, childNode.childNodes[0].data)
                # elif the node is the email address, set the user's e-mail
                elif childNode.localName == 'emailAddress':
                    try:
                        __usr.email = childNode.childNodes[0].data
                        logger.debug("(uid: %s) email defined: %s",
                                     __usr.id, childNode.childNodes[0].data)
                    except IndexError:
                        pass
        # store the last user
        _usrs.append(__usr)
        logger.debug("uid {0} stored".format(__usr.id))

        # return the users read in
        return _usrs

#if __name__ == '__main__':
#    logging.basicConfig(level=logging.DEBUG)
#    
