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

# Importing OpenCV package
import cv2, sys, traceback, time
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import pyqtSignal
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QRegExpValidator
from DBTools import OSTools
from TsvDBCreator import SetUpTSVDB
import DBTools
from datetime import datetime

class OpenCV3():

    def __init__(self):
        self._cap = cv2.VideoCapture()
    
    def getCapture(self):
        return self._cap
    
    def setColor(self, numpyArray):
        cv2.cvtColor(numpyArray, cv2.COLOR_BGR2RGB, numpyArray)  # @UndefinedVariable
        
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


OPENCV = OpenCV3()


class CVImage(QtGui.QImage):

    def __init__(self, numpyArray):
        height, width, bytesPerComponent = numpyArray.shape
        dst = numpyArray
        bytesPerLine = bytesPerComponent * width
            
        OPENCV.setColor(dst)
        super(CVImage, self).__init__(dst.data, width, height, bytesPerLine, QtGui.QImage.Format_RGB888)


class VideoWidget(QtWidgets.QFrame):
    """ A class for rendering video coming from OpenCV """
    trigger = pyqtSignal(float, float, float)
    
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
        else: 
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
    
    def updateUI(self, frameNumber, framecount, timeinfo):
        self.trigger.emit(frameNumber, framecount, timeinfo)

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
        #palette = qApp.palette()
        #palette.setBrush(QPalette.Base, palette.button())
        #self.lineEdit().setPalette(palette)

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

    def eventFilter(self, object, event):

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

    #mark items in data or textarray as selected
    def selectData(self,textArray):
        #TODO
        pass

