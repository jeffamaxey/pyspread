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
_grid_actions.py
=======================

Module for main main grid level actions.
All non-trivial functionality that results from grid actions
and belongs to the grid only goes here.

Provides:
---------
  1. FileActions: Actions which affect the open grid
  2. TableRowActionsMixin: Mixin for TableActions
  3. TableColumnActionsMixin: Mixin for TableActions
  4. TableTabActionsMixin: Mixin for TableActions
  5. TableActions: Actions which affect table
  6. MacroActions: Actions on macros
  7. UnRedoActions: Actions on the undo redo system
  8. GridActions: Actions on the grid as a whole
  9. SelectionActions: Actions on the grid selection
  10. FindActions: Actions for finding and replacing
  11. AllGridActions: All grid actions as a bundle
  

"""

import bz2
from copy import copy

from config import config

from gui._grid_table import GridTable
from gui._events import *
from lib._interfaces import sign, verify, is_pyme_present, get_font_from_data

from lib.selection import Selection
from model.model import DictGrid

from actions._grid_cell_actions import CellActions

class FileActions(object):
    """File actions on the grid"""
    
    def __init__(self):
        self.saving = False
        
        self.main_window.Bind(EVT_COMMAND_GRID_ACTION_OPEN, self.open) 
        self.main_window.Bind(EVT_COMMAND_GRID_ACTION_SAVE, self.save)

    def validate_signature(self, filename):
        """Returns True if a valid signature is present for filename"""
        
        sigfilename = filename + '.sig'
        
        try:
            dummy = open(sigfilename)
            dummy.close()
        except IOError:
            # Signature file does not exist
            return False
        
        # Check if the sig is valid for the sigfile
        return verify(sigfilename, filename)

    def enter_safe_mode(self):
        """Enters safe mode"""
        
        self.code_array.safe_mode = True

    def leave_safe_mode(self):
        """Leaves save mode"""
        
        self.code_array.safe_mode = False
        post_command_event(self.main_window, SafeModeExitMsg)
        
    def approve(self, filepath):
        """Sets safe mode if signature missing of invalid"""
        
        if self.validate_signature(filepath):
            self.leave_safe_mode()
            post_command_event(self.main_window, SafeModeExitMsg)
            
            statustext = "Valid signature found. File is trusted."
            post_command_event(self.main_window, StatusBarMsg, text=statustext)
            
        else:
            self.enter_safe_mode()
            post_command_event(self.main_window, SafeModeEntryMsg)
            
            statustext = "File is not properly signed. Safe mode " + \
                         "activated. Select File -> Approve to leave safe mode."
            post_command_event(self.main_window, StatusBarMsg, text=statustext)

    def _get_file_version(self, infile):
        """Returns infile version string."""
        
        # Determine file version
        for line1 in infile:
            break
        for line2 in infile:
            break
        
        if line1.strip() != "[Pyspread save file version]":
            errortext = "File format unsupported. " + filepath + \
                " seems not to be a pyspread save file version 0.1."
            raise ValueError, errortext
        
        return line2.strip()

    def _abort_open(self, filepath, infile):
        """Aborts file open"""
        
        statustext = "File loading aborted."
        post_command_event(self.main_window, StatusBarMsg, 
                           text=statustext)
        
        infile.close()
        
        self.opening = False
        self.need_abort = False

    def _empty_grid(self, shape):
        """Empties grid and sets shape to shape"""
        
        self.code_array.dict_grid.clear()
        c_a = self.code_array.dict_grid.cell_attributes
        [c_a.pop() for _ in xrange(len(c_a))]
        self.code_array.unredo.reset()
        self.code_array.result_cache.clear()

    
    def open(self, event):
        """Opens a file that is specified in event.attr
        
        Parameters
        ----------
        event.attr: Dict
        \tkey filepath contains file path of file to be loaded
        
        """
        
        filepath = event.attr["filepath"]
        
        # Set states for file open
        
        self.opening = True
        self.need_abort = False
        
        # Print this on IOErrors when reading from the infile
        ioerror_statustext = "Error reading from file " + filepath + "."
        
        try:
            infile = bz2.BZ2File(filepath, "r")
            
        except IOError:
            statustext = "Error opening file " + filepath + "."
            post_command_event(self.main_window, StatusBarMsg, text=statustext)
            
            return False
        
        # Make loading safe
        self.approve(filepath)
        
        # Abort if file version not supported
        try:
            version = self._get_file_version(infile)
            if version != "0.1":
                statustext = "File version " + version + \
                             "unsupported (not 0.1)."
                post_command_event(self.main_window, StatusBarMsg, 
                                   text=statustext)
                return False
            
        except (IOError, ValueError), errortext:
            post_command_event(self.main_window, StatusBarMsg, text=errortext)
        
        # Parse content

        def parser(*args):
            """Dummy parser. Raises ValueError"""
            
            raise ValueError_grid_actions.py, "No section parser present."

        section_readers = { \
            "[shape]": self.code_array.dict_grid.parse_to_shape,
            "[grid]": self.code_array.dict_grid.parse_to_grid,
            "[attributes]": self.code_array.dict_grid.parse_to_attribute,
            "[row_heights]": self.code_array.dict_grid.parse_to_height,
            "[col_widths]": self.code_array.dict_grid.parse_to_width,
            "[macros]": self.code_array.dict_grid.parse_to_macro,
        }
        
        # Disable undo
        self.grid.code_array.unredo.active = True
        
        try:
            for cycle, line in enumerate(infile):
                stripped_line = line.decode("utf-8").strip()
                if stripped_line:
                    # There is content in this line
                    if stripped_line in section_readers:
                        # Switch parser
                        parser = section_readers[stripped_line]
                    else:
                        # Parse line
                        parser(line)
                        if parser == self.code_array.dict_grid.parse_to_shape:
                            # Empty grid
                            self._empty_grid(self.code_array.shape)
                            
                            self.grid.GetTable().ResetView()
                else:
                   pass
                
                # Enable abort during long saves
                if self._is_aborted(cycle, "Loading file... "):
                    self._abort_open(filepath, infile)
                    return False
        
        except IOError:
            statustext = "Error opening file " + filepath + "."
            post_command_event(self.main_window, StatusBarMsg, text=statustext)
            
            return False
        
        infile.close()
        self.opening = False
        
        # Enable undo again
        self.grid.code_array.unredo.active = False
        
        self.grid.GetTable().ResetView()
        self.grid.ForceRefresh()
        
        # File sucessfully opened. Approve again to show status.
        self.approve(filepath)
        
    def sign_file(self, filepath):
        """Signs file if possible"""
        
        if is_pyme_present() and not self.code_array.safe_mode:
            signature = sign(filepath)
            signfile = open(filepath + '.sig','wb')
            signfile.write(signature)
            signfile.close()
            msg = 'File successfully saved and signed.'
            statustext = 'File saved and signed'
            post_command_event(self.main_window, StatusBarMsg, 
                               text=statustext)
        else:
            msg = 'Cannot sign the file. Maybe PyMe is not installed.'
            short_msg = 'Cannot sign file!'
            self.main_window.interfaces.display_warning(msg, short_msg)

    def _abort_save(self, filepath, outfile):
        """Aborts file save"""
        
        statustext = "Save aborted."
        post_command_event(self.main_window, StatusBarMsg, 
                           text=statustext)
        
        outfile.close()
        os.remove(filepath)
        
        self.saving = False
        self.need_abort = False
    
    def save(self, event):
        """Saves a file that is specified in event.attr
        
        Parameters
        ----------
        event.attr: Dict
        \tkey filepath contains file path of file to be saved
        
        """
        
        filepath = event.attr["filepath"]
        
        dict_grid = self.code_array.dict_grid
        
        self.saving = True
        self.need_abort = False
        
        # Print this on IOErrors when writing to the outfile
        ioerror_statustext = "Error writing to file " + filepath + "."
        
        # Save file is compressed
        try:
            outfile = bz2.BZ2File(filepath, "wb")
            
        except IOError:
            statustext = "Error opening file " + filepath + "."
            post_command_event(self.main_window, StatusBarMsg, text=statustext)
            return False
    
        # Header
        try:
            outfile.write("[Pyspread save file version]\n")
            outfile.write("0.1\n")
            
        except IOError:
            post_command_event(self.main_window, StatusBarMsg, 
                               text=ioerror_statustext)
            return False
        
        # The output generators yield the lines for the outfile
        output_generators = [ \
            # Grid content
            dict_grid.grid_to_strings(),
            # Cell attributes
            dict_grid.attributes_to_strings(),
            # Row heights
            dict_grid.heights_to_strings(),
            # Column widths
            dict_grid.widths_to_strings(),
            # Macros
            dict_grid.macros_to_strings(),
        ]
        
        # Options for self._is_aborted
        abort_options_list = [ \
            ["Saving grid... ", len(dict_grid), 100000],
            ["Saving cell attributes... ", len(dict_grid.cell_attributes)],
            ["Saving row heights... ", len(dict_grid.row_heights)],
            ["Saving column widths... ", len(dict_grid.col_widths)],
            ["Saving macros... ", dict_grid.macros.count("\n")],
        ]
        
        # Save cycle
        
        for generator, options in zip(output_generators, abort_options_list):
            for cycle, line in enumerate(generator):
                try:
                    outfile.write(line.encode("utf-8"))
                    
                except IOError:
                    post_command_event(self.main_window, StatusBarMsg, 
                                       text=ioerror_statustext)
                    return False
                
                # Enable abort during long saves
                if self._is_aborted(cycle, *options):
                    self._abort_save(filepath, outfile)
                    return False

        # Save is done

        outfile.close()
        
        self.saving = False
        
        # Mark content as unchanged
        post_command_event(self.main_window, ContentChangedMsg, changed=False)
        
        # Sign so that the new file may be retrieved without safe mode
        
        self.sign_file(filepath)


class TableRowActionsMixin(object):
    """Table row controller actions"""

    def set_row_height(self, row, height):
        """Sets row height and marks grid as changed"""
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        tab = self.grid.current_table
        
        self.code_array.set_row_height(row, tab, height)
        self.grid.SetRowSize(row, height)

    def insert_rows(self, row, no_rows=1):
        """Adds no_rows rows before row, appends if row > maxrows 
        
        and marks grid as changed
        
        """
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        self.code_array.insert(row, no_rows, axis=0)
        
    def delete_rows(self, row, no_rows=1):
        """Deletes no_rows rows and marks grid as changed"""
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        self.code_array.delete(row, no_rows, axis=0)


class TableColumnActionsMixin(object):
    """Table column controller actions"""

    def set_col_width(self, col, width):
        """Sets column width and marks grid as changed"""
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        tab = self.grid.current_table
        
        self.code_array.set_col_width(col, tab, width)
        self.grid.SetColSize(col, width)

    def insert_cols(self, col, no_cols=1):
        """Adds no_cols columns before col, appends if col > maxcols 
        
        and marks grid as changed
        
        """
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        self.code_array.insert(col, no_cols, axis=1)
        
    def delete_cols(self, col, no_cols=1):
        """Deletes no_cols column and marks grid as changed"""
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        self.code_array.delete(col, no_cols, axis=1)
        

class TableTabActionsMixin(object):
    """Table tab controller actions"""

    def insert_tabs(self, tab, no_tabs=1):
        """Adds no_tabs tabs before table, appends if tab > maxtabs
        
        and marks grid as changed
        
        """
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        self.code_array.insert(tab, no_tabs, axis=2)

    def delete_tabs(self, tab, no_tabs=1):
        """Deletes no_tabs tabs and marks grid as changed"""
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        self.code_array.delete(tab, no_tabs, axis=2)


class TableActions(TableRowActionsMixin, TableColumnActionsMixin, 
                   TableTabActionsMixin):
    """Table controller actions"""
    
    def __init__(self):
        
        # Action states
        
        self.pasting = False
        
        # Bindings
        
        self.main_window.Bind(wx.EVT_KEY_DOWN, self.on_key)
    
    def on_key(self, event):
        """Sets abort if pasting and if escape is pressed"""
        
        # If paste is running and Esc is pressed then we need to abort
        
        if event.GetKeyCode() == wx.WXK_ESCAPE and \
           self.pasting or self.saving:
            self.need_abort = True
        
        event.Skip()
    
    def _abort_paste(self):
        """Aborts import"""
        
        statustext = "Paste aborted."
        post_command_event(self.main_window, StatusBarMsg, 
                           text=statustext)
        
        self.pasting = False
        self.need_abort = False
    
    def _show_final_overflow_message(self, row_overflow, col_overflow):
        """Displays overflow message after import in statusbar"""
        
        if row_overflow and col_overflow:
            overflow_cause = "rows and columns"
        elif row_overflow:
            overflow_cause = "rows"
        elif col_overflow:
            overflow_cause = "columns"
        else:
            raise AssertionError, "Import cell overflow missing"
        
        statustext = "The imported data did not fit into the grid " + \
                     overflow_cause + ". It has been truncated. " + \
                     "Use a larger grid for full import."
        post_command_event(self.main_window, StatusBarMsg, text=statustext)
    
    def paste(self, tl_key, data):
        """Pastes data into grid table starting at top left cell tl_key
        
        and marks grid as changed
        
        Parameters
        ----------
        
        ul_key: Tuple
        \key of top left cell of paste area
        data: iterable of iterables where inner iterable returns string
        \tThe outer iterable represents rows
        
        """
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        self.pasting = True
        
        grid_rows, grid_cols, _ = self.grid.code_array.shape
                
        self.need_abort = False
        
        try:
            tl_row, tl_col, tl_tab = tl_key
        
        except ValueError:
            tl_row, tl_col = tl_key
            tl_tab = self.grid.current_table
        
        row_overflow = False
        col_overflow = False
        
        for src_row, col_data in enumerate(data):
            target_row = tl_row + src_row
            
            if self._is_aborted(src_row, "Pasting cells... "):
                self._abort_paste()
                return False
            
            # Check if rows fit into grid
            if target_row >= grid_rows:
                row_overflow = True
                break
            
            for src_col, cell_data in enumerate(col_data):
                target_col = tl_col + src_col
                
                if target_col >= grid_cols:
                    col_overflow = True
                    break
                
                key = target_row, target_col, tl_tab
                
                try:
                    self.grid.code_array[key] = cell_data
                except KeyError:
                    pass
        
        if row_overflow or col_overflow:
            self._show_final_overflow_message(row_overflow, col_overflow)

        self.pasting = False

    def change_grid_shape(self, shape):
        """Grid shape change event handler, marks content as changed"""
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        self.grid.code_array.shape = shape


class UnRedoActions(object):
    """Undo and redo operations"""
    
    def undo(self):
        """Calls undo in model.code_array.unredo, marks content as changed"""
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        self.code_array.unredo.undo()
        
    def redo(self):
        """Calls redo in model.code_array.unredo, marks content as changed"""
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        self.code_array.unredo.redo()


class GridActions(object):
    """Grid level grid actions"""
    
    def __init__(self):
        
        self.prev_rowcol = [] # Last mouse over cell
        
        self.main_window.Bind(EVT_COMMAND_GRID_ACTION_NEW, self.new)
        self.main_window.Bind(EVT_COMMAND_GRID_ACTION_TABLE_SWITCH, 
                              self.switch_to_table)
    
    def new(self, event):
        """Creates a new spreadsheet. Expects code_array in event."""
        
        # Grid table handles interaction to code_array
        
        self._empty_grid(event.shape)
    
        _grid_table = GridTable(self.grid, self.grid.code_array)
        self.grid.SetTable(_grid_table, True)
    
    # Zoom actions
    
    def _zoom_rows(self, zoom):
        """Zooms grid rows"""
        
        self.grid.SetDefaultRowSize(self.grid.std_row_size * zoom, 
                                    resizeExistingRows=True)
        self.grid.SetRowLabelSize(self.grid.row_label_size * zoom)
        
        for row, tab in self.code_array.row_heights:
            if tab == self.grid.current_table:
                zoomed_row_size = self.code_array.row_heights[(row, tab)] * zoom
                self.grid.SetRowSize(row, zoomed_row_size)
    
    def _zoom_cols(self, zoom):
        """Zooms grid columns"""
        
        self.grid.SetDefaultColSize(self.grid.std_col_size * zoom, 
                                    resizeExistingCols=True)
        self.grid.SetColLabelSize(self.grid.col_label_size * zoom)
    
        for col, tab in self.code_array.col_widths:
            if tab == self.grid.current_table:
                zoomed_col_size = self.code_array.col_widths[(col, tab)] * zoom
                self.grid.SetColSize(col, zoomed_col_size)
    
    def _zoom_labels(self, zoom):
        """Adjust grid label font to zoom factor"""
        
        labelfont = self.grid.GetLabelFont()
        default_fontsize = get_font_from_data(config["font"]).GetPointSize() - 2
        labelfont.SetPointSize(max(1, int(round(default_fontsize * zoom))))
        self.grid.SetLabelFont(labelfont)
    
    def zoom(self, zoom):
        """Zooms to zoom factor"""
        
        # Zoom factor for grid content
        self.grid.grid_renderer.zoom = zoom
        
        # Zoom grid labels
        self._zoom_labels(zoom)
        
        # Zoom rows and columns
        self._zoom_rows(zoom)
        self._zoom_cols(zoom)
        
        self.grid.ForceRefresh()
        
        statustext = u"Zoomed to {0:.2f}.".format(zoom)
            
        post_command_event(self.main_window, StatusBarMsg, text=statustext)
    
    def zoom_in(self):
        """Zooms in by zoom factor"""
        
        zoom = self.grid.grid_renderer.zoom
        
        target_zoom = zoom * (1 + config["zoom_factor"])
        
        if target_zoom < config["maximum_zoom"]:
            self.zoom(target_zoom)
        
    def zoom_out(self):
        """Zooms out by zoom factor"""
        
        zoom = self.grid.grid_renderer.zoom
        
        target_zoom = zoom * (1 - config["zoom_factor"])
        
        if target_zoom > config["minimum_zoom"]:
            self.zoom(target_zoom)
    
    def on_mouse_over(self, key):
        """Displays cell code of cell key in status bar"""
        
        row, col, tab = key
        
        if (row, col) != self.prev_rowcol and row >= 0 and col >= 0:
            self.prev_rowcol[:] = [row, col]
            
            hinttext = self.grid.GetTable().GetSource(row, col, tab)
            
            if hinttext is None:
                hinttext = ''
            
            post_command_event(self.main_window, StatusBarMsg, text=hinttext)
    
    def get_visible_area(self):
        """Returns visible area
       
        Format is a tuple of the top left tuple and the lower right tuple
        
        """
        
        grid = self.grid
        
        top = grid.YToRow(grid.GetViewStart()[1] * grid.ScrollLineX)
        left = grid.XToCol(grid.GetViewStart()[0] * grid.ScrollLineY)
        
        # Now start at top left for determining the bottom right visible cell
        
        bottom, right = top, left 
        
        while grid.IsVisible(bottom, left, wholeCellVisible=False):
            bottom += 1
            
        while grid.IsVisible(top, right, wholeCellVisible=False):
            right += 1
            
        # The derived lower right cell is *NOT* visible
        
        bottom -= 1
        right -= 1
        
        return (top, left), (bottom, right)
    
    def switch_to_table(self, event):
        """Switches grid to table
        
        Parameters
        ----------
        
        event.newtable: Integer
        \tTable that the grid is switched to
        
        """
        
        newtable = event.newtable
        
        no_tabs = self.grid.code_array.shape[2]
        
        if 0 <= newtable <= no_tabs:
            self.grid.current_table = newtable
            self.grid.ForceRefresh()
            
            ##self.grid.zoom_rows()
            ##self.grid.zoom_cols()
            ##self.grid.zoom_labels()
            
            ##post_entryline_text(self.grid, "")

    def get_cursor(self):
        """Returns current grid cursor cell (row, col, tab)"""
        
        return self.grid.GetGridCursorRow(), self.grid.GetGridCursorCol(), \
               self.grid.current_table

    def set_cursor(self, value):
        """Changes the grid cursor cell."""
        
        if len(value) == 3:
            row, col, tab = value
            
            if tab != self.cursor[2]:
                post_command_event(self.main_window, GridActionTableSwitchMsg, 
                                   newtable=tab)
        else:
            row, col = value
        
        if not (row is None and col is None):
            self.grid.MakeCellVisible(row, col)
            self.grid.SetGridCursor(row, col)
        
    cursor = property(get_cursor, set_cursor)
    

class SelectionActions(object):
    """Actions that affect the grid selection"""
    
    def get_selection(self):
        """Returns selected cells in grid as Selection object"""
        
        # GetSelectedCells: individual cells selected by ctrl-clicking
        # GetSelectedRows: rows selected by clicking on the labels
        # GetSelectedCols: cols selected by clicking on the labels
        # GetSelectionBlockTopLeft
        # GetSelectionBlockBottomRight: For blocks of cells selected by dragging
        # across the grid cells.
        
        block_top_left = self.grid.GetSelectionBlockTopLeft()
        block_bottom_right = self.grid.GetSelectionBlockBottomRight()
        rows = self.grid.GetSelectedRows()
        cols = self.grid.GetSelectedCols()
        cells = self.grid.GetSelectedCells()
        
        return Selection(block_top_left, block_bottom_right, rows, cols, cells)
    
    def select_cell(self, row, col, add_to_selected=False):
        self.grid.SelectBlock(row, col, row, col, addToSelected=add_to_selected)
    
    def select_slice(self, row_slc, col_slc, add_to_selected=False):
        """Selects a slice of cells
        
        Parameters
        ----------
         * row_slc: Integer or Slice
        \tRows to be selected
         * col_slc: Integer or Slice
        \tColumns to be selected
         * add_to_selected: Bool, defaults to False
        \tOld selections are cleared if False
        
        """
        
        if not add_to_selected:
            self.grid.ClearSelection()
        
        if row_slc == row_slc == slice(None, None, None):
            # The whole grid is selected
            self.grid.SelectAll()
            
        elif row_slc.stop is None and col_slc.stop is None:
            # A block is selcted:
            self.grid.SelectBlock(row_slc.start, col_slc.start, 
                                  row_slc.stop-1, col_slc.stop-1)
        else:
            for row in xrange(row_slc.start, row_slc.stop, row_slc.step):
                for col in xrange(col_slc.start, col_slc.stop, col_slc.step):
                    self.select_cell(row, col, add_to_selected=True)

    def delete_selection(self):
        """Deletes selected cells, marks content as changed"""
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        selection = self.get_selection()
        
        del_keys = [key for key in self.grid.code_array if key[:2] in selection]
        
        for key in del_keys:
            self.grid.actions.delete_cell(key)

class FindActions(object):
    """Actions for finding inside the grid"""
    
    def find(self, gridpos, find_string, flags):
        """Return next position of event_find_string in MainGrid
        
        Parameters:
        -----------
        gridpos: 3-tuple of Integer
        \tPosition at which the search starts
        find_string: String
        \tString to find in grid
        flags: Int
        \twx.wxEVT_COMMAND_FIND flags
        
        """
        
        findfunc = self.grid.code_array.findnextmatch
        
        if "DOWN" in flags:
            if gridpos[0] < self.grid.code_array.shape[0]:
                gridpos[0] += 1
            elif gridpos[1] < self.grid.code_array.shape[1]:
                gridpos[1] += 1
            elif gridpos[2] < self.grid.code_array.shape[2]:
                gridpos[2] += 1
            else:
                gridpos = (0, 0, 0)
        elif "UP" in flags:
            if gridpos[0] > 0:
                gridpos[0] -= 1
            elif gridpos[1] > 0:
                gridpos[1] -= 1
            elif gridpos[2] > 0:
                gridpos[2] -= 1
            else:
                gridpos = [dim - 1 for dim in self.grid.code_array.shape]
        
        return findfunc(tuple(gridpos), find_string, flags)
        
    def replace(self, findpos, find_string, replace_string):
        """Replaces occurrences of find_string with replace_string at findpos
        
        and marks content as changed
        
        Parameters
        ----------
        
        findpos: 3-Tuple of Integer
        \tPosition in grid that shall be replaced
        find_string: String
        \tString to be overwritten in the cell
        replace_string: String
        \tString to be used for replacement

        """
        
        # Mark content as changed
        post_command_event(self.main_window, ContentChangedMsg, changed=True)
        
        old_code = self.grid.code_array(findpos)
        new_code = old_code.replace(find_string, replace_string)
    
        self.grid.code_array[findpos] = new_code
        self.grid.actions.cursor = findpos
        
        statustext = "Replaced '" + old_code + "' with '" + new_code + \
                     "' in cell " + unicode(list(findpos)) + "."
                     
        post_command_event(self.main_window, StatusBarMsg, text=statustext)

class AllGridActions(FileActions, TableActions, UnRedoActions, 
                     GridActions, SelectionActions, FindActions, CellActions):
    """All grid actions as a bundle"""
    
    def __init__(self, grid, code_array):
        self.main_window = grid.main_window
        self.grid = grid
        self.code_array = code_array
        
        FileActions.__init__(self)
        TableActions.__init__(self)
        UnRedoActions.__init__(self)
        GridActions.__init__(self)
        SelectionActions.__init__(self)
        FindActions.__init__(self)
        CellActions.__init__(self)

    def _is_aborted(self, cycle, statustext, total_elements=None, freq=1000):
        """Displays progress and returns True if abort
        
        Parameters
        ----------
        
        statustext: String
        \tLeft text in statusbar to be displayed
        cycle: Integer
        \tThe current operation cycle
        total_elements: Integer:
        \tThe number of elements that have to be processed
        freq: Integer, defaults to 1000
        \tNo. operations between two abort possibilities
        
        """
        
        # Show progress in statusbar each 1000 cells
        if cycle % 1000 == 0:
            # See if we know how much data comes along
            if total_elements is None:
                total_elements_str = ""
            else:
                total_elements_str = " of " + str(total_elements)
                
            statustext = statustext + str(cycle) + total_elements_str + \
                        " elements processed. Press <Esc> to abort."
            post_command_event(self.main_window, StatusBarMsg, 
                       text=statustext)
            
            # Now wait for the statusbar update to be written on screen
            wx.Yield()
            
            # Abort if we have to
            if self.need_abort:
                # We have to abort`
                return True
                
        # Continue
        return False

    def _replace_bbox_none(self, bbox):
        """Returns bbox, in which None is replaced by grid boundaries"""
        
        (bb_top, bb_left), (bb_bottom, bb_right) = bbox
        
        if bb_top is None:
            bb_top = 0
        
        if bb_left is None:
            bb_left = 0    
        
        if bb_bottom is None:
            bb_bottom = self.code_array.shape[0] - 1
        
        if bb_right is None:
            bb_right = self.code_array.shape[1] - 1  
        
        return (bb_top, bb_left), (bb_bottom, bb_right)
