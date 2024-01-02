from zim.plugins import PluginClass
from zim.actions import action
from zim.gui.mainwindow import MainWindowExtension
from zim.gui.pageview import PageViewExtension
from gi.repository import Gdk
from gi.repository import Gtk
from enum import Enum

class ViPlugin(PluginClass):

	plugin_info = {
		"name": _( "Vi Mode" ),
		"description": _( "Vi mode... ish" ),
		"author": "Tom <tom@tomg.xyz> to start with",
	}

	_ex_input = None

class ViMainWindowExtension( MainWindowExtension ):

	nbinds = [
		( ["i"],
			lambda self : setattr( self, "insert_mode", True ) ),
		( ["I"], lambda self : (
			self.tv.do_move_cursor(
				Gtk.MovementStep.PARAGRAPH_ENDS, -1, False ),
			setattr( self, "insert_mode", True ) ) ),
		( ["a"], lambda self : (
			self.tv.do_move_cursor(
				Gtk.MovementStep.LOGICAL_POSITIONS, 1, False ),
			setattr( self, "insert_mode", True ) ) ),
		( ["A"], lambda self : (
			self.tv.do_move_cursor(
				Gtk.MovementStep.PARAGRAPH_ENDS, 1, False ),
			setattr( self, "insert_mode", True ) ) ),
		( ["o"], lambda self : (
			self.tv.do_move_cursor(
				Gtk.MovementStep.PARAGRAPH_ENDS, 1, False ),
			self.tv.do_insert_at_cursor( self.tv, "\n" ),
			setattr( self, "insert_mode", True ) ) ),
		( ["O"], lambda self : (
			self.tv.do_move_cursor(
				Gtk.MovementStep.PARAGRAPH_ENDS, -1, False ),
			self.tv.do_insert_at_cursor( self.tv, "\n" ),
			self.tv.do_move_cursor(
				Gtk.MovementStep.DISPLAY_LINES, -1, False ),
			setattr( self, "insert_mode", True ) ) ),
		( [ "h" ], lambda self : self.tv.do_move_cursor(
			Gtk.MovementStep.LOGICAL_POSITIONS, -1, False ) ),
		( [ "j" ], lambda self : self.tv.do_move_cursor(
			Gtk.MovementStep.DISPLAY_LINES, 1, False ) ),
		( [ "k" ], lambda self : self.tv.do_move_cursor(
			Gtk.MovementStep.DISPLAY_LINES, -1, False ) ),
		( [ "l" ], lambda self : self.tv.do_move_cursor(
			Gtk.MovementStep.LOGICAL_POSITIONS, 1, False ) ),
		( [ "w" ], lambda self : self.tv.do_move_cursor(
			Gtk.MovementStep.WORDS, 1, False ) ),
		( [ "b" ], lambda self : self.tv.do_move_cursor(
			Gtk.MovementStep.WORDS, -1, False ) ),
		( [ "colon" ], lambda self : (
			setattr( self.plugin._ex_input, "_return_widget", self.tv ),
			self.plugin._ex_input.entry.set_text( "" ),
			self.plugin._ex_input.entry.grab_focus() ) ),
	]

	ibinds = [
		( [ "Escape" ],
			lambda self : setattr( self, "insert_mode", False ) ),
		( [ "j", "k" ],
			lambda self : setattr( self, "insert_mode", False ) ),
	]

	def __init__( self, plugin, window ):

		MainWindowExtension.__init__( self, plugin, window )
		self.plugin = plugin
		self.window = window
		self.tv = self.window.pageview.textview
		self.connectto( self.tv, "key-press-event" )

		self.insert_mode = False
		self.keybuffer = []

	def on_key_press_event( self, widget, event ):

		# Gdk / pygobject doesn't notice if we just append event to the
		# keybuffer and will free the underlying C object I guess and
		# that's how you make a python program segfault.
		# copy.[deep]copy() don't work for reasons.
		# So here I am, manually copying all the listed elements of the
		# GdkEventKey structure.  Whatever.  Seems to work.
		# (Gtk4, and the corresponding python bindings, have ref/unref
		# functions for events, that presmably would fix this.  Just
		# saying.)  Also, I'm completely ignoring key release events,
		# but again: Whatever.  Seems to work.

		copy = Gdk.EventKey()
		copy.group = event.group
		copy.hardware_keycode = event.hardware_keycode
		copy.is_modifier = event.is_modifier
		copy.keyval = event.keyval
		copy.length = event.length
		copy.send_event = event.send_event
		copy.state = event.state
		copy.string = event.string
		copy.time = event.time
		copy.type = event.type
		copy.window = event.window

		# I don't think ::is_modifier is actually set correctly because
		# modifiers keep messing up my keybindings, but in theory this
		# should be here, right?
		if not event.is_modifier:
			self.keybuffer.append( copy )

			while self.match( False ):
				pass

		return True

	Match = Enum( "Match", [ "NONE", "PARTIAL", "FULL" ] )

	def match( self, timeout ):

		length = 0
		start = 0
		m = self.Match.NONE
		b = None

		for bind in \
				self.ibinds if self.insert_mode else self.nbinds:

			bind_match, bind_start, bind_len = \
				self.match_bind( bind, self.keybuffer )

			if ( self.Match.FULL == bind_match or
					( not timeout and
						bind_match == self.Match.PARTIAL ) ) and \
					( b == None or bind_start < start or
					( bind_start == start and bind_len > length ) ):

				length = bind_len
				start = bind_start
				b = bind
				m = bind_match

		if self.insert_mode:
			for event in self.keybuffer if m == self.Match.NONE else \
					self.keybuffer[:start]:
				self.tv.do_key_press_event( event )

		if m == self.Match.FULL:
			self.keybuffer = self.keybuffer[start + length:]
		elif m == self.Match.PARTIAL:
			self.keybuffer = self.keybuffer[start:]
		else:
			self.keybuffer = []

		if m == self.Match.FULL:
			b[1]( self )
			return True
		else:
			return False

	def match_bind( self, bind, keybuffer ):

		for start in range( 0, len( keybuffer ) ):

			l = 0;

			while l < len( bind[0] ) and \
					start + l < len( keybuffer ) and \
					Gdk.keyval_name( keybuffer[start + l].keyval ) == \
						bind[0][l]:
				l += 1

			if l == len( bind[0] ):
				return self.Match.FULL, start, l
			elif 0 < l and start + l == len( keybuffer ):
				return self.Match.PARTIAL, start, l

		return self.Match.NONE, 0, 0

class ViPageViewExtension( PageViewExtension ):

	excmds = [
		( [ "w", "write" ], lambda self, argv :
			self.pageview.save_page() ),
		( [ "q", "quit", "qa", "x", "xa", "xit", "exit" ],
			lambda self, argv :
				Gtk.main_quit() if Gtk.main_level() > 0 else None ),
	]

	def __init__( self, plugin, window ):

		PageViewExtension.__init__( self, plugin, window )
		plugin._ex_input = self.ex

	@action( _( "_Ex Input" ), accelerator="F6", icon="system-run",
		menuhints="tools:entry" )
	def ex( self ):

		text = [ i for i in self.ex.entry.get_text().split( " " )
			if i != "" ]
		for cmd in self.excmds:
			if text[0] in cmd[0]:
				cmd[1]( self, text )

		self.ex.entry.set_text( "" )
		if None != self.ex._return_widget:
			self.ex._return_widget.grab_focus()
