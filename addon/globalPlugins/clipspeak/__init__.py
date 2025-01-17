# -*- coding: utf-8 -*-
# Clipspeak
# An addon to monitor and speak messages relating to clipboard operations
# By: Damien Lindley Created: 19th April 2017
# Modified by Rui Fontes, Ângelo Miguel and Abel Júnior in 26/03/2022
# This file is covered by the GNU General Public License.
# See the file COPYING for more details.

import globalPluginHandler
import globalVars
import ui
import api
import inputCore
import scriptHandler
from scriptHandler import script
from logHandler import log
import controlTypes
if hasattr(controlTypes, "Role"):
	for r in controlTypes.Role: setattr(controlTypes, r.__str__().replace("Role.", "ROLE_"), r)
else:
	setattr(controlTypes, "Role", type('Enum', (), dict([(x.split("ROLE_")[1], getattr(controlTypes, x)) for x in dir(controlTypes) if x.startswith("ROLE_")])))

if hasattr(controlTypes, "State"):
	for r in controlTypes.State: setattr(controlTypes, r.__str__().replace("State.", "STATE_"), r)
else:
	setattr(controlTypes, "State", type('Enum', (), dict([(x.split("STATE_")[1], getattr(controlTypes, x)) for x in dir(controlTypes) if x.startswith("STATE_")])))

from . import clipboard_monitor
# For update process
from . update import *
import addonHandler
addonHandler.initTranslation()

# Constants:

# Clipboard content: What are we working with?
cc_none=0
cc_text=1
cc_read_only_text=2
cc_file=3
cc_list=4
cc_other=5

# Clipboard mode: What are we doing?
cm_none=0
cm_cut=1
cm_copy=2
cm_paste=3

# Not strictly clipboard, but...
cm_undo=4
cm_redo=5

# Defining variables on NVDA.INI
def initConfiguration():
	global announcement
	try:
		value = config.conf[ourAddon.manifest["name"]]["announce"]
	except KeyError:
		config.conf[ourAddon.manifest["name"]] = {}
		config.conf[ourAddon.manifest["name"]]["announce"] = "boolean(default=True)"
		announcement = getConfig("announce")
	else:
		value = config.conf[ourAddon.manifest["name"]]["announce"]
		announcement = True if value == "True" else False

# Reading value of variable in NVDA.ini
def getConfig(key):
	value = config.conf[ourAddon.manifest["name"]][key]
	return bool(value)

# Saving value in NVDA.ini
def setConfig(key, value):
	try:
		config.conf.profiles[0][ourAddon.manifest["name"]][key] = value
	except:
		config.conf[ourAddon.manifest["name"]][key] = value