# #Main App Window. 
class MainFrame(QtWidgets.QMainWindow):
    
    def __init__(self, qapp, aPath=None):
        self._isStarted = False
        self.__qapp = qapp
        self.model = Registration()
        self.cameraThread = None
        self.qtQueueRunning = False
        self.capturing = False
        self.photoTaken=False
        
        super(MainFrame, self).__init__()
        self.setWindowIcon(getAppIcon())
        self._widgets = self.initUI()
        self.centerWindow()
        # self._widgets.enableUserActions(False)
        self.setWindowTitle("Registrierung für Fit'n Fun Mitglieder")
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
        
        self.ui_VideoFrame = VideoWidget(self)
        self.ui_VideoFrame.setToolTip("Warten bis ein grüner Rahmen angezeigt wird, dann 'Photo' Knopf drücken") 
        
        self.ui_PhotoButton = QtWidgets.QPushButton()
        self.updatePhotoButton()
        self.ui_PhotoButton.clicked.connect(self._onScreenShot)
        self.ui_PhotoButton.setToolTip("Wechsel zwischen Video und Photo machen")
        
        self.ui_SearchLabel = QtWidgets.QLabel(self)
        self.ui_SearchLabel.setText("Suche:")
        
        #self.ui_SearchEdit = QtWidgets.QLineEdit(self)
        self.ui_SearchEdit = QtWidgets.QComboBox(self)
        self.ui_SearchEdit.setEditable(True) #Is that right??
        #self.ui_SearchEdit.currentIndexChanged.connect(self._onSearchChanged)
        self.ui_SearchEdit.setInsertPolicy(QtWidgets.QComboBox.NoInsert);
        self.ui_SearchEdit.completer().setCompletionMode(QtWidgets.QCompleter.PopupCompletion);
        self.ui_SearchEdit.activated.connect(self._onSearchChanged)
        self.ui_SearchEdit.setToolTip("Nachnamen eingeben, um eine Person zu suchen")
        
        # self.ui_SearchEdit.setSizePolicy(QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Preferred)
        
        self.ui_IDLabel = QtWidgets.QLabel(self)
        self.ui_IDLabel.setText("Nummer:")
        self.ui_IDEdit = QtWidgets.QLineEdit(self)
        self.ui_IDEdit.setValidator(QtGui.QIntValidator(1,100000,self))
        self.ui_IDEdit.setValidator(QRegExpValidator(QRegExp('^([1-9][0-9]*\.?|0\.)[0-9]+$'), self))
        self.ui_IDEdit.setToolTip("Die Conplan <Adressnummer> ist hier einzutragen")

        self.ui_FirstNameLabel = QtWidgets.QLabel(self)
        self.ui_FirstNameLabel.setText("Vorname:")
        self.ui_FirstNameEdit = QtWidgets.QLineEdit(self)
        
        self.ui_LastNameLabel = QtWidgets.QLabel(self)
        self.ui_LastNameLabel.setText("Nachname:")
        self.ui_LastNameEdit = QtWidgets.QLineEdit(self)

        self.ui_BirthLabel = QtWidgets.QLineEdit(self)
        self.ui_BirthLabel.setText("")
        self.ui_BirthLabel.setReadOnly(True);
        self.ui_BirthLabel.setToolTip("Geburtstag (nicht veränderbar)")

        self.ui_RFIDLabel = QtWidgets.QLabel(self)
        self.ui_RFIDLabel.setText("RFID Nummer")
        self.ui_RFID = QtWidgets.QLineEdit(self)
        self.ui_RFID.setToolTip("RFID mit Kartenleser einchecken - Erst draufclicken -dann scannen!")
        self.ui_RFID.textEdited.connect(self._onRFIDRead)

        self.ui_AccessLabel = QtWidgets.QLabel(self)
        self.ui_AccessLabel.setText("Merkmale:")
        self.ui_AccessLabel.setToolTip("Hier kann der Zugangscode (Multi3) angepasst werden - aktuell nur einer")
        
        self.ui_AccessCombo = QtWidgets.QComboBox(self)
        #self.ui_AccessCombo = CheckableComboBox(self)
        themes = SetUpTSVDB.ACCESSLIST
        for item in themes:
            self.ui_AccessCombo.addItem(item)
        self.ui_AccessCombo.setCurrentText("")  # self.model.iconSet
        self.ui_AccessCombo.currentTextChanged.connect(self._onAccessChanged)
        #self.ui_AccessCombo.setToolTip("Angabe der Zugangsbereiche (Mehrfachwahl möglich)")
        self.ui_AccessCombo.setToolTip("Angabe des Zugangsbereichs")

        self.ui_CreateButton = QtWidgets.QPushButton()
        self.ui_CreateButton.setText("Speichern")
        self.ui_CreateButton.clicked.connect(self._onSaveMember)
        self.ui_CreateButton.setToolTip("In Datenbank speichern und Zugang erlauben")

        self.ui_ExitButton = QtWidgets.QPushButton()
        self.ui_ExitButton.setText("Neu")
        self.ui_ExitButton.clicked.connect(self._onNewClicked)
        self.ui_ExitButton.setToolTip("Ein weiters Mitglied einchecken")
        
        box = self.makeGridLayout()
        
        # Without central widget it won't work
        wid = QtWidgets.QWidget(self)
        self.setCentralWidget(wid)        
        wid.setLayout(box)
        self.adjustSize()

    # simple toggle
    def updatePhotoButton(self):
        if self.capturing:
            self.ui_PhotoButton.setText("Photo")
        else: 
            self.ui_PhotoButton.setText("Web Cam")            

    # fill the search combo
    def fillSearchCombo(self,memberList):
        self.ui_SearchEdit.clear()
        self.ui_SearchEdit.addItem("",None)
        for member in memberList:
            entry= member.searchName()
            self.ui_SearchEdit.addItem(entry,member)
            


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
        gridLayout.addWidget(self.ui_BirthLabel,11,4,1,2)
        
        line = QtWidgets.QFrame();
        line.setFrameShape(QtWidgets.QFrame.HLine);
        line.setFrameShadow(QtWidgets.QFrame.Sunken);
        
        gridLayout.addWidget(line, 12, 1, 1, -1)
        
        gridLayout.addWidget(self.ui_ExitButton, 13, 1, 1, 1)
        gridLayout.addWidget(self.ui_CreateButton, 13, 5, 1, 1)
        
        gridLayout.setRowStretch(1, 1)

        return gridLayout

    def setEntryFields(self,mbr): #TODO
        self.ui_IDEdit.setText(mbr.primKeyString())
        self.ui_FirstNameEdit.setText(mbr.firstName)
        self.ui_LastNameEdit.setText(mbr.lastName)
        self.ui_AccessCombo.setCurrentText(mbr.access)
        self.ui_BirthLabel.setText(mbr.birthdayString())
        self.ui_RFID.setText(mbr.rfidString())
        #self.ui_AccessCombo.do-sth    
           
 
    # The widget callbacks
    @QtCore.pyqtSlot(str)
    #Zugangs kontrolle - not nicht designed
    def _onAccessChanged(self, text):
        Log.info("Accessmode:%s", text)
        #do we need this event?

    @QtCore.pyqtSlot()
    def _onScreenShot(self):
        if self.capturing:
            self.capturing = False
            if self.model.takeScreenshot("/tmp/tsv.screenshot.png"):
                self.photoTaken=True
                self.cameraThread.showFrame(self.model.currentFrame)
            else:
                self.getMessageDialog("Kein Photo gespeichert!", "Es konnte kein Gesicht erkannt werden \nBitte nochmals probieren").show()
            self.updatePhotoButton()
        else:
            self._initCapture()

    @QtCore.pyqtSlot(int)
    def _onSearchChanged(self, idx):
        mbr = self.ui_SearchEdit.itemData(idx)
        if mbr:
            self.setEntryFields(mbr)

    @QtCore.pyqtSlot()
    def _onNewClicked(self):
        self.ui_SearchEdit.setCurrentIndex(-1)
        self._clearFields()        
    
    @QtCore.pyqtSlot(str)            
    def _onRFIDRead(self,rfid):
        #this we need to check
        if len(rfid)<10:
            return
        print("Read slot %s"%(rfid))
        if not rfid:
            return;
        
        mbr=self.ui_SearchEdit.currentData()
        testId=None
        if mbr:
            testId=mbr.id
        if not self.model.verifyRfid(rfid,testId):
            d= self.getErrorDialog("** RFID **", "Ungültige RFID, bitte einen anderen Token benutzen", "In der Datenbank existiert bereits eine solche RFID Nummer und kann nicht nochmal vergeben werden")
            d.show()

    #persist to database (Speichern)
    #Store & contrl picture only if not in mbr
    def _onSaveMember(self):
        mbr=self.ui_SearchEdit.currentData()
        idstr = self.ui_IDEdit.text()
        firstName= self.ui_FirstNameEdit.text()
        lastName= self.ui_LastNameEdit.text()
        access = self.ui_AccessCombo.currentText()
        birthdate= self.ui_BirthLabel.text()
        rfid = self.ui_RFID.text()
        photoSaved= mbr is not None and mbr.picpath is not None
        
        msg=""
        if not idstr:
            msg="Mitgliedsnr ? \n"
        if not firstName:
            msg = msg+"Vorname ? \n"
        if not lastName:
            msg = msg+"Nachname ? \n"
        if not access:
            msg = msg+"Zugangscode ? \n"
        if not (self.photoTaken or photoSaved):
            msg = msg+"Photo ? \n"
        if not rfid:
            msg= msg+"RFID Code ? \n"
           
        if len(msg)>0: 
            self.getErrorDialog("Eingabefehler","Bitte alle Felder ausfüllen",msg).show()
            Log.warning("Data error:%s",msg)
            return

        mid= int(idstr)
        rfid_int= int(rfid)
        #we should update in the correct form
        if mbr is not None:
            bd = mbr.asDBDate(birthdate)
            mbr.update(mid,firstName,lastName,access,bd,rfid_int)
            self.ui_SearchEdit.setEditText(mbr.searchName())
        else:
            #create new member, update search box
            mbr=Mitglied(mid,firstName,lastName,access,None,rfid_int)
            entry= mbr.searchName()
            self.ui_SearchEdit.addItem(entry,mbr)
        #need a try catch.
        if self.photoTaken:
            res= self.model.savePicture(mbr)#scps the pic to remote and adds uri to db...
            if not res:
                self.getErrorDialog("Verbindungsfehler","Bild konnte nicht gespeichert werden","Das muss gemeldet werden").show()
   
        self.model.updateMember(mbr)
        #self.model.printMemberCard(mbr)
        self.photoTaken=False
        
        self._clearFields()
        
    def _clearFields(self):
        self.ui_SearchEdit.clearEditText()
        self.ui_IDEdit.clear()
        self.ui_FirstNameEdit.clear()
        self.ui_LastNameEdit.clear()
        self.ui_AccessCombo.clearEditText()       
        self.ui_BirthLabel.clear()
        self.ui_RFID.clear()
        self.model.currentFrame=None
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

    def getErrorDialog(self, text, infoText, detailedText):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setIcon(QtWidgets.QMessageBox.Warning)
        dlg.setWindowModality(QtCore.Qt.WindowModal)
        dlg.setWindowTitle("Fehler")
        dlg.setText(text)
        dlg.setInformativeText(infoText)
        dlg.setDetailedText(detailedText)
        dlg.setStandardButtons(QtWidgets.QMessageBox.Ok)
        spacer = QtWidgets.QSpacerItem(300,50, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum)
        layout = dlg.layout()
        layout.addItem(spacer, layout.rowCount(), 0, 1, layout.columnCount())
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
    
    def _displayFrame(self):
        self.ui_VideoFrame.showFrame(self.cameraThread.result)
    
    @QtCore.pyqtSlot(str)
    def _showCameraError(self,text):
        dlg=self.getErrorDialog("Kamerafehler", text, "Ein Kamerafehler ist aufgetreten. Häufigste Ursache ist, das sie nicht gefunden werden kann.")
        dlg.show()
    
    @QtCore.pyqtSlot(str)
    def _setRFID(self,key):
        print("RFID:",key)
        self.ui_RFID.setText(key)
    
    def __queueStarted(self, state):
        if self.qtQueueRunning:
            return
        self.qtQueueRunning = True
        self.ui_VideoFrame.showFrame(None)
        
        self.cameraThread = CameraThread(self.model.activateCamera)
        self.cameraThread.signal.connect(self._displayFrame)
        #self.cameraThread.error.connect(self._showCameraError)
        if self._initModel():
            self._initCapture()
        
    
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
        res = self.model.connect()
        QApplication.restoreOverrideCursor()
        if not res:
            dlg= self.getErrorDialog("Datenbank Fehler ", "Datenbank nicht gefunden", "Es besteht keine Verbindung zur Datenbank. Muss gemeldet werden!")
            dlg.buttonClicked.connect(self._onErrorDialogClicked)
            dlg.show()
        else:
            memberList = self.model.getMembers()
            self.fillSearchCombo(memberList)
            # self.ui_SearchEdit.add alot of data
            
        return res

    def _onErrorDialogClicked(self,_):
        self.close()

    def closeEvent(self,event):
        self.model.stopCamera()
        self.cameraThread.quit()
        self.cameraThread.wait()
        try:
            super(MainFrame, self).closeEvent(event)
        except:
            Log.exception("Error Exit")        
