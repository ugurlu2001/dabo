""" dPemMixin.py: Provide common PEM functionality """
import sys, types
import dabo, dabo.common
from dabo.dLocalize import _
import dabo.ui.dPemMixinBase
import dabo.dEvents as dEvents


class dPemMixin(dabo.ui.dPemMixinBase.dPemMixinBase):
	""" Provide Property/Event/Method interfaces for dForms and dControls.

	Subclasses can extend the property sheet by defining their own get/set
	functions along with their own property() statements.
	"""
	def __getattr__(self, att):
		""" Try to resolve att to a child object reference.

		This allows accessing children with the style:
			self.mainPanel.txtName.Value = "test"
		"""
		
		children = self.winfo_children()

		ret = None
		for child in children:
			if child.winfo_name() == att:
				ret = child
				exit
				
		if not ret:
			raise AttributeError, "%s object has no attribute %s" % (
				self._name, att)
		else:
			return ret

	
	def _beforeInit(self):
		self._name = '?'
		self.initStyleProperties()
		
		# Call the subclass hook:
		self.beforeInit()

	
	def _afterInit(self):
		self.debug = False
		
		self.initProperties()
		self.initChildObjects()
		self.afterInit()
		
		self._mouseLeftDown, self._mouseRightDown = False, False

		self._initEvents()
		self.initEvents()

		self.raiseEvent(dEvents.Create)

					
	def _initEvents(self):
		# Bind tk events to handlers that re-raise the Dabo events:
		
		self.bind("<Destroy>", self._onTkDestroy)
		self.bind("<FocusIn>", self._onTkGotFocus)
		self.bind("<FocusOut>", self._onTkLostFocus)

		# Activate and Deactivate don't mean what we expect in Tk...
