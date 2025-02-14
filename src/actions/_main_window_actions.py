#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright 2008 Martin Manns
# Distributed under the terms of the GNU General Public License
# generated by wxGlade 0.6 on Mon Mar 17 23:22:49 2008

# --------------------------------------------------------------------
# pyspread is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyspread is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyspread.  If not, see <http://www.gnu.org/licenses/>.
# --------------------------------------------------------------------


"""
_main_window_actions.py
=======================

Module for main window level actions.
All non-trivial functionality that results from main window actions
and belongs to the application as whole (in contrast to the grid only)
goes here.

Provides:
---------
  1. ExchangeActions: Actions for foreign format import and export
  2. PrintActions: Actions for printing
  3. ClipboardActions: Actions which affect the clipboard
  4. MacroActions: Actions which affect macros  
  5. HelpActions: Actions for getting help
  6. AllMainWindowActions: All main window actions as a bundle

"""

import csv
import os
import types

from copy import copy

import wx
import wx.html

from sysvars import get_help_path

from config import config
from lib._interfaces import Digest
from gui._printout import PrintCanvas, Printout
from gui._events import *


class CsvInterface(object):
    """CSV interface class
    
    Provides
    --------
     * __iter__: CSV reader - generator of generators of csv data cell content
     * write: CSV writer
    
    """
    
    def __init__(self, main_window, path, dialect, digest_types, has_header):
        self.main_window = main_window
        self.path = path
        self.csvfilename = os.path.split(path)[1]
        
        self.dialect = dialect
        self.digest_types = digest_types
        self.has_header = has_header
        
        self.first_line = False
        
    def __iter__(self):
        """Generator of generators that yield csv data"""
        
        try:
            csv_file = open(self.path, "r")
            csv_reader = csv.reader(csv_file, self.dialect)
            
        except IOError, err:
            statustext = "Error opening file " + self.path + "."
            post_command_event(self.main_window, StatusBarMsg, text=statustext)
            
            csv_file = [] 
        
        self.first_line = self.has_header
        
        try:
            for line in csv_reader:
                yield self._get_csv_cells_gen(line)
                self.first_line = False
                                              
        except Exception, err:
            msg = 'The file "' + self.csvfilename + '" only partly loaded.' + \
                  '\n \nError message:\n' + str(err)
            short_msg = 'Error reading CSV file'
            self.main_window.interfaces.display_warning(msg, short_msg)
        
        finally:
            statustext = "File " + self.csvfilename + " imported successfully."
            post_command_event(self.main_window, StatusBarMsg, text=statustext)
        
        csv_file.close()
    
    def _get_csv_cells_gen(self, line):
        """Generator of values in a csv line"""
        
        digest_types = self.digest_types
        
        for j, value in enumerate(line):
            if self.first_line:
                digest_key = None
                digest = lambda x: x
            else:
                try:
                    digest_key = digest_types[j]
                except IndexError:
                    digest_key = digest_types[0]
                    
                digest = Digest(acceptable_types=[digest_key])
                
            try:
                digest_res = digest(value)
                
                if digest_key is not None and digest_res != "\b" and \
                   digest_key is not types.CodeType:
                    digest_res = repr(digest_res)
                elif digest_res == "\b":
                    digest_res = None
                
            except Exception, err:
                digest_res = str(err)
            
            yield digest_res
    
    def write(self, iterable):
        """Writes values from iterable into CSV file"""
        
        csvfile = open(self.path, "wb")
        csv_writer = csv.writer(csvfile, self.dialect)
        
        for line in iterable:
            csv_writer.writerow(line)
        
        csvfile.close()


class TxtGenerator(object):
    """Generator of generators of Whitespace separated txt file cell content"""
        
    def __init__(self, main_window, path):
        self.main_window = main_window
        try:
            self.infile = open(path, "r")
            
        except IOError, err:
            statustext = "Error opening file " + path + "."
            post_command_event(self.main_window, StatusBarMsg, text=statustext)
            self.infile = []

    def __iter__(self):
        for line in self.infile:
            for col in line.split():
                yield col
        
        infile.close()