initConfiguration()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):	
	# Creating the constructor of the newly created GlobalPlugin class.
	def __init__(self):
		# Call of the constructor of the parent class.
		super(globalPluginHandler.GlobalPlugin, self).__init__()

		# Adding a NVDA configurations section
		gui.NVDASettingsDialog.categoryClasses.append(ClipSpeakSettingsPanel)

		# To allow waiting end of network tasks
		core.postNvdaStartup.register(self.networkTasks)

	def networkTasks(self):
		# Calling the update process...
		_MainWindows = Initialize()
		_MainWindows.start()

	def terminate(self):
		super(GlobalPlugin, self).terminate()
		core.postNvdaStartup.unregister(self.networkTasks)
		gui.settingsDialogs.NVDASettingsDialog.categoryClasses.remove(ClipSpeakSettingsPanel)

	# Script functions:

	@script( 
	# For translators: Message to be announced during Keyboard Help 
	description = _("Cut selected item to clipboard, if appropriate."), 
	# For translators: Name of the section in "Input gestures" dialog. 
	category = _("Clipboard"), 
	gesture = "kb:Control+X")
	def script_cut(self, gesture):
		log.debug("Script activated: Cut.")
		log.debug("Processing input gesture.")
		if self.process_input(gesture):
			return
		log.debug("Speaking message.")
		self.speak_appropriate_message(cm_cut)

	@script( 
	# For translators: Message to be announced during Keyboard Help 
	description = _("Copy selected item to clipboard, if appropriate."), 
	# For translators: Name of the section in "Input gestures" dialog. 
	category = _("Clipboard"), 
	gesture = "kb:Control+C")
	def script_copy(self, gesture):
		log.debug("Script activated: Copy.")
		log.debug("Processing input gesture.")
		if self.process_input(gesture):
			return
		log.debug("Speaking message.")
		self.speak_appropriate_message(cm_copy)

	@script( 
	# For translators: Message to be announced during Keyboard Help 
	description = _("Paste item from clipboard, if appropriate."), 
	# For translators: Name of the section in "Input gestures" dialog. 
	category = _("Clipboard"), 
	gesture = "kb:Control+V")
	def script_paste(self, gesture):
		log.debug("Script activated: Paste.")
		log.debug("Processing input gesture.")
		if self.process_input(gesture):
			return
		log.debug("Speaking message.")
		self.speak_appropriate_message(cm_paste)

	@script( 
	# For translators: Message to be announced during Keyboard Help 
	description = _("Undo operation."),
	# For translators: Name of the section in "Input gestures" dialog. 
	category = _("Clipboard"), 
	gesture = "kb:Control+Z")
	def script_undo(self, gesture):
		log.debug("Script activated: Undo.")
		log.debug("Processing input gesture.")
		if self.process_input(gesture):
			return
		log.debug("Speaking message.")
		self.speak_appropriate_message(cm_undo)

	@script( 
	# For translators: Message to be announced during Keyboard Help 
	description = _("Redo operation."),
	# For translators: Name of the section in "Input gestures" dialog.
	category = _("Clipboard"), 
	gesture = "kb:Control+Y")
	def script_redo(self, gesture):
		log.debug("Script activated: Redo.")
		log.debug("Processing input gesture.")
		if self.process_input(gesture):
			return
		log.debug("Speaking message.")
		self.speak_appropriate_message(cm_redo)

	# Internal functions: Examines our environment so we can speak the appropriate message.
	def process_input(self, gesture):
		log.debug("Evaluating possible gestures.")
		scripts=[]
		maps=[inputCore.manager.userGestureMap, inputCore.manager.localeGestureMap]

		log.debug("Found gesture mapping: \r"%maps)
		log.debug("Enumerating scripts for these maps.")
		for map in maps:
			log.debug("Enumerating gestures for map %r"%map)
			for identifier in gesture.identifiers:
				log.debug("Enumerating scripts for gesture %r"%identifier)
				scripts.extend(map.getScriptsForGesture(identifier))

		log.debug("Found scripts: %r"%scripts)

		focus=api.getFocusObject()
		log.debug("Examining focus: %r"%focus)
		tree=focus.treeInterceptor
		log.debug("Examining tree interceptor: %r"%tree)

		log.debug("Checking tree interceptor state.")
		if tree and tree.isReady:

			log.debug("Tree interceptor in use. Retrieving scripts for the interceptor.")
			func=scriptHandler._getObjScript(tree, gesture, scripts)
			log.debug("Examining object: %r"%func)

			log.debug("Examining function attributes.")
			if func and (not tree.passThrough or getattr(func,"ignoreTreeInterceptorPassThrough",False)):

				log.debug("This gesture is already handled elsewhere. Executing associated function.")
				func(tree)
				return True

		log.debug("Nothing associated here. Pass straight to the system.")
		gesture.send()
		return False

	def speak_appropriate_message(self, cm_flag):
		cc_flag = self.examine_focus()
		# Todo: If we can validate whether or not a control can work with the clipboard, we can return an invalid message here.
		log.debug("Finding appropriate message for clipboard content type: %r"%cc_flag)
		if cc_flag==cc_none:
			return
		elif cc_flag == cc_text:
			# Pick a word suitable to the content.
			text = api.getClipData()
			if len(text) < 500:
				text = text
			else:
				text = _("%s characters")%len(text)
			word1 = _(text)
		elif cc_flag==cc_file:
			# Translators: A single word representing a file.
			word=_("file")

		elif cc_flag==cc_list:
			# Translators: A single word representing an item in a list.
			word=_("item")

		# Decide what will be announced...
		if announcement == True:
			word = word1 = ""

		# Validate and speak.
		log.debug("Validating clipboard mode: %r"%cm_flag)

		if cm_flag==cm_undo and self.can_undo(cc_flag):
			# Translators: Message to speak when undoing.
			ui.message(_("Undo"))

		if cm_flag==cm_redo and self.can_redo(cc_flag):
			# Translators: A message spoken when redoing a previously undone operation.
			ui.message(_("Redo"))

		if cm_flag==cm_cut and self.can_cut(cc_flag):
			if cc_flag == cc_text:
				# Translators: A message to speak when cutting text to the clipboard.
				ui.message(_("Cut: %s")%word1)
			else:
				# Translators: A message to speak when cutting an item to the clipboard.
				ui.message(_("Cut %s")%word)

		if cm_flag==cm_copy and self.can_copy(cc_flag):
			if cc_flag == cc_text:
				# Translators: A message spoken when copying text to the clipboard.
				ui.message(_("Copy: %s")%word1)
			else:
				# Translators: A message spoken when copying to the clipboard.
				ui.message(_("Copy %s")%word)

		if cm_flag==cm_paste and self.can_paste(cc_flag):
			if cc_flag == cc_text:
				# Translators: A message spoken when pasting text from the clipboard.
				ui.message(_("Pasted: %s")%word1)
			else:
				# Translators: A message spoken when pasting from the clipboard.
				ui.message(_("Pasted %s")%word)

	def examine_focus(self):
		focus=api.getFocusObject()
		if not focus:
			return cc_none
		log.debug("Examining focus object: %r"%focus)
		# Retrieve the control's states and roles.
		states=focus.states

		# Check for an explorer/file browser window.
		# Todo: Is this an accurate method?
		if (focus.windowClassName == "DirectUIHWND") and controlTypes.STATE_SELECTED in states:
			return cc_file

		# Check for a list item.
		elif (focus.role == controlTypes.ROLE_LISTITEM or controlTypes.ROLE_TABLEROW) and controlTypes.STATE_SELECTED in states:
			return cc_list

		# Check if we're looking at text.
		elif (controlTypes.STATE_EDITABLE or controlTypes.STATE_MULTILINE) in states:
			if controlTypes.STATE_READONLY in states:
				return cc_read_only_text
			else:
				# Otherwise, we're just an ordinary text field.
				log.debug("Field seems to be editable.")
				return cc_text

		# For some reason, not all controls have an editable state, even when they clearly are.
		elif focus.role==controlTypes.ROLE_EDITABLETEXT:
			return cc_text
		elif controlTypes.STATE_READONLY in states:
			return cc_read_only_text
		elif focus.windowClassName == "RichEditD2DPT":
			return cc_text
		# Todo: Other control types we need to check?
		else:
			log.debug("Control type would not suggest clipboard operations.")
			return cc_none

	# Validation functions: In case we need to extend the script to allow more control/window types etc.
	# Todo: Can we check a control to see if it enables these operations? For instance whether a list enables copy or a text field allows select all?
	def can_undo(self, cc_flag):
		if cc_flag==cc_read_only_text:
			return False
		return True

	def can_redo(self, cc_flag):
		if cc_flag==cc_read_only_text:
			return False
		return True

	def can_cut(self, cc_flag):
		if cc_flag==cc_read_only_text:
			return False
		# Todo: Validate the control and make sure there is something that could potentially be cut.
		return True

	def can_copy(self, cc_flag):
		# Todo: Validate the control and make sure there is something that could potentially be copied.
		return True

	def can_paste(self, cc_flag):
		if cc_flag==cc_read_only_text:
			return False

		log.debug("Checking clipboard.")
		if not self.__clipboard.valid_data():
			return False
		return True

	# Define an object of type clipboard_monitor that will keep track of the clipboard for us.
	__clipboard = clipboard_monitor.clipboard_monitor()


