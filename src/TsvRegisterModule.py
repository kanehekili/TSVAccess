'''
Created on Apr 2, 2023
This module registers a user:
Open UI and shows a vidcam
Take picture
Add Useer number (prim key)
Generate uuid
print pic +code
add that user to the TsvDB
@author: matze
'''
'''
TODO -read directly from usb - we need the event to pop up...
https://stackoverflow.com/questions/67017165/read-data-from-usb-rfid-reader-using-python
'''
'''
Fetch picture
from PIL import Image
import requests
im = Image.open(requests.get(url, stream=True).raw)
or:
>>> resp=requests.get("http://localhost:5001/TSVPIC/TSV.png")
or img = Image.open(BytesIO(response.content))
>>> type(pic)

'''

# Importing OpenCV package
#TODO use PyQt6
import cv2, sys, traceback, time, argparse, os
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import pyqtSignal, QTimer
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator
from DBTools import OSTools
from TsvDBCreator import SetUpTSVDB
import DBTools
from datetime import datetime
import requests
import TsvDBCreator


class OpenCV3():

    @classmethod
    def setColor(cls, numpyArray):
        cv2.cvtColor(numpyArray, cv2.COLOR_BGR2RGB, numpyArray)  # @UndefinedVariable

    @classmethod
    def getBestCameraIndex(cls):
        best = (-1, -1)  # indx,w*h
        for i in range(8, 0, -1):
            vc = cv2.VideoCapture(i, cv2.CAP_V4L2)
            if vc.isOpened():
                rval, frame = vc.read()
                if rval:
                    height, width, _bytesPerComponent = frame.shape  # numpyArray
                    print("Camera ", i, "ok:", width, ">", height)
                    quality = width * height
                    if best[1] < quality:
                        best = (i, quality)
                else:
                    print("Camera ", i, "found, no read")                    
            else:
                print("Camera ", i, "fails")
        camIndex = best[0]
        if camIndex < 0:
            camIndex = 0
        print("selected camera is:", camIndex)
        return camIndex

    @classmethod
    def getCamera(cls, index):
        cap = cv2.VideoCapture(index, cv2.CAP_V4L2)
        if cap.isOpened():
            rval, _frame = cap.read()
            if rval: 
                return cap
        return None

    def __init__(self, capture=None):
        self._cap = capture
    
    def getCapture(self):
        return self._cap
    
    def getFrameWidth(self):
        return self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)  # @UndefinedVariable
     
    def getFrameHeight(self):
        return self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)  # @UndefinedVariable
    
    def getFrameCount(self):
        return self._cap.get(cv2.CAP_PROP_FRAME_COUNT)  # @UndefinedVariable
    
    def getFPS(self):
        return self._cap.get(cv2.CAP_PROP_FPS)  # @UndefinedVariable
    
    def setFramePosition(self, pos):
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, pos)  # @UndefinedVariable
    
    def getFramePosition(self):
        return self._cap.get(cv2.CAP_PROP_POS_FRAMES)  # @UndefinedVariable
        
    def setAVIPosition(self, pos):
        self._cap.set(cv2.CAP_PROP_POS_AVI_RATIO, pos)  # @UndefinedVariable
        
    def setTimePosition(self, ms):
        self._cap.set(cv2.CAP_PROP_POS_MSEC, ms)  # @UndefinedVariable
        
    def getTimePosition(self):
        return self._cap.get(cv2.CAP_PROP_POS_MSEC)  # @UndefinedVariable
    
    def isOpened(self):
        return self._cap.isOpened()

'''
Unbelievable windows crap: To get your icon into the task bar:
'''
if os.name == 'nt':
    import ctypes
    myappid = 'Register.tsv.access'  # arbitrary string
    cwdll = ctypes.windll  # @UndefinedVariable
    cwdll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)


class CVImage(QtGui.QImage):

    def __init__(self, numpyArray):
        height, width, bytesPerComponent = numpyArray.shape
        dst = numpyArray
        bytesPerLine = bytesPerComponent * width
            
        OpenCV3.setColor(dst)
        super(CVImage, self).__init__(dst.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888)


class VideoWidget(QtWidgets.QFrame):
    """ A class for rendering video coming from OpenCV """
    # trigger = pyqtSignal(float, float, float)
    
    def __init__(self, parent):
        QtWidgets.QFrame.__init__(self, parent)
        self._defaultHeight = 576
        self._defaultWidth = 720
        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self._image = None
        self.imageRatio = 16.0 / 9.0
        self.setFrameStyle(QtWidgets.QFrame.Panel | QtWidgets.QFrame.Sunken)
        self.setLineWidth(1)

    def paintEvent(self, event):
        QtWidgets.QFrame.paintEvent(self, event)
        if self._image is None:
            return
        
        qSize = self.size()
        w = qSize.width()
        h = qSize.height()
        imgY = w / self.imageRatio
        if imgY > h:
            imgY = h
            imgX = self.imageRatio * h
            x = (w - imgX) / 2;
            y = 0
        else:
            imgX = w;
            x = 0
            y = (h - imgY) / 2
        
        painter = QtGui.QPainter(self)
        painter.drawImage(QtCore.QRectF(x, y, imgX, imgY), self._image)
        # painter.end()
        
    def sizeHint(self):
        return QtCore.QSize(self._defaultWidth, self._defaultHeight)

    def showFrame(self, aFrame):
        if aFrame is None:  # showing an error icon...
            self.showPicture('web/static/TSV-big.png')
            return
            
        resy = aFrame.shape[0]
        resx = aFrame.shape[1]
        self.imageRatio = resx / resy
        self._image = CVImage(aFrame)
        self.update()
        
    def showPicture(self, path):
        with open(path, 'rb') as filedata:
            contents = filedata.read();
            self._image = QtGui.QImage()
            self._image.loadFromData(contents, format=None)
            box = self._image.rect()
            self.imageRatio = box.width() / float(box.height())
        self.update()
    
    def showImage(self, img):
        self._image = img
        box = self._image.rect()
        self.imageRatio = box.width() / float(box.height())
        self.update()
        
    def setVideoGeometry(self, ratio, rotation):
        if rotation > 0:
            self.imageRatio = 1.0 / float(ratio)
        else:
            self.imageRatio = float(ratio)       

    '''
    def updateUI(self, frameNumber, framecount, timeinfo):
        self.trigger.emit(frameNumber, framecount, timeinfo)
    '''