'''
class RFIDThread(QtCore.QThread):
    signal = pyqtSignal(str)
    
    def __init__(self, func):
        QtCore.QThread.__init__(self)
        self.func = func
    
    def run(self):
        self.func(self)
        
    def dispatch(self,key):
        self.signal.emit(key)        
'''

class CameraThread(QtCore.QThread):
    signal = pyqtSignal()
    #error= pyqtSignal(str)
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
def headRec(): 
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

    def __init__(self):
        #self.accesscodes = []
        self.currentFrame = None
        self.borders = []
        self.cameraOn = False
        self.cameraStatus = None
        

    def connect(self):
        self.dbSystem = SetUpTSVDB(SetUpTSVDB.DATABASE)
        self.db = self.dbSystem.db
        return self.dbSystem.isConnected()
    
    # reads the list and passes it to the caller...
    def getMembers(self):
        fields = ','.join(Mitglied.FIELD_DEF)#FIELD_DEF=('id','first_name','last_name','access','birth_date,picpath,uuid') 
        #stmt = "SELECT id,first_name,last_name from " + self.dbSystem.MAINTABLE
        stmt = "SELECT "+fields+" from " + self.dbSystem.MAINTABLE
        col = []
        # currently: [(1234, 'Merti', 'quanz'), (1236, 'Cora', 'Schnell')]
        res = self.db.select(stmt)
        for titem in res:
            # id(int) (str) (str) (str) date! int
            m = Mitglied(titem[0], titem[1], titem[2],titem[3],titem[4],titem[6])
            m.picpath=titem[5]
            col.append(m)
        return col
    
    def updateMember(self,mbr):
        table=self.dbSystem.MAINTABLE
        fields=Mitglied.FIELD_SAVE_DEF
        data=mbr.dataSaveArray()
        self.db.insertMany(table,fields,data)
    
    #we need some sane values.Try with at least 300 pix in size.
    def activateCamera(self, cameraThread):
        camera_id = cv2.CAP_V4L2
        cap = cv2.VideoCapture(camera_id)
        if cap is None or not cap.isOpened():
            Log.warning("Camera not found!")
            self.cameraStatus="Keine Kamera gefunden"
            return
            
        CTHRES=300 #find out... 
        self.currentFrame = None
        
        # Loading the required haar-cascade xml classifier file
        haar_cascade = cv2.CascadeClassifier('/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml') 
        # haar_cascade = cv2.CascadeClassifier('./data/upper_body.xml')
        # Reading the image
        print("Cam on")
        self.cameraOn = True
        # emit signal?
        while self.cameraOn:
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
                    left = x-offsetX
                    top= y-offsetY
                    right= x+w+offsetX
                    bottom=y+h+offsetY
                    cv2.rectangle(frame, (left,top),(right,bottom), (0, 255, 0), 2)
                    #cv2.rectangle(frame, (x - offsetX, y - offsetY), (x + w + offsetX, y + h + offsetY), (0, 255, 0), 2)
                    #self.borders = [x - offsetX + 2, y - offsetY + 2, w + 2 * offsetX - 4, h + 2 * offsetY - 4]
                    
                    px=max(0,left+2)
                    py=max(0,top+2)
                    dw=right-px -2
                    dh=bottom-py -2;
                    if dw >CTHRES and dh>CTHRES:
                        self.borders=[px,py,dw,dh]
                    else:
                        Log.debug("Invalid frame size: %d / %d -> %d/%d",px,py,dw,dh)
                       
                
                if self.cameraOn: 
                    self.currentFrame = frame
                    cameraThread.showFrame(frame)
                
        cap.release()
    
    def takeScreenshot(self, path):
        self.cameraOn = False
        if self.currentFrame is None or len(self.borders)==0:
            Log.info("Screenshot failed")
            return False
        x = self.borders[0]
        y = self.borders[1]
        w = self.borders[2]
        h = self.borders[3]
        Log.info("Crop photo dim: %d/%d > %d/%d",x,y,w,h)
        cropped = self.currentFrame[y:y + h, x:x + w].copy()
        cv2.imwrite(path, cv2.cvtColor(cropped, cv2.COLOR_RGB2BGR))
        self.currentFrame = cv2.cvtColor(self.currentFrame[y:y + h, x:x + w], cv2.COLOR_RGB2BGR)
        return True   

    def stopCamera(self):
        self.cameraOn=False
        
    #dont- save pic with member name on remote device via scp or smb.     
    def printMemberCard(self,member):
        #generate OCR for now    
        #get both images & convert: left to right (else -append)
        #convert +append image_1.png image_2.png -resize x500 new_image_conbined.png
        data = str(member.id)+","+member.searchName()
        cmd1=["/usr/bin/qrencode","-o", "/tmp/qr.png", "-s", "6",data]
        res=DBTools.runExternal(cmd1)
        #print(res)
        
        #possible density stuff. We need to ensure that the saved size is independent of the camera!
        #montage card[1-4]*.png -tile 2x2+140+140 -geometry 382x240+65+52 -density 100 cards.pdf
        cmd2=["/usr/bin/convert","+append","/tmp/tsv.screenshot.png","/tmp/qr.png","-resize","x400","/tmp/member.png" ]
        res=DBTools.runExternal(cmd2)
        #print(res)
        
    def savePicture(self,member):
        saved= "/tmp/tsv.screenshot.png"
        data = member.lastName+"-"+member.primKeyString()+".png"
        targetPath = SetUpTSVDB.PICPATH
        member.picpath=data
        cmd1=["scp",saved,targetPath+data]
        res=DBTools.runExternal(cmd1)
        if len(res[0])>0:
            Log.info("Save Pic result:%s",res[0])
        if len(res[1])>0:
            Log.warning("Save Pic result:%s",res[1]) 
            return False
        return True           
        
        
        #save current frame and remove that imwrite in takeScreenshot
        #scp saved to remote location
        '''
        another way for getting the pic:
        img = CVImage(frame.copy()).scaled(int(self.cvWidget.imageRatio * self.iconSize), self.iconSize)
            pix = QtGui.QPixmap.fromImage(img)
        #conveert to base64 String
        def toBase64(self,pix):
            data = QtCore.QByteArray() 
            buf = QtCore.QBuffer(data)
            pix.save(buf, 'JPG')
            #breaks xml test=data.toBase64()
            t1=data.toBase64()
            t2= str(t1,'ascii')
            return t2    
        #back to img
        def fromBase64(self,pixstr):
            if pixstr is None:
                return None
            t1=bytearray(pixstr,"ascii")
            #data = QtCore.QByteArray.fromBase64(pixstr,QtCore.QByteArray.Base64Encoding)
            data = QtCore.QByteArray.fromBase64(t1)
            pix=QtGui.QPixmap()
            pix.loadFromData(data)
            return pix        
        
        generate and install ssh key or use pwd..
        import subprocess
        subprocess.run(["scp", FILE, "USER@SERVER:PATH"])
        '''
        #store Name(not path) into db
        return True
        
    def verifyRfid(self,rfidString,testId):
        #check if rfid  alreay exists ->False
        stmt="SELECT id from "+self.dbSystem.MAINTABLE+" where uuid="+rfidString
        res = self.db.select(stmt)
        if len(res)>0:
            if res[0][0]==testId:
                return True # it belongs to him..
            Log.warning("User %d already has RFID key:%s",res[0][0],rfidString)
            return False
        return True
            
    
    