if globalVars.appArgs.secure:
	# Override the global plugin to disable it.
	GlobalPlugin = globalPluginHandler.GlobalPlugin


class ClipSpeakSettingsPanel(gui.SettingsPanel):
	# Translators: Title of the ClipSpeak settings dialog in the NVDA settings.
	title = _("ClipSpeak")

	def makeSettings(self, settingsSizer):
		sHelper = gui.guiHelper.BoxSizerHelper(self, sizer = settingsSizer)

		# Translators: Checkbox name in the configuration dialog
		self.announceWnd = sHelper.addItem(wx.CheckBox(self, label=_("Announce only copy/cut/paste")))
		self.announceWnd.Bind(wx.EVT_CHECKBOX, self.onChk2)
		global announcement
		self.announceWnd.Value = announcement

		# Translators: Checkbox name in the configuration dialog
		self.shouldUpdateChk = sHelper.addItem(wx.CheckBox(self, label=_("Check for updates at startup")))
		self.shouldUpdateChk	.Bind(wx.EVT_CHECKBOX, self.onChk)
		self.shouldUpdateChk	.Value = shouldUpdate

	def onChk(self, event):
		shouldUpdate = self.shouldUpdateChk.Value

	def onChk2(self, event):
		global announcement
		announcement = self.announceWnd.Value

	def onSave (self):
		setConfig("isUpgrade", self.shouldUpdateChk.Value)
		setConfig("announce", self.announceWnd.Value)

