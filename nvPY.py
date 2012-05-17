#!/usr/bin/env python

# nvPY: cross-platform note-taking app with simplenote syncing
# copyright 2012 by Charl P. Botha <cpbotha@vxlabs.com>
# new BSD license

# inspired by notational velocity and nvALT, neither of which I've used,
# and ResophNotes, which I have used.

# full width horizontal bar at top to search
# left column with current results: name, mod date, summary, tags
# right column with text of currently selected note

# * typing in the search bar:
# - press enter: focus jumps to note if ANYTHING is selected. if nothing is
# selected, enter creates a new note with the current string as its name.
# - esc clears the search entry, esc again jumps to list
# - up and down changes currently selected list
# * in note conten area
# - esc goes back to notes list.

# http://www.scribd.com/doc/91277952/Simple-Note-API-v2-1-3
# this also has a sync algorithm!

# 1. finish implementing search
# 1.5. think about other storage formats. What if we want to store more? (cursor position and so on. sqlite?)
# 2. note editing
#   a) saving to disc: remember lmodified or whatever.
#   b) syncing with simplenote

# to check if we're online

import ConfigParser
from notes_db import NotesDB
import os
import sys
import time
from utils import KeyValueObject, SubjectMixin
import view

class Config:
    def __init__(self, cfg_fname, defaults):
        # allow_no_value=True means we'll just get None for undefined values
        cp = ConfigParser.SafeConfigParser(defaults, allow_no_value=True)
        cp.read(cfg_fname)
        self.sn_username = cp.get('default', 'sn_username')
        self.sn_password = cp.get('default', 'sn_password')
        self.db_path = cp.get('default', 'db_path')
        
class NotesListModel(SubjectMixin):
    def __init__(self):
        # call mixin ctor
        SubjectMixin.__init__(self)
        
        self.list = []
        
    def set_list(self, alist):
        self.list = alist
        self.notify_observers('set:list', None)
        
    def get_idx(self, key):
        found = [i for i,e in enumerate(self.list) if e.key == key]
        if found:
            return found[0]
        
        else:
            return -1
    
class Controller:
    """Main application class.
    """
    
    def __init__(self):
        # setup appdir
        if hasattr(sys, 'frozen') and sys.frozen:
            self.appdir, _ = os.path.split(sys.executable)
            
        else:
            dirname = os.path.dirname(__file__)
            if dirname and dirname != os.curdir:
                self.appdir = dirname
            else:
                self.appdir = os.getcwd()
        
        # should probably also look in $HOME
        cfg_defaults = {'appdir' : self.appdir}
        self.config = Config(os.path.join(self.appdir, 'nvPY.cfg'), cfg_defaults)
        
        # read our database of notes into memory
        # and sync with simplenote.
        self.notes_db = NotesDB(self.config.db_path, self.config.sn_username, self.config.sn_password)
        #self.notes_db.sync_full()

        self.notes_list_model = NotesListModel()
        
        # create the interface
        self.view = view.View(self, self.notes_list_model)
        # we want to be notified when the user does stuff
        self.view.add_observer('select:note', self.observer_view_select_note)
        self.view.add_observer('change:entry', self.observer_view_change_entry)
        self.view.add_observer('change:text', self.observer_view_change_text)
        self.view.add_observer('create:note', self.observer_view_create_note)
        self.view.add_observer('keep:house', self.observer_view_keep_house)
        
        # nn is a list of (key, title, modifydate) objects
        nn = self.notes_db.get_note_names()
        # this will trigger the list_change event
        self.notes_list_model.set_list(nn)

        # we'll use this to keep track of the currently selected note
        self.selected_note = KeyValueObject(idx=-1, key=-1)
        self.view.select_note(0)
        
    def get_version(self):
        return "0.1"
    
    def quit(self):
        self.view.close()
        
    def main_loop(self):
        # FIXME: before you start the view main loop, give it some
        # time-based handlers to run.
        self.view.main_loop()
        
    def observer_view_keep_house(self, view, evt_type, evt):
        nsaved = self.notes_db.save()
        if nsaved > 0:
            self.view.set_status_text('%d notes saved to disc on %s.' % (nsaved, time.asctime()))
        
    def observer_view_select_note(self, view, evt_type, evt):
        self.select_note(evt.sel)
            
    def observer_view_change_entry(self, view, evt_type, evt):
        # for each new evt.value coming in, get a new list from the notes_db
        # and set it in the notes_list_model
        nn = self.notes_db.get_note_names(evt.value)
        self.notes_list_model.set_list(nn)
        # we select note in the view, this will eventually come back to us
        # in observer_view_select_note
        self.view.select_note(0)

    def observer_view_change_text(self, view, evt_type, evt):
        # get new text and update our database
        self.notes_db.set_note_content(self.selected_note.key,
                                       self.view.get_text())
        
    def observer_view_create_note(self, view, evt_type, evt):
        # create the note
        new_key = self.notes_db.create_note(evt.title)
        # clear the search entry, this should trigger a new list being returned
        self.view.set_search_entry_text('')
        # we should focus on our thingy
        idx = self.notes_list_model.get_idx(new_key)
        self.view.select_note(idx)
    
    def select_note(self, idx):
        if idx >= 0:
            key = self.notes_list_model.list[idx].key
            c = self.notes_db.get_note_content(key)

        else:
            key = -1
            c = ''
            idx = -1
        
        self.selected_note.idx = idx
        self.selected_note.key = key

        # when we do this, we don't want the change:text event thanks
        self.view.mute('change:text')            
        self.view.set_text(c)
        self.view.unmute('change:text')

def main():
    controller = Controller()
    controller.main_loop()
    

if __name__ == '__main__':
    main()