class ExchangeActions(object):
    """Actions for foreign format import and export"""
    
    def _import_csv(self, path):
        """CSV import workflow"""

        # Get csv info
        
        try:
            dialect, has_header, digest_types = \
                self.main_window.interfaces.get_csv_import_info(path)
                
        except TypeError:
            return
            
        except IOError, err:
            statustext = "Error opening file " + path + "."
            post_command_event(self.main_window, StatusBarMsg, text=statustext)
            return
        
        return CsvInterface(self.main_window, 
                            path, dialect, digest_types, has_header)
    
    def _import_txt(self, path):
        """Whitespace-delimited txt import workflow. This should be fast."""
        
        return TxtGenerator(path)
    
    def import_file(self, filepath, filterindex):
        """Imports external file
        
        Parameters
        ----------
        
        filepath: String
        \tPath of import file
        filterindex: Integer
        \tIndex for type of file, 0: csv, 1: tab-delimited text file
        
        """
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        if filterindex == 0:
            # CSV import option choice
            return self._import_csv(filepath)
        elif filterindex == 1:
            # TXT import option choice
            return self._import_txt(filepath)
        else:
            msg = "Unknown import choice" + str(filterindex)
            short_msg = 'Error reading CSV file'
            
            self.main_window.interfaces.display_warning(msg, short_msg)


    def _export_csv(self, filepath, data):
        """CSV import workflow"""

        # Get csv info
        
        csv_info = self.main_window.interfaces.get_csv_export_info(data)
        
        if csv_info is None:
            return
        
        try:
            dialect, digest_types, has_header = csv_info
        except TypeError:
            return
        
        # Export CSV file
        
        csv_interface = CsvInterface(filepath, dialect, digest_types, 
                                     has_header)
        
        try:
            csv_interface.write(data)
            
        except IOError, err:
            msg = 'The file "' + path + '" could not be fully written ' + \
                  '\n \nError message:\n' + str(err)
            short_msg = 'Error writing CSV file'
            self.main_window.interfaces.display_warning(msg, short_msg)

    def export_file(self, filepath, filterindex, data):
        """Exports external file. Only CSV supported yet."""
        
        self._export_csv(filepath, data)


class PrintActions(object):
    """Actions for printing"""
    
    def print_preview(self, print_area, print_data):
        """Launch print preview"""
        
        pdd = wx.PrintDialogData(print_data)
        
        # Create the print canvas
        canvas = PrintCanvas(self.main_window, self.grid, print_area)
        
        printout = Printout(canvas)
        printout2 = Printout(canvas)
        
        self.preview = wx.PrintPreview(printout, printout2, print_data)

        if not self.preview.Ok():
            print "Houston, we have a problem...\n"
            return

        pfrm = wx.PreviewFrame(self.preview, self.main_window, "Print preview")

        pfrm.Initialize()
        pfrm.SetPosition(self.main_window.GetPosition())
        pfrm.SetSize(self.main_window.GetSize())
        pfrm.Show(True)
    
    def printout(self, print_area, print_data):
        """Print out print area
        
        See:
        http://aspn.activestate.com/ASPN/Mail/Message/wxpython-users/3471083
        
        """
        
        pdd = wx.PrintDialogData(print_data)
        printer = wx.Printer(pdd)
        
        # Create the print canvas
        canvas = PrintCanvas(self.main_window, self.grid, print_area)
        
        printout = Printout(canvas)
        
        if printer.Print(self.main_window, printout, True):
            self.print_data = \
                wx.PrintData(printer.GetPrintDialogData().GetPrintData())
        
        printout.Destroy()
        canvas.Destroy()


class ClipboardActions(object):
    """Actions which affect the clipboard"""
    
    def cut(self, selection):
        """Cuts selected cells and returns data in a tab separated string
        
        Parameters
        ----------
        
        selection: Selection object
        \tSelection of cells in current table that shall be copied
        
        """
        
        # Call copy with delete flag
        
        return self.copy(selection, delete=True)
    
    def _get_code(self, key):
        """Returns code for given key (one cell)
        
        Parameters
        ----------
        
        key: 3-Tuple of Integer
        \t Cell key
        
        """
        
        data = self.grid.code_array(key)
        self.grid.code_array.result_cache.clear()
        
        return data
    
    def copy(self, selection, getter=None, delete=False):
        """Returns code from selection in a tab separated string
        
        Cells that are not in selection are included as empty.
        
        Parameters
        ----------
        
        selection: Selection object
        \tSelection of cells in current table that shall be copied
        getter: Function, defaults to _get_code
        \tGetter function for copy content
        delete: Bool
        \tDeletes all cells inside selection
        
        """
        
        if getter is None:
            getter = self._get_code
        
        tab = self.grid.current_table
        
        selection_bbox = selection.get_bbox()
        
        if not selection_bbox:
            # There is no selection
            bb_top, bb_left = self.grid.actions.cursor[:2]
            bb_bottom, bb_right = bb_top, bb_left
        else:
            replace_none = self.main_window.grid.actions._replace_bbox_none
            (bb_top, bb_left), (bb_bottom, bb_right) = \
                            replace_none(selection.get_bbox())
        
        data = []
        
        for __row in xrange(bb_top, bb_bottom + 1):
            data.append([])
            
            for __col in xrange(bb_left, bb_right + 1):
                # Only copy content if cell is in selection or 
                # if there is no selection
                
                if (__row, __col) in selection or not selection_bbox:
                    content = getter((__row, __col, tab))
                    
                    # Delete cell if delete flag is set
                    
                    if delete:
                        try:
                            self.grid.code_array.pop((__row, __col, tab))
                        
                        except KeyError:
                            pass
                    
                    # Store data
                    
                    if content is None:
                        data[-1].append(u"")
                        
                    else:
                        data[-1].append(content)
                        
                else:
                    data[-1].append(u"")
        
        return "\n".join("\t".join(line) for line in data)
    
    def _get_result_string(self, key):
        """Returns unicode string of result for given key (one cell)
        
        Parameters
        ----------
        
        key: 3-Tuple of Integer
        \t Cell key
        
        """
        
        row, col, tab = key
        
        return unicode(self.grid.code_array[row, col, tab])
    
    def copy_result(self, selection):
        """Returns result strings from selection in a tab separated string"""
        
        getter = self._get_result_string
        
        return self.copy(selection, getter=getter)
    
    def paste(self, key, data):
        """Pastes data into grid
        
        Parameters
        ----------
        
        key: 2-Tuple of Integer
        \tTop left cell
        data: String
        \tTab separated string of paste data
        """
        
        data_gen = (line.split("\t") for line in data.split("\n"))
        
        self.grid.actions.paste(key[:2], data_gen)
        
        self.main_window.grid.ForceRefresh()