class Mitglied():
    FIELD_DEF=('id','first_name','last_name','access','birth_date','picpath','uuid')
    FIELD_SAVE_DEF=('id','first_name','last_name','access','picpath','uuid')
    def __init__(self, mid_int, fn, ln,access,birthdate,rfid_int):  # id, firstname, lastname, DOB, access1, access2
        self.picpath=None #special handling
        self.update(mid_int, fn, ln,access,birthdate,rfid_int)
        
    def searchName(self):
        return self.lastName + " " + self.firstName

    def update(self,mid_int, fn, ln,access,birthdate,rfid_int):
        self.id = mid_int #This is int
        self.firstName = fn
        self.lastName = ln
        self.access=access
        self.birthdate=birthdate #This is a date
        self.rfid=rfid_int #Must be int for faster search
        
    
    
    #TODO error; Wrong datatype if no saved and retireved.
    #Todo: no check if rfid is unique 
    def birthdayString(self):
        return datetime.strftime(self.birthdate, '%d.%m.%Y')
    
    def asDBDate(self,stringDate):
        return datetime.strptime(stringDate, '%d.%m.%Y')
    
    def primKeyString(self):
        return str(self.id)

    def rfidString(self):
        if self.rfid:
            return str(self.rfid)
        return None
    
    #data to save, no birthday        
    def dataSaveArray(self):
        row=[]
        inner=(self.id,self.firstName,self.lastName,self.access,self.picpath,self.rfid) #birthdate is read only
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


def main():
    try:
        global WIN
        global Log
        wd = OSTools().getLocalPath(__file__)
        OSTools.setMainWorkDir(wd)
        Log = DBTools.Log
        OSTools.setupRotatingLogger("TSVAccess", True)
        OSTools.setLogLevel("Info")
        argv = sys.argv
        app = QApplication(argv)
        app.setWindowIcon(getAppIcon())
        WIN = MainFrame(app)  # keep python reference!
        app.exec_()
        # logging.shutdown()
    except:
        Log.exception("Error in main:")
        # ex_type, ex_value, ex_traceback
        sys_tuple = sys.exc_info()
        QtWidgets.QMessageBox.critical(None, "Error!", str(sys_tuple[1]))


if __name__ == '__main__':
    sys.excepthook = handle_exception
    sys.exit(main())