# https://gis.stackexchange.com/questions/350148/qcombobox-multiple-selection-pyqt5
class CheckableComboBox(QtWidgets.QComboBox):

    # Subclass Delegate to increase item height
    class Delegate(QtWidgets.QStyledItemDelegate):

        def sizeHint(self, option, index):
            size = super().sizeHint(option, index)
            size.setHeight(20)
            return size

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Make the combo editable to set a custom text, but readonly
        self.setEditable(True)
        self.lineEdit().setReadOnly(True)
        # Make the lineedit the same color as QPushButton
        # palette = qApp.palette()
        # palette.setBrush(QPalette.Base, palette.button())
        # self.lineEdit().setPalette(palette)

        # Use custom delegate
        self.setItemDelegate(CheckableComboBox.Delegate())

        # Update the text when an item is toggled
        self.model().dataChanged.connect(self.updateText)

        # Hide and show popup when clicking the line edit
        self.lineEdit().installEventFilter(self)
        self.closeOnLineEditClick = False

        # Prevent popup from closing when clicking on an item
        self.view().viewport().installEventFilter(self)

    def resizeEvent(self, event):
        # Recompute text to elide as needed
        self.updateText()
        super().resizeEvent(event)

    def eventFilter(self, _object, event):

        if object == self.lineEdit():
            if event.type() == QtCore.QEvent.MouseButtonRelease:
                if self.closeOnLineEditClick:
                    self.hidePopup()
                else:
                    self.showPopup()
                return True
            return False

        if object == self.view().viewport():
            if event.type() == QtCore.QEvent.MouseButtonRelease:
                index = self.view().indexAt(event.pos())
                item = self.model().item(index.row())

                if item.checkState() == QtCore.Qt.Checked:
                    item.setCheckState(QtCore.Qt.Unchecked)
                else:
                    item.setCheckState(QtCore.Qt.Checked)
                return True
        return False

    def showPopup(self):
        super().showPopup()
        # When the popup is displayed, a click on the lineedit should close it
        self.closeOnLineEditClick = True

    def hidePopup(self):
        super().hidePopup()
        # Used to prevent immediate reopening when clicking on the lineEdit
        self.startTimer(100)
        # Refresh the display text when closing
        self.updateText()

    def timerEvent(self, event):
        # After timeout, kill timer, and reenable click on line edit
        self.killTimer(event.timerId())
        self.closeOnLineEditClick = False

    def updateText(self):
        texts = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == QtCore.Qt.Checked:
                texts.append(self.model().item(i).text())
        text = ", ".join(texts)

        # Compute elided text (with "...")
        metrics = QtGui.QFontMetrics(self.lineEdit().font())
        elidedText = metrics.elidedText(text, QtCore.Qt.ElideRight, self.lineEdit().width())
        self.lineEdit().setText(elidedText)

    def addItem(self, text, data=None):
        item = QtGui.QStandardItem()
        item.setText(text)
        if data is None:
            item.setData(text)
        else:
            item.setData(data)
        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable)
        item.setData(QtCore.Qt.Unchecked, QtCore.Qt.CheckStateRole)
        self.model().appendRow(item)

    def addItems(self, texts, datalist=None):
        for i, text in enumerate(texts):
            try:
                data = datalist[i]
            except (TypeError, IndexError):
                data = None
            self.addItem(text, data)

    def currentData(self):
        # Return the list of selected items data
        res = []
        for i in range(self.model().rowCount()):
            if self.model().item(i).checkState() == QtCore.Qt.Checked:
                res.append(self.model().item(i).data())
        return res

    # mark items in data or textarray as selected
    def selectData(self, textArray):
        # TODO
        pass