class MacroActions(object):
    """Actions which affect macros"""
    
    def replace_macros(self, macros):
        """Replaces macros"""
        
        self.grid.code_array.macros = macros
        
    def execute_macros(self):
        """Executes macros and marks grid as changed"""
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        self.grid.code_array.execute_macros()
    
    def open_macros(self, filepath):
        """Loads macros from file and marks grid as changed
        
        Parameters
        ----------
        filepath: String
        \tPath to macro file
        
        """
        
        try:
            macro_infile = open(filepath, "r")
            
        except IOError, err:
            statustext = "Error opening file " + filepath + "."
            post_command_event(self.main_window, StatusBarMsg, text=statustext)
            
            return False
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        macrocode = macro_infile.read()
        macro_infile.close()
        
        self.grid.code_array.macros += "\n" + macrocode.strip("\n")
        
    def save_macros(self, filepath, macros):
        """Saves macros to file
        
        Parameters
        ----------
        filepath: String
        \tPath to macro file
        macros: String
        \tMacro code
        
        """
        
        macro_outfile = open(filepath, "w")
        macro_outfile.write(macros)
        macro_outfile.close()


class HelpActions(object):
    """Actions for getting help"""
    
    def launch_help(self, helpname, filename):
        """Generic help launcher
        
        Launches HTMLWindow that shows content of filename 
        or the Internet page with the filename url
        
        Parameters
        ----------
        
        filename: String
        \thtml file or url
        
        """
        
        # Set up window
        
        position = config["help_window_position"]
        size = config["help_window_size"]
        
        help_window = wx.Frame(self.main_window, -1, helpname, position, size)
        help_htmlwindow = wx.html.HtmlWindow(help_window, -1, (0, 0), size)
        
        help_window.Bind(wx.EVT_MOVE, self.OnHelpMove)
        help_window.Bind(wx.EVT_SIZE, self.OnHelpSize)
        
        # Get help data
        current_path = os.getcwd()
        os.chdir(get_help_path())
        
        try:
            help_file = open(filename, "r")
            help_html = help_file.read()
            help_file.close()
            help_htmlwindow.SetPage(help_html)
        
        except IOError:
            
            help_htmlwindow.LoadPage(filename)
        
        # Show tutorial window
        
        help_window.Show()
        
        os.chdir(current_path)
    
    def OnHelpMove(self, event):
        """Help window move event handler stores position in config"""
        
        config["help_window_position"] = repr(event.GetPosition())
        
    def OnHelpSize(self, event):
        """Help window size event handler stores size in config"""
        
        config["help_window_size"] = repr(event.GetSize())
    
class AllMainWindowActions(ExchangeActions, PrintActions, 
                           ClipboardActions, MacroActions, HelpActions):
    """All main window actions as a bundle"""
    
    def __init__(self, main_window, grid):
        self.main_window = main_window
        self.grid = grid
        
        ExchangeActions.__init__(self)
        PrintActions.__init__(self)
        ClipboardActions.__init__(self)
        MacroActions.__init__(self)
        HelpActions.__init__(self)
        