# 		self.bind("<Activate>", self._onTkActivate)
# 		self.bind("<Deactivate>", self._onTkDeactivate)

		self.bind("<KeyPress>", self._onTkKeyDown)
		self.bind("<KeyRelease>", self._onTkKeyUp)
		
		self.bind("<Enter>", self._onTkMouseEnter)
		self.bind("<Leave>", self._onTkMouseLeave)
		self.bind("<Button-1>", self._onTkMouseLeftDown)
		self.bind("<ButtonRelease-1>", self._onTkMouseLeftUp)
		self.bind("<Button-3>", self._onTkMouseRightDown)
		self.bind("<ButtonRelease-3>", self._onTkMouseRightUp)
				
		
			
	def _onTkDestroy(self, event):
		self.raiseEvent(dEvents.Destroy, event)
		
	def _onTkGotFocus(self, event):
		self.raiseEvent(dEvents.GotFocus, event)
		
	def _onTkLostFocus(self, event):
		self.raiseEvent(dEvents.LostFocus, event)

	def _onTkActivate(self, event):
		self.raiseEvent(dEvents.Activate, event)

	def _onTkDeactivate(self, event):
		self.raiseEvent(dEvents.Deactivate, event)

	def _onTkKeyDown(self, event):
		self.raiseEvent(dEvents.KeyDown, event)

	def _onTkKeyUp(self, event):
		self.raiseEvent(dEvents.KeyUp, event)

	def _onTkMouseEnter(self, event):
		self.raiseEvent(dEvents.MouseEnter, event)

	def _onTkMouseLeave(self, event):
		self.raiseEvent(dEvents.MouseLeave, event)
		self._mouseLeftDown, self._mouseRightDown = False, False

	def _onTkMouseLeftDown(self, event):
		self.raiseEvent(dEvents.MouseLeftDown, event)
		self._mouseLeftDown = True

	def _onTkMouseLeftUp(self, event):
		self.raiseEvent(dEvents.MouseLeftUp, event)
		if self._mouseLeftDown:
			# mouse went down and up in this control: send a click:
			self.raiseEvent(dEvents.MouseLeftClick, event)
			self._mouseLeftDown = False

	def _onTkMouseRightDown(self, event):
		self.raiseEvent(dEvents.MouseRightDown, event)
		self._mouseRightDown = True

	def _onTkMouseRightUp(self, event):
		self.raiseEvent(dEvents.MouseRightUp, event)
		if self._mouseRightDown:
			# mouse went down and up in this control: send a click:
			self.raiseEvent(dEvents.MouseRightClick, event)
			self._mouseLeftDown = False

			
	def raiseEvent(self, eventClass, nativeEvent=None, *args, **kwargs):
		# Call the Dabo-native raiseEvent(), passing along the Tkinter after_idle
		# function, so that the Dabo events can be processed at next idle.
		dPemMixin.doDefault(eventClass, nativeEvent, callAfterFunc=self.after_idle, 
			*args, **kwargs)
	
		
	def getPropertyInfo(self, name):
		d = dPemMixin.doDefault(name)   # the property helper does most of the work
		
		# Hide some wx-specific props in the designer:
		d['showInDesigner'] = not name in ('Size', 'Position', 'WindowHandle', 'TypeID')

		# Some wx-specific props need to be initialized early. Let the designer know:
		d['preInitProperty'] = name in ('Alignment', 'BorderStyle', 'PasswordEntry', 
				'Orientation', 'ShowLabels', 'TabPosition')

		return d
		
	
	def addObject(self, classRef, name, *args, **kwargs):
		""" Instantiate object as a child of self.
		
		The class reference must be a Dabo object (must inherit dPemMixin).
		
		The name parameter will be used on the resulting instance, and additional 
		arguments received will be passed on to the constructor of the object.
		"""
		object = classRef(self, name=name, *args, **kwargs)
		return object

			
	def reCreate(self, child=None):
		""" Recreate self.
		"""
		if child:
			propValDict = self.getPropValDict(child)
			style = child.GetWindowStyle()
			classRef = child.__class__
			name = child.Name
			child.Destroy()
			newObj = self.addObject(classRef, name, style=style)
			self.applyPropValDict(newObj, propValDict)
			return newObj
		else:
			return self.Parent.reCreate(self)
	
	
	def clone(self, obj, name=None):
		""" Create another object just like the passed object. It assumes that the 
		calling object will be the container of the newly created object.
		"""
		propValDict = self.getPropValDict(obj)
		if name is None:
			name = obj.Name + "1"
		newObj = self.addObject(obj.__class__, 
				name, style=obj.GetWindowStyle() )
		self.applyPropValDict(newObj, propValDict)
		return newObj
		

	# Scroll to the bottom to see the property definitions.

	# Property get/set/delete methods follow.
	
	def _getGeometryTuple(self):
		""" Convert Tkinter's 'widthXheight+left+top' format into a more usable
		set of 2-tuples. The first tuple is (width,height) and the second is
		(left,top). This is used by the various property getters/setters for
		left, top, height, width.
		"""
		g = self.wm_geometry()
		size = tuple([int(k) for k in (g[0:g.find('+')].split('x'))])
		pos = tuple([int(k) for k in (g[g.find('+')+1:].split('+'))])
		return (size, pos)

	def _setGeometryTuple(self, geometryTuple):
		""" Given a geometry tuple, convert and send to Tkinter to be applied.
		"""
		size = geometryTuple[0]
		pos = geometryTuple[1]
		self.wm_geometry("%sx%s+%s+%s" % (size[0], size[1], pos[0], pos[1]))
		


	def _getFont(self):
		return "Not implemented yet."
	
	def _getFontEditorInfo(self):
		return {'editor': 'font'}
	
	def _setFont(self, font):
		dabo.errorLog.write("_setFont not implemented yet.")

		
	def _getFontInfo(self):
		return "Not implemented yet."

	def _getFontBold(self):
		return "Not implemented yet."
	def _setFontBold(self, fontBold):
		dabo.errorLog.write("_setFontBold not implemented yet.")

	def _getFontItalic(self):
		return "Not implemented yet."
	def _setFontItalic(self, fontItalic):
		dabo.errorLog.write("_setFontItalic not implemented yet.")

	def _getFontFace(self):
		return "Not implemented yet."

	def _getFontSize(self):
		return "Not implemented yet."
	def _setFontSize(self, fontSize):
		dabo.errorLog.write("_setFontSize not implemented yet.")

	def _getFontUnderline(self):
		return "Not implemented yet."
	def _setFontUnderline(self, val):
		dabo.errorLog.write("_setFontUnderline not implemented yet.")


	def _getTop(self):
		return self._getGeometryTuple()[1][1]
	def _setTop(self, top):
		size = self._getGeometryTuple()[0]
		pos = list(self._getGeometryTuple()[1])
		pos[1] = top
		pos = tuple(pos)
		self._setGeometryTuple((size, pos))
		
	def _getLeft(self):
		return self._getGeometryTuple()[1][0]
	def _setLeft(self, left):
		size = self._getGeometryTuple()[0]
		pos = list(self._getGeometryTuple()[1])
		pos[0] = left
		pos = tuple(pos)
		self._setGeometryTuple((size, pos))

	def _getPosition(self):
		return self._getGeometryTuple()[1]

	def _setPosition(self, position):
		size = self._getGeometryTuple()[0]
		pos = tuple(position)
		self._setGeometryTuple((size, pos))


	def _getWidth(self):
		return self._getGeometryTuple()[0][0]

	def _getWidthEditorInfo(self):
		return {'editor': 'integer', 'min': 0, 'max': 8192}

	def _setWidth(self, width):
		pos = self._getGeometryTuple()[1]
		size = list(self._getGeometryTuple()[0])
		size[0] = width
		size = tuple(size)
		self._setGeometryTuple((size, pos))


	def _getHeight(self):
		return self._getGeometryTuple()[0][1]

	def _getHeightEditorInfo(self):
		return {'editor': 'integer', 'min': 0, 'max': 8192}

	def _setHeight(self, height):
		pos = self._getGeometryTuple()[1]
		size = list(self._getGeometryTuple()[0])
		size[1] = height
		size = tuple(size)
		self._setGeometryTuple((size, pos))


	def _getSize(self):
		return self._getGeometryTuple()[0]
		
	def _setSize(self, size):
		pos = self._getGeometryTuple()[1]
		size = tuple(size)
		self._setGeometryTuple((size, pos))

	def _getName(self):
		name = self.winfo_name()
		self._name = name      # keeps name available even after C++ object is gone.
		return name
	

	def _getCaption(self):
		return self.wm_title()
	def _setCaption(self, caption):
		self.wm_title(str(caption))

	def _getEnabled(self):
		return self.IsEnabled()
	def _setEnabled(self, value):
		self.Enable(value)


	def _getBackColor(self):
		return self.GetBackgroundColour()

	def _getBackColorEditorInfo(self):
		return {'editor': 'colour'}

	def _setBackColor(self, value):
		self.SetBackgroundColour(value)
		if self == self:
			# Background color changes don't seem to result in
			# an automatic refresh.
			self.Refresh()


	def _getForeColor(self):
		return self.GetForegroundColour()

	def _getForeColorEditorInfo(self):
		return {'editor': 'colour'}

	def _setForeColor(self, value):
		self.SetForegroundColour(value)


	def _getMousePointer(self):
		return self.GetCursor()
	def _setMousePointer(self, value):
		self.SetCursor(value)


	def _getToolTipText(self):
		t = self.GetToolTip()
		if t:
			return t.GetTip()
		else:
			return ''

	def _getToolTipTextEditorInfo(self):
		return {'editor': 'string', 'len': 8192}

	def _setToolTipText(self, value):
		t = self.GetToolTip()
		if t:
			t.SetTip(value)
		else:
			if value:
				t = wx.ToolTip(str(value))
				self.SetToolTip(t)


	def _getHelpContextText(self):
		return self.GetHelpText()
	def _setHelpContextText(self, value):
		self.SetHelpText(str(value))


	def _getVisible(self):
		return self.IsShown()
	def _setVisible(self, value):
		self.Show(bool(value))

	def _getParent(self):
		try:
			parent = self.nametowidget(self.winfo_parent())
		except:
			parent = None
		if isinstance(parent, dPemMixin):
			return parent
		else:
			return None
		
	def _setParent(self, obj):
		return None

	def _getWindowHandle(self):
		return self.GetHandle()

	def _getBorderStyle(self):
		if self.hasWindowStyleFlag(wx.RAISED_BORDER):
			return 'Raised'
		elif self.hasWindowStyleFlag(wx.SUNKEN_BORDER):
			return 'Sunken'
		elif self.hasWindowStyleFlag(wx.SIMPLE_BORDER):
			return 'Simple'
		elif self.hasWindowStyleFlag(wx.DOUBLE_BORDER):
			return 'Double'
		elif self.hasWindowStyleFlag(wx.STATIC_BORDER):
			return 'Static'
		elif self.hasWindowStyleFlag(wx.NO_BORDER):
			return 'None'
		else:
			return 'Default'

	def _getBorderStyleEditorInfo(self):
		return {'editor': 'list', 'values': ['Default', 'None', 'Simple', 'Sunken', 
						'Raised', 'Double', 'Static']}

	def _setBorderStyle(self, style):
		self.delWindowStyleFlag(wx.NO_BORDER)
		self.delWindowStyleFlag(wx.SIMPLE_BORDER)
		self.delWindowStyleFlag(wx.SUNKEN_BORDER)
		self.delWindowStyleFlag(wx.RAISED_BORDER)
		self.delWindowStyleFlag(wx.DOUBLE_BORDER)
		self.delWindowStyleFlag(wx.STATIC_BORDER)

		style = str(style)

		if style == 'None':
			self.addWindowStyleFlag(wx.NO_BORDER)
		elif style == 'Simple':
			self.addWindowStyleFlag(wx.SIMPLE_BORDER)
		elif style == 'Sunken':
			self.addWindowStyleFlag(wx.SUNKEN_BORDER)
		elif style == 'Raised':
			self.addWindowStyleFlag(wx.RAISED_BORDER)
		elif style == 'Double':
			self.addWindowStyleFlag(wx.DOUBLE_BORDER)
		elif style == 'Static':
			self.addWindowStyleFlag(wx.STATIC_BORDER)
		elif style == 'Default':
			pass
		else:
			raise ValueError, ("The only possible values are 'None', "
							"'Simple', 'Sunken', and 'Raised.'")


	# Property definitions follow
	
	WindowHandle = property(_getWindowHandle, None, None,
					'The platform-specific handle for the window. Read-only. (long)')

	Font = property(_getFont, _setFont, None,
					'The font properties of the object. (obj)')
	FontInfo = property(_getFontInfo, None, None,
					'Specifies the platform-native font info string. Read-only. (str)')
	FontBold = property(_getFontBold, _setFontBold, None,
					'Specifies if the font is bold-faced. (bool)')
	FontItalic = property(_getFontItalic, _setFontItalic, None,
					'Specifies whether font is italicized. (bool)')
	FontFace = property(_getFontFace, None, None,
					'Specifies the font face. (str)')
	FontSize = property(_getFontSize, _setFontSize, None,
					'Specifies the point size of the font. (int)')
	FontUnderline = property(_getFontUnderline, _setFontUnderline, None,
					'Specifies whether text is underlined. (bool)')

	Top = property(_getTop, _setTop, None, 
					'The top position of the object. (int)')
	Left = property(_getLeft, _setLeft, None,
					'The left position of the object. (int)')
	Position = property(_getPosition, _setPosition, None, 
					'The (x,y) position of the object. (tuple)')

	Width = property(_getWidth, _setWidth, None,
					'The width of the object. (int)')
	Height = property(_getHeight, _setHeight, None,
					'The height of the object. (int)')
	Size = property(_getSize, _setSize, None,
					'The size of the object. (tuple)')


	Caption = property(_getCaption, _setCaption, None, 
					'The caption of the object. (str)')

	Enabled = property(_getEnabled, _setEnabled, None,
					'Specifies whether the object (and its children) can get user input. (bool)')

	Visible = property(_getVisible, _setVisible, None,
					'Specifies whether the object is visible at runtime. (bool)')                    


	BackColor = property(_getBackColor, _setBackColor, None,
					'Specifies the background color of the object. (tuple)')

	ForeColor = property(_getForeColor, _setForeColor, None,
					'Specifies the foreground color of the object. (tuple)')

	MousePointer = property(_getMousePointer, _setMousePointer, None,
					'Specifies the shape of the mouse pointer when it enters this window. (obj)')
	
 	Name = property(_getName, None, None, 
 					'The name of the object. (str)')
	
	Parent = property(_getParent, _setParent, None,	
					'The containing object. (obj)')

	ToolTipText = property(_getToolTipText, _setToolTipText, None,
					'Specifies the tooltip text associated with this window. (str)')

	HelpContextText = property(_getHelpContextText, _setHelpContextText, None,
					'Specifies the context-sensitive help text associated with this window. (str)')

	BorderStyle = property(_getBorderStyle, _setBorderStyle, None,
					'Specifies the type of border for this window. (int). \n'
					'     None \n'
					'     Simple \n'
					'     Sunken \n'
					'     Raised')


if __name__ == "__main__":
	o = dPemMixin()
	print o.BaseClass
	o.BaseClass = "dForm"
	print o.BaseClass