# #Main App Window. 
class MainFrame(QtWidgets.QMainWindow):
    
    def __init__(self, qapp, cameraIndex):
        self._isStarted = False
        self.__qapp = qapp
        self.model = Registration(cameraIndex)
        self.cameraThread = None
        self.qtQueueRunning = False
        self.capturing = False
        self.photoTaken = False
        
        super(MainFrame, self).__init__()
        self.setWindowIcon(getAppIcon())
        self._widgets = self.initUI()
        self.centerWindow()
        # self._widgets.enableUserActions(False)
        self.setWindowTitle("Registrierung für TSV Mitglieder")
        self.show()
        qapp.applicationStateChanged.connect(self.__queueStarted)    

    def centerWindow(self):
        frameGm = self.frameGeometry()
        screen = QApplication.desktop().screenNumber(QApplication.desktop().cursor().pos())
        centerPoint = QApplication.desktop().screenGeometry(screen).center()
        frameGm.moveCenter(centerPoint)
        self.move(frameGm.topLeft())
        
    def initUI(self):
        # #some default:
        # self.init_toolbar()
        self.ui_VideoFrame = VideoWidget(self)
        self.ui_VideoFrame.setToolTip("Warten bis ein grüner Rahmen angezeigt wird, dann 'Photo' Knopf drücken") 
        
        self.ui_PhotoButton = QtWidgets.QPushButton()
        self.updatePhotoButton()
        self.ui_PhotoButton.clicked.connect(self._onPhotoButtonClicked)
        self.ui_PhotoButton.setToolTip("Wechsel zwischen Video und Photo machen")
        
        self.ui_SearchLabel = QtWidgets.QLabel(self)
        self.ui_SearchLabel.setText("Suche:")
        
        self.ui_SearchEdit = QtWidgets.QComboBox(self)
        self.ui_SearchEdit.setEditable(True)  # Is that right??
        # self.ui_SearchEdit.currentIndexChanged.connect(self._onSearchChanged)
        self.ui_SearchEdit.setInsertPolicy(QtWidgets.QComboBox.NoInsert);
        self.ui_SearchEdit.completer().setCompletionMode(QtWidgets.QCompleter.PopupCompletion);
        self.ui_SearchEdit.activated.connect(self._onSearchChanged)
        self.ui_SearchEdit.setToolTip("Nachnamen eingeben, um eine Person zu suchen")
        #self.ui_SearchEdit.installEventFilter(self)
        
        # self.ui_SearchEdit.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        
        self.ui_IDLabel = QtWidgets.QLabel(self)
        self.ui_IDLabel.setText("Nummer:")
        self.ui_IDEdit = QtWidgets.QLineEdit(self)
        self.ui_IDEdit.setValidator(QtGui.QIntValidator(1, 100000, self))
        self.ui_IDEdit.setValidator(QRegExpValidator(QRegExp('^([1-9][0-9]*\.?|0\.)[0-9]+$'), self))
        self.ui_IDEdit.setToolTip("Die Conplan <Adressnummer> ist hier einzutragen")

        self.ui_FirstNameLabel = QtWidgets.QLabel(self)
        self.ui_FirstNameLabel.setText("Vorname:")
        self.ui_FirstNameEdit = QtWidgets.QLineEdit(self)
        self.ui_FirstNameEdit.setToolTip("Vorname des Mitglieds (Wird bei Suche übernommen)")
        
        self.ui_LastNameLabel = QtWidgets.QLabel(self)
        self.ui_LastNameLabel.setText("Nachname:")
        self.ui_LastNameEdit = QtWidgets.QLineEdit(self)
        self.ui_LastNameEdit.setToolTip("Nachname des Mitglieds (Wird bei Suche übernommen)")

        self.ui_RFIDLabel = QtWidgets.QLabel(self)
        self.ui_RFIDLabel.setText("RFID Nummer")
        self.ui_RFID = QtWidgets.QLineEdit(self)
        self.ui_RFID.setToolTip("RFID mit Kartenleser einchecken - Erst draufclicken -dann scannen!")
        self.ui_RFID.textEdited.connect(self._onRFIDRead)
        #self.ui_RFID.installEventFilter(self)

        self.ui_AccessLabel = QtWidgets.QLabel(self)
        self.ui_AccessLabel.setText("Merkmale:")
        self.ui_AccessLabel.setToolTip("Hier kann der Zugangscode (Multi3) angepasst werden - aktuell nur einer")
        
        self.ui_AccessCombo = QtWidgets.QComboBox(self)
        # self.ui_AccessCombo = CheckableComboBox(self)
        # TODO Wrong- location/group agnostic... 
        themes = TsvDBCreator.ACCESSCODES
        self.ui_AccessCombo.addItem("-")
        for item in themes:
            self.ui_AccessCombo.addItem(item)
        self.ui_AccessCombo.setCurrentText("")  # self.model.iconSet
        self.ui_AccessCombo.currentTextChanged.connect(self._onAccessChanged)
        # self.ui_AccessCombo.setToolTip("Angabe der Zugangsbereiche (Mehrfachwahl möglich)")
        self.ui_AccessCombo.setToolTip("Angabe des Zugangsbereichs")

        self.ui_BirthLabel = QtWidgets.QLineEdit(self)
        self.ui_BirthLabel.setText("")
        self.ui_BirthLabel.setReadOnly(True);
        self.ui_BirthLabel.setToolTip("Geburtstag (nicht veränderbar)")

        self.ui_CreateButton = QtWidgets.QPushButton()
        self.ui_CreateButton.setText("   Speichern")
        self.ui_CreateButton.setIcon(QtGui.QIcon("./web/static/save.png"))
        self.ui_CreateButton.clicked.connect(self._onSaveMember)
        self.ui_CreateButton.setToolTip("In Datenbank speichern und Zugang erlauben")

        self.ui_AboButton = QtWidgets.QPushButton()
        self.ui_AboButton.setText("  Abo + Sperren")
        self.ui_AboButton.setIcon(QtGui.QIcon("./web/static/ticket.png"))
        self.ui_AboButton.clicked.connect(self._onOpenAboDialog)
        self.ui_AboButton.setToolTip("10er Karten anlegen")
        self.ui_AboButton.setEnabled(False)

        # geht immer
        self.ui_ExitButton = QtWidgets.QPushButton()
        # self.ui_ExitButton = QtWidgets.QToolButton()
        # self.ui_ExitButton.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        self.ui_ExitButton.setText("            Neu")
        self.ui_ExitButton.setIcon(QtGui.QIcon("./web/static/new.png"))
        self.ui_ExitButton.clicked.connect(self._onNewClicked)
        self.ui_ExitButton.setToolTip("Ein weiters Mitglied einchecken")
        
        box = self.makeGridLayout()
        
        # Without central widget it won't work
        wid = QtWidgets.QWidget(self)
        self.setCentralWidget(wid)        
        wid.setLayout(box)
        self.adjustSize()

    def eventFilter(self,widget,event):
        if widget != self.ui_SearchEdit:
            if event.type()==QtCore.QEvent.FocusIn:
                print("Focus in")
                self.ui_SearchEdit.clearFocus()
                #return False
            #return False
        return super(MainFrame,self).eventFilter(widget,event)
                

    def init_toolbar(self):
        # QtGui.QAction Py6
        self.newAction = QtWidgets.QAction(QtGui.QIcon('./web/static/new.png'), 'Neu anlegen', self)
        self.newAction.setShortcut('Ctrl+N')
        self.newAction.triggered.connect(self.xxx)

        self.photoAction = QtWidgets.QAction(QtGui.QIcon('./web/static/video.png'), 'Kamera/Photo', self)
        self.photoAction.setShortcut('Ctrl+P')
        self.photoAction.triggered.connect(self.xxx)

        self.aboAction = QtWidgets.QAction(QtGui.QIcon('./web/static/ticket.png'), 'Ticket Verkauf', self)
        self.aboAction.setShortcut('Ctrl+T')
        self.aboAction.triggered.connect(self.xxx)

        self.saveAction = QtWidgets.QAction(QtGui.QIcon('./web/static/video.png'), 'Speichern', self)
        self.saveAction.setShortcut('Ctrl+S')
        self.saveAction.triggered.connect(self.xxx)
                
        self.toolbar = self.addToolBar('Main')
        self.toolbar.addAction(self.newAction)
        self.toolbar.addAction(self.photoAction)
        self.toolbar.addSeparator()
        self.toolbar.addAction(self.aboAction)
        self.toolbar.addAction(self.saveAction)

    def xxx(self):
        print("test")

    # simple toggle
    def updatePhotoButton(self):
        if self.capturing:
            self.ui_PhotoButton.setText("Photo")
        else: 
            self.ui_PhotoButton.setText("Web Cam")            

    # fill the search combo
    def fillSearchCombo(self, memberList):
        self.ui_SearchEdit.clear()
        self.ui_SearchEdit.addItem("", None)
        for member in memberList:
            entry = member.searchName()
            self.ui_SearchEdit.addItem(entry, member)
            
    def updateAboButton(self, mbr):
        self.ui_AboButton.setEnabled(mbr is not None)

    def makeGridLayout(self):
        # fromRow(y) - fromColumn(x)  rowSpan(height) columnSpan(width), ggf alignment
        gridLayout = QtWidgets.QGridLayout()
        gridLayout.addWidget(self.ui_VideoFrame, 0, 1, 4, -1);

        gridLayout.addWidget(self.ui_SearchLabel, 4, 1, 1, 1)
        gridLayout.addWidget(self.ui_SearchEdit, 4, 2, 1, 3)
        
        gridLayout.addWidget(self.ui_PhotoButton, 4, 5, 1, 1)
        
        line = QtWidgets.QFrame();
        line.setFrameShape(QtWidgets.QFrame.HLine);
        line.setFrameShadow(QtWidgets.QFrame.Sunken);
    
        gridLayout.addWidget(line, 5, 1, 1, -1)
        
        gridLayout.addWidget(self.ui_IDLabel, 7, 1, 1, 1)
        gridLayout.addWidget(self.ui_IDEdit, 7, 2, 1, 4)

        gridLayout.addWidget(self.ui_FirstNameLabel, 8, 1, 1, 1)
        gridLayout.addWidget(self.ui_FirstNameEdit, 8, 2, 1, 4)

        gridLayout.addWidget(self.ui_LastNameLabel, 9, 1, 1, 1)
        gridLayout.addWidget(self.ui_LastNameEdit, 9, 2, 1, 4)

        gridLayout.addWidget(self.ui_RFIDLabel, 10, 1, 1, 1)
        gridLayout.addWidget(self.ui_RFID, 10, 2, 1, 4)
        
        gridLayout.addWidget(self.ui_AccessLabel, 11, 1, 1, 1)
        gridLayout.addWidget(self.ui_AccessCombo, 11, 2, 1, 2)
        gridLayout.addWidget(self.ui_BirthLabel, 11, 4, 1, 2)
        
        line = QtWidgets.QFrame();
        line.setFrameShape(QtWidgets.QFrame.HLine);
        line.setFrameShadow(QtWidgets.QFrame.Sunken);
        
        gridLayout.addWidget(line, 12, 1, 1, -1)
        
        gridLayout.addWidget(self.ui_ExitButton, 13, 1, 1, 1)
        gridLayout.addWidget(self.ui_AboButton, 13, 3, 1, 1)
        gridLayout.addWidget(self.ui_CreateButton, 13, 5, 1, 1)
        
        gridLayout.setRowStretch(1, 1)

        return gridLayout

    def setEntryFields(self, mbr):  # TODO
        self.ui_IDEdit.setText(mbr.primKeyString())
        self.ui_FirstNameEdit.setText(mbr.firstName)
        self.ui_LastNameEdit.setText(mbr.lastName)
        self.ui_AccessCombo.setCurrentText(mbr.access)
        self.ui_BirthLabel.setText(mbr.birthdayString())
        self.ui_RFID.setText(mbr.rfidString())
        # self.ui_AccessCombo.do-sth    
 
    # The widget callbacks
    @QtCore.pyqtSlot(str)
    # Zugangs kontrolle - not designated
    def _onAccessChanged(self, text):
        #Log.info("Accessmode:%s", text)
        pass

    @QtCore.pyqtSlot()
    def _onPhotoButtonClicked(self):
        if self.capturing:
            self.capturing = False
            if self.model.takeScreenshot("/tmp/tsv.screenshot.png"):
                self.photoTaken = True
                self.cameraThread.showFrame(self.model.getFrame())
            else:
                self.getMessageDialog("Kein Photo gespeichert!", "Es konnte kein Gesicht erkannt werden \nBitte nochmals probieren").show()
                self.photoTaken = False
            self.updatePhotoButton()
        else:
            self._initCapture()

    @QtCore.pyqtSlot(int)
    def _onSearchChanged(self, idx):
        mbr = self.ui_SearchEdit.itemData(idx)
        if mbr:
            Log.info("Member selected:%s",mbr.searchName())
            self.setEntryFields(mbr)
            #Still having the focus, so add it to the event loop
            QTimer.singleShot(1, self.ui_RFID.setFocus)
            
            if not (mbr.picpath and self._displayMemberFace(mbr)):
                self._initCapture()  # fastCam !TODO NO just turn on cam...
            self.updateAboButton(mbr)

    @QtCore.pyqtSlot()
    def _onNewClicked(self):
        self.ui_SearchEdit.setCurrentIndex(-1)
        self._clearFields()        
    
    @QtCore.pyqtSlot(str)            
    def _onRFIDRead(self, rfid):
        if len(rfid) < 9: #typing
            return
        Log.info("Checking RFID:%s", rfid)
        if not rfid:
            return;
        
        if self.model.containsLegacyAA(rfid):
            res = self.getQuestionDialog("Vorsicht!", "Hat der Benuzter einen blauen Chip für Zugang?")
            if not res:
                Log.warning("AssaAbloy RFID chip found: %s", rfid)
                self.ui_RFID.clear()
                return
        
        mbr = self.ui_SearchEdit.currentData()
        testId = None
        if mbr:
            testId = mbr.id
        if not self.model.verifyRfid(rfid, testId):
            d = self.getErrorDialog("** RFID **", "Ungültige RFID, bitte einen anderen Token benutzen", "In der Datenbank existiert bereits eine solche RFID Nummer und kann nicht nochmal vergeben werden")
            d.show()
            self.ui_RFID.clear()

    # persist to database (Speichern)
    # Store & contrl picture only if not in mbr
    @QtCore.pyqtSlot()
    def _onSaveMember(self):
        mbr = self.ui_SearchEdit.currentData()
        idstr = self.ui_IDEdit.text()
        firstName = self.ui_FirstNameEdit.text()
        lastName = self.ui_LastNameEdit.text()
        access = self.ui_AccessCombo.currentText()
        birthdate = self.ui_BirthLabel.text()
        rfid = self.ui_RFID.text()
        photoSaved = mbr is not None and mbr.picpath is not None
        
        msg = ""
        if not idstr:
            msg = "Mitgliedsnr ? \n"
        if not firstName:
            msg = msg + "Vorname ? \n"
        if not lastName:
            msg = msg + "Nachname ? \n"
        if not access:
            msg = msg + "Zugangscode ? \n"
        if not (self.photoTaken or photoSaved):
            msg = msg + "Photo ? \n"
        if not rfid:
            msg = msg + "RFID Code ? \n"
           
        if len(msg) > 0: 
            self.getErrorDialog("Eingabefehler", "Bitte alle Felder ausfüllen", msg,mail=False).show()
            Log.warning("Data error:%s", msg)
            return

        mid = int(idstr)
        rfid_int = int(rfid)
        # we should update in the correct form
        if mbr is not None:
            bd = mbr.asDBDate(birthdate)
            mbr.update(mid, firstName, lastName, access, bd, rfid_int)
            self.ui_SearchEdit.setEditText(mbr.searchName())
        else:
            # create new member, update search box
            mbr = Mitglied(mid, firstName, lastName, access, None, rfid_int)
            entry = mbr.searchName()
            self.ui_SearchEdit.addItem(entry, mbr)
        # need a try catch.
        if self.photoTaken:
            res = self.model.savePicture(mbr)  # scps the pic to remote and adds uri to db...
            if not res:
                self.getErrorDialog("Verbindungsfehler", "Bild konnte nicht gespeichert werden", "Der Fehler wurde per eMail gemeldet!").show()
                self.photoTaken = False
                return  # only all or nothing
        QTimer.singleShot(0, lambda: self.model.updateMember(mbr))
        # self.model.updateMember(mbr)
        # self.model.printMemberCard(mbr)
        self.photoTaken = False
        self._clearFields()

    @QtCore.pyqtSlot()
    def _onOpenAboDialog(self):
        mbr = self.ui_SearchEdit.currentData()
        if not mbr:
            Log.warning("Abo call with no member!")
            return
        self.model.readAboData(mbr)
        dlg = AboDialog(self, mbr)
        dlg.show()  # async - dialog has to to the work
        
    def _clearFields(self):
        self.ui_SearchEdit.clearEditText()
        self.ui_IDEdit.clear()
        self.ui_FirstNameEdit.clear()
        self.ui_LastNameEdit.clear()
        self.ui_AccessCombo.clearEditText()       
        self.ui_BirthLabel.clear()
        self.ui_RFID.clear()
        self.model.cameraOn = False
        self.capturing = False
        self.updatePhotoButton()
        self.updateAboButton(None)
        self.cameraThread.showFrame(None)  # Icon
         
    # dialogs
    def __getInfoDialog(self, text):
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowModality(QtCore.Qt.WindowModal)
        dlg.setWindowTitle("Information")
        layout = QtWidgets.QVBoxLayout(dlg)
        label = QtWidgets.QLabel(text)
        label.sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        label.setSizePolicy(label.sizePolicy)
        label.setMinimumSize(QtCore.QSize(300, 40))
        layout.setSizeConstraint(QtWidgets.QLayout.SetFixedSize)
        layout.addWidget(label)
        return dlg

    def getErrorDialog(self, text, infoText, detailedText,mail=True):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setIcon(QtWidgets.QMessageBox.Warning)
        dlg.setWindowModality(QtCore.Qt.WindowModal)
        dlg.setWindowTitle("Fehler")
        dlg.setText(text)
        dlg.setInformativeText(infoText)
        dlg.setDetailedText(detailedText)
        dlg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        spacer = QtWidgets.QSpacerItem(300, 50, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        layout = dlg.layout()
        layout.addItem(spacer, layout.rowCount(), 0, 1, layout.columnCount())
        msg=infoText+"\n DETAIL:"+detailedText
        if mail:
            self.model.mailError(msg)
        return dlg
    
    def getMessageDialog(self, text, infoText):
        # dlg = DialogBox(self)
        dlg = QtWidgets.QMessageBox(self)
        dlg.setIcon(QtWidgets.QMessageBox.Information)
        dlg.setWindowModality(QtCore.Qt.WindowModal)
        dlg.setWindowTitle("Hinweis")
        dlg.setText(text)
        dlg.setInformativeText(infoText)
        dlg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        # Workaround to resize a qt dialog. WTF!
        spacer = QtWidgets.QSpacerItem(300, 5, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        layout = dlg.layout()
        layout.addItem(spacer, layout.rowCount(), 0, 1, layout.columnCount())
        
        # dlg.setMinimumSize(450, 0)
        return dlg;        
    
    def getQuestionDialog(self, title, text):
        buttonReply = QtWidgets.QMessageBox().question(self, title, text,);
        return buttonReply == QtWidgets.QMessageBox.Yes
    
    @QtCore.pyqtSlot()
    def _displayFrame(self):
        self.ui_VideoFrame.showFrame(self.cameraThread.result)
    
    @QtCore.pyqtSlot(str)
    def _showCameraError(self, text):
        dlg = self.getErrorDialog("Kamerafehler", text, "Ein Kamerafehler ist aufgetreten. Häufigste Ursache ist, das sie nicht gefunden werden kann.")
        dlg.show()
    
    def __queueStarted(self, _state):
        if self.qtQueueRunning:
            return
        self.qtQueueRunning = True
        self.ui_VideoFrame.showFrame(None)
        
        self.cameraThread = CameraThread(self.model.activateCamera)
        self.cameraThread.signal.connect(self._displayFrame)
        self._initModel()
    
    def _displayMemberFace(self, member):
        raw = self.model.loadPicture(member)
        if raw == None:
            self.getErrorDialog("Verbindungsproblem", "Server ist nicht erreichbar", "Der Server, der die Bilder  liefern soll ist nicht erreichbar - Der Fehler wurde per eMail gemeldet").show()
            return False
        try:
            self.model.cameraOn = False
            self.capturing = False
            img = QtGui.QImage()
            img.loadFromData(raw)
            self.ui_VideoFrame.showImage(img)
            self.updatePhotoButton()
        except:
            Log.exception("Pic load failed")
            return False
        return True
    
    def _initCapture(self):
        self.capturing = True
        QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        self.updatePhotoButton()
        self.cameraThread.start()
        while not self.model.cameraOn:
            if self.model.cameraStatus is None:
                time.sleep(0.2)
            else:
                self._showCameraError(self.model.cameraStatus)
                break
        QApplication.restoreOverrideCursor()

    def _initModel(self):
        QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        if not self.model.startCamera():
            self._showCameraError(self.model.cameraStatus)
        
        res = self.model.connect()
        QApplication.restoreOverrideCursor()
        if not res:
            dlg = self.getErrorDialog("Datenbank Fehler ", "Datenbank nicht gefunden", "Es besteht keine Verbindung zur Datenbank. Bitte melden!",mail=False)
            dlg.buttonClicked.connect(self._onErrorDialogClicked)
            dlg.show()
        else:
            memberList = self.model.getMembers()
            self.fillSearchCombo(memberList)
            
        return res

    def _onErrorDialogClicked(self, _):
        self.close()

    def closeEvent(self, event):
        self.model.stopCamera()
        self.cameraThread.quit()
        self.cameraThread.wait()
        try:
            super(MainFrame, self).closeEvent(event)
        except:
            Log.exception("Error Exit")   

            
class AboDialog(QtWidgets.QDialog):

    def __init__(self, parent, member):
        super(AboDialog, self).__init__(parent)
        self.model = member
        self.init_ui()

    def init_ui(self):
        self.setWindowModality(QtCore.Qt.WindowModal)
        self.setWindowTitle("Abo & Sperren")
        frame1 = QtWidgets.QFrame()
        frame1.setFrameStyle(QtWidgets.QFrame.Box | QtWidgets.QFrame.Sunken)
        frame1.setLineWidth(1)
        aboBox = QtWidgets.QVBoxLayout(frame1)
        hBox = QtWidgets.QHBoxLayout(frame1)
        prepaid = self.model.currentAbo[1]
        self.saunaCount= QtWidgets.QSpinBox()
        self.saunaCount.setValue(prepaid)
        self.saunaCount.valueChanged.connect(self._prepaidChanged)
        self.check_sauna = QtWidgets.QCheckBox("Sauna 10er Ticket \tfrei:")
        
        self.check_sauna.setToolTip("Haken = 10 Tickets kaufen")
        # TODO check current abo count and flag 
        
        self.check_culprit = QtWidgets.QCheckBox("Mitglied sperren")
        self.check_culprit.setToolTip("Bei Haken wird kein Zugang erlaubt")
        self.check_culprit.setChecked(self.model.flag > 0)
        
        hBox.addWidget(self.check_sauna)
        hBox.addWidget(self.saunaCount)
        aboBox.addLayout(hBox)
        aboBox.addWidget(self.check_culprit)
        
        QBtn = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        
        outBox = QtWidgets.QVBoxLayout()
        outBox.addWidget(frame1)
        outBox.addWidget(buttonBox)
        self.setLayout(outBox)
        self.setMinimumSize(400, 0)

    @QtCore.pyqtSlot(int)
    def _prepaidChanged(self,val):
        self.model.abo = (TsvDBCreator.ACTIVITY_SAUNA,0)
        self.model.currentAbo = (TsvDBCreator.ACTIVITY_SAUNA,self.saunaCount.value())
        
    def accept(self):
        #Must be possible to change the prepaid data without having checked
        if self.check_sauna.isChecked():
            self.model.abo = (TsvDBCreator.ACTIVITY_SAUNA, 10)
        self.model.flag = int(self.check_culprit.isChecked() == True)
        super().accept()


class CameraThread(QtCore.QThread):
    signal = pyqtSignal()
    # error= pyqtSignal(str)
    result = None

    def __init__(self, func):
        QtCore.QThread.__init__(self)
        self.func = func

    def run(self):
        self.func(self)

    def showFrame(self, frame):
        self.result = frame
        self.signal.emit()


###DEMO ###
def __DEMO__headRec(): 
    camera_id = 0
    delay = 1
    window_name = 'OpenCV Onboarding'
    cap = cv2.VideoCapture(camera_id)
    # Loading the required haar-cascade xml classifier file
    haar_cascade = cv2.CascadeClassifier('/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml') 
    # haar_cascade = cv2.CascadeClassifier('./data/upper_body.xml')
    # Reading the image
    while True:
        ret, frame = cap.read()
    
        if ret:
            # Converting image to grayscale
            gray_img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      
            # Applying the face detection method on the grayscale image
            # faces_rect = haar_cascade.detectMultiScale(gray_img,scaleFactor=1.1, minNeighbors=9)
            faces_rect = haar_cascade.detectMultiScale(gray_img, scaleFactor=1.3, minNeighbors=9)
      
            # Iterating through rectangles of detected faces
            for (x, y, w, h) in faces_rect:
                offsetX = round(w / 2)
                offsetY = round(h / 2)
                cv2.rectangle(frame, (x - offsetX, y - offsetY), (x + w + offsetX, y + h + offsetY), (0, 255, 0), 2)
      
            cv2.imshow(window_name, frame)
      
        if cv2.waitKey(delay) & 0xFF == ord('q'):
            break
    
    cv2.destroyWindow(window_name)


class Registration():
    SAVEPIC = "/tmp/tsv.screenshot.png"   

    def __init__(self, cameraIndex):
        # self.accesscodes = []
        self.currentFrame = None
        self.croppedPic =None
        self.borders = []
        self.cameraOn = False
        self.cameraStatus = None
        self.camIndex = cameraIndex
        self.cam = None
        self.dimension = [0, 0]
        self.aaTransponders = []

    def connect(self):
        self.dbSystem = SetUpTSVDB(SetUpTSVDB.DATABASE)
        self.db = self.dbSystem.db
        if self.dbSystem.isConnected():
            self.readAATransponders()
            return True
        return False
    
    def readAATransponders(self):
        # tODO That is TABLE now!
        '''
        path = OSTools.getLocalPath(__file__)
        tr = OSTools.joinPathes(path, "data", "AATransponder")
        with open(tr,"r") as file:
            raw=file.read()
            self.AATransponders=raw.split(';')
        '''
        stmt = "Select uuid from %s" % (SetUpTSVDB.ASSAABLOY)
        rows = self.db.select(stmt)
        for uuid in rows:
            self.aaTransponders.append(uuid[0]) 
        Log.info("Loaded AA Transponders:%d", len(self.aaTransponders))
    
    def containsLegacyAA(self, rfid):
        return rfid in self.aaTransponders
    
    # reads the list and passes it to the caller...
    def getMembers(self):
        fields = ','.join(Mitglied.FIELD_DEF)  # FIELD_DEF=('id','first_name','last_name','access','birth_date,picpath,uuid,flag') 
        # stmt = "SELECT id,first_name,last_name from " + self.dbSystem.MAINTABLE
        stmt = "SELECT " + fields + " from " + self.dbSystem.MAINTABLE
        col = []
        # currently: [(1234, 'Merti', 'quanz'), (1236, 'Cora', 'Schnell')]
        res = self.db.select(stmt)
        for titem in res:
            # id(int) (str) (str) (str) date! int
            m = Mitglied(titem[0], titem[1], titem[2], titem[3], titem[4], titem[6])
            m.picpath = titem[5]
            m.flag = titem[7]
            col.append(m)
        return col
    
    def updateMember(self, mbr):
        table = self.dbSystem.MAINTABLE
        fields = Mitglied.FIELD_SAVE_DEF
        data = mbr.dataSaveArray()
        Log.info("Saving memmber:%s", str(data[0]))
        self.db.insertMany(table, fields, data)
        self.updateAboData(mbr) 
    
    def updateAboData(self, mbr):
        section = mbr.abo[0]
        if section is None:
            return
        oldCount = mbr.currentAbo[1]
        newCount=mbr.abo[1]
        fields = ('mitglied_id', 'section', 'prepaid')
        data = [(mbr.id, section, oldCount + mbr.abo[1])]
        Log.info("Update ABO prepaid count from %s , %d +%d", section, oldCount,newCount)
        if newCount>0: #stays 0 if old has been changed
            msg="Mitglied Nr %d (%s %s) \nhat heute ein 10er Abo bestellt - als Erinnerung zum abbuchen \U0001f604"%(mbr.id,mbr.firstName,mbr.lastName)
            self.dbSystem.sendEmail("Sauna Abo Daten", True, msg)
            
        self.db.insertMany(self.dbSystem.BEITRAGTABLE, fields, data)

    def readAboData(self, mbr):
        section = TsvDBCreator.PREPAID_INDICATOR[0]  # currently only one
        stmt = "select prepaid from BEITRAG where mitglied_id=%d and section='%s'" % (mbr.id, section)
        rows = self.db.select(stmt)
        if len(rows) == 0:
            Log.debug("No Abo data")
            return
        mbr.currentAbo = (section, rows[0][0])
        Log.info("Abo count:%d", rows[0][0])
    
    def mailError(self,msg):
        self.dbSystem.sendEmail("Registration Error Msg", False, msg)
    
    def startCamera(self):
        self.cam = OpenCV3.getCamera(self.camIndex)
        Log.info("cam found")
        self.cameraStatus = None       
        if self.cam is None or not self.cam.isOpened():
            Log.warning("Camera not found!")
            self.cameraStatus = "Keine Kamera gefunden"
            return False

        self.dimension[0] = self.cam.get(cv2.CAP_PROP_FRAME_WIDTH)  # @UndefinedVariable
        self.dimension[1] = self.cam.get(cv2.CAP_PROP_FRAME_HEIGHT)  # @UndefinedVariable
        Log.info("Cam resolution: %d@%d", self.dimension[0], self.dimension[1])
        return True
    
    # we need some sane values.Try with at least 300 pix in size.
    def activateCamera(self, cameraThread):
        self.borders = []
        if self.cam is None:
            return
        cap = self.cam    
        self.currentFrame = None
        
        # Loading the required haar-cascade xml classifier file
        # TODO won't work on windows add it locally: https://github.com/opencv/opencv/tree/master/data/haarcascades
        # improve: https://gist.github.com/UnaNancyOwen/3f06d4a0d04f3a75cc62563aafbac332
        # chinese solution https://github.com/opencv/opencv_zoo/blob/main/models/face_detection_yunet/demo.py -CPU!
        haar_cascade = cv2.CascadeClassifier('/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml') 
        # haar_cascade = cv2.CascadeClassifier('./data/upper_body.xml')
        # Reading the image
        self.cameraOn = True
        # emit signal?
        while self.cameraOn:
            ret, frame = cap.read()
        
            if ret:
                # Converting image to grayscale
                gray_img = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
          
                # Applying the face detection method on the grayscale image
                # faces_rect = haar_cascade.detectMultiScale(gray_img,scaleFactor=1.1, minNeighbors=9)
                faces_rect = haar_cascade.detectMultiScale(gray_img, scaleFactor=1.2, minNeighbors=7, minSize=(100, 120))
                # Iterating through rectangles of detected faces
                for (x, y, w, h) in faces_rect:
                    offsetX = round(w / 2)
                    offsetY = round(h / 2)
                    left = x - offsetX
                    top = y - offsetY
                    right = x + w + offsetX
                    bottom = y + h + offsetY
                    col = (0, 255, 0)
                    bok = True
                    # raw data
                    if left < 0 or right > self.dimension[0]:
                        col = (0 , 0, 255)
                        bok = False
                    if top < 0 or bottom > self.dimension[1]:
                        col = (0 , 0, 255)
                        bok = False

                    cv2.rectangle(frame, (left, top), (right, bottom), col, 2)

                    px = max(0, left + 2)
                    py = max(0, top + 2)
                    dw = right - px - 2
                    dh = bottom - py - 2;
                    if bok and self.cameraOn:
                        self.borders = [px, py, dw, dh]
                        self.currentFrame = frame
                
                if self.cameraOn: 
                    cameraThread.showFrame(frame)

    def takeScreenshot(self, path):
        self.cameraOn = False
        self.croppedPic = None
        if self.currentFrame is None or len(self.borders) == 0:
            Log.info("Screenshot failed")
            return False
        x = self.borders[0]
        y = self.borders[1]
        w = self.borders[2]
        h = self.borders[3]
        #Log.info("Crop photo dim: %d/%d > %d/%d", x, y, w, h)
        self.croppedPic = cv2.cvtColor(self.currentFrame[y:y + h, x:x + w].copy(),cv2.COLOR_RGB2BGR)
        cv2.imwrite(path, self.croppedPic) #save picture needs that
        return True   

    def getFrame(self):
        return self.croppedPic

    def stopCamera(self):
        self.cameraOn = False
        if self.cam:
            self.cam.release()        
        
    # dont- save pic with member name on remote device via scp or smb.     
    def __deprecated_printMemberCard(self, member):
        # generate OCR for now    
        # get both images & convert: left to right (else -append)
        # convert +append image_1.png image_2.png -resize x500 new_image_conbined.png
        data = str(member.id) + "," + member.searchName()
        cmd1 = ["/usr/bin/qrencode", "-o", "/tmp/qr.png", "-s", "6", data]
        res = DBTools.runExternal(cmd1)
        print(res)
        # possible density stuff. We need to ensure that the saved size is independent of the camera!
        # montage card[1-4]*.png -tile 2x2+140+140 -geometry 382x240+65+52 -density 100 cards.pdf
        cmd2 = ["/usr/bin/convert", "+append", "/tmp/tsv.screenshot.png", "/tmp/qr.png", "-resize", "x400", "/tmp/member.png" ]
        res = DBTools.runExternal(cmd2)
        print(res)

    # beware_ connection could be broken
    def savePicture(self, member):
        self.db.ensureConnection() 
        saved = Registration.SAVEPIC       
        targetPath = SetUpTSVDB.PICPATH
        pic = member.lastName + "-" + member.primKeyString() + ".png"
        
        host = SetUpTSVDB.HOST
        response = None
        try:
            reqUrl = "http://%s:5001/%s/%s" % (host, targetPath, pic)     
            Log.info("Saving picture :%s" % (reqUrl)) 
            # reqUrl="http://localhost:5001/TSVPIC/"+pic #works!
            response = requests.post(reqUrl, files={'file':open(saved, 'rb')})
        except:
            Log.error("Pic server not available:")
            return False;
        saveOK = response != None and response.status_code == 200
        if saveOK:
           member.picpath = pic
        return saveOK 
     
    '''scp example - for other use..    
    def savePicture2(self, member):
        saved = Registration.SAVEPIC
        data = member.lastName + "-" + member.primKeyString() + ".png"
        targetPath = SetUpTSVDB.PICPATH
        member.picpath = data
        try:
            with SCPClient(self.sshClient.get_transport()) as scp:
                place = targetPath + data
                Log.info("Saving picture :%s" % (data))
                scp.put(saved, place)
        except Exception:
            Log.exception("SCP failure")
            return False
        return True           
    '''
      
    def loadPicture(self, member):
        self.db.ensureConnection()
        targetPath = SetUpTSVDB.PICPATH
        pic = member.picpath
        host = SetUpTSVDB.HOST
        reqUrl = "http://%s:5001/%s/%s" % (host, targetPath, pic)
        Log.debug("Load url:%s", reqUrl)
        try:
            pic = requests.get(reqUrl).content
        except:
            Log.error("Picture Server not present")
            return None
        return pic
 
    def verifyRfid(self, rfidString, testId):
        # check if rfid  alreay exists ->False
        stmt = "SELECT id from " + self.dbSystem.MAINTABLE + " where uuid=" + rfidString
        res = self.db.select(stmt)
        if res is None:
            Log.warning("invalid rfid:%s", rfidString)
            return False            
        if len(res) > 0:
            if res[0][0] == testId:
                return True  # it belongs to him..
            Log.warning("User %d already has RFID key:%s", res[0][0], rfidString)
            return False
        return True
    
    
class Mitglied():
    FIELD_DEF = ('id', 'first_name', 'last_name', 'access', 'birth_date', 'picpath', 'uuid', 'flag')
    FIELD_SAVE_DEF = ('id', 'first_name', 'last_name', 'access', 'picpath', 'uuid', 'flag')

    def __init__(self, mid_int, fn, ln, access, birthdate, rfid_int):  # id, firstname, lastname, DOB, access1, access2
        # special handling
        self.picpath = None
        self.flag = 0
        self.abo = (None, 0)  # TsvDBCrator SECTION, count (str,int)
        self.currentAbo = (None, 0)  # TsvDBCrator SECTION, count (str,int)             
        self.update(mid_int, fn, ln, access, birthdate, rfid_int)
        
    def searchName(self):
        return self.lastName + " " + self.firstName

    def update(self, mid_int, fn, ln, access, birthdate, rfid_int):
        self.id = mid_int  # This is int
        self.firstName = fn
        self.lastName = ln
        self.access = access
        self.birthdate = birthdate  # This is a date
        self.rfid = rfid_int  # Must be int for faster search
    
    # TODO error; Wrong datatype if no saved and retireved.
    # Todo: no check if rfid is unique 
    def birthdayString(self):
        if self.birthdate is None:
            return ""
        return datetime.strftime(self.birthdate, '%d.%m.%Y')
    
    def asDBDate(self, stringDate):
        if len(stringDate)<6:
            return None
        return datetime.strptime(stringDate, '%d.%m.%Y')
    
    def primKeyString(self):
        return str(self.id)

    def rfidString(self):
        if self.rfid:
            return str(self.rfid)
        return None
    
    # data to save, no birthday        
    def dataSaveArray(self):
        row = []
        inner = (self.id, self.firstName, self.lastName, self.access, self.picpath, self.rfid, self.flag)  # birthdate is read only
        row.append(inner)
        return row


def getAppIcon():
    return QtGui.QIcon('./web/static/tsv_logo_100.png')


def handle_exception(exc_type, exc_value, exc_traceback):
    """ handle all exceptions """
    if WIN is not None:
        infoText = str(exc_value)
        detailText = "*".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        WIN.getErrorDialog("Unexpected error", infoText, detailText).show()
        Log.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


def parse():
    parser = argparse.ArgumentParser(description="Registration")
    parser.add_argument('-s', dest="searchCamera", action='store_true', help="Search for a camera")
    parser.add_argument('-c', dest="setCamera", type=int, default=0, help="set a camera index")
    parser.add_argument('-d', dest="debug", action='store_true', help="Debug logs")
    return parser.parse_args()    


def main(args):
    # todo speed up camera lookup. check log and promote: -c nbr
    if args.searchCamera:
        OpenCV3.getBestCameraIndex()
        sys.exit()
        
    try:
        global WIN
        global Log
        wd = OSTools().getLocalPath(__file__)
        OSTools.setMainWorkDir(wd)
        OSTools.setupRotatingLogger("TSVAccess", True)
        Log = DBTools.Log
        if args.debug:
            OSTools.setLogLevel("Debug")
        else:
            OSTools.setLogLevel("Info")
        argv = sys.argv
        app = QApplication(argv)
        app.setWindowIcon(getAppIcon())
        WIN = MainFrame(app, args.setCamera)  # keep python reference!
        # ONLY windoze, if ever: app.setStyleSheet(winStyle())
        # app.setStyle(QtWidgets.QStyleFactory.create("Fusion"));
        app.exec_()
        # logging.shutdown()
    except:
        Log.exception("Error in main:")
        # ex_type, ex_value, ex_traceback
        sys_tuple = sys.exc_info()
        QtWidgets.QMessageBox.critical(None, "Error!", str(sys_tuple[1]))


def winStyle():
    return """
        QWidget
        {
        color:black;
        background-color: lightgray;
        font-size: 15px;
        }
        
        QPushButton {
        color: white;
        font: bold 14px;
        min-width:20em;
        background-color: QLinearGradient( x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #88d, stop: 0.1 #99e, stop: 0.49 #77c, stop: 0.5 #66b, stop: 1 #77c);
        border-width: 1px;
        border-color: #339;
        border-style: solid;
        border-radius: 7;
        padding: 3px;
        padding-left: 5px;
        padding-right: 5px;
        min-width: 50px;
        max-width: 50px;
        min-height: 13px;
        max-height: 13px;
        }

          QLineEdit {
        padding: 1px;
        border-style: solid;
        border: 2px solid gray;
        border-radius: 8px;
        }
        
        QLabel {
        font-weight: bold;
        } """


if __name__ == '__main__':
    sys.excepthook = handle_exception
    sys.exit(main(parse()))

'''
QFile File("stylesheet.qss");
File.open(QFile::ReadOnly);
QString StyleSheet = QLatin1String(File.readAll());

qApp->setStyleSheet(StyleSheet);

  QApplication a(argc, argv);
  a.setStyleSheet(teststyle);
  MainWindow w;
  w.show();
'''

