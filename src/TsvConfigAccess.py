import sys, traceback, argparse
from DBTools import OSTools
import DBTools
from TsvDBCreator import SetUpTSVDB, Konfig, DBAccess, LOC_KRAFTRAUM,\
    ACTIVITY_GYM,ACTIVITY_KR,ACTIVITY_SAUNA, SECTION_FIT, SECTION_SAUNA, LOC_DOJO,LOC_MZR,LOC_NORD,LOC_SAUNA,LOC_SPIEGELSAAL

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QHBoxLayout, QComboBox, QMessageBox, QDialog, QFormLayout, QLineEdit, QListWidget, QListWidgetItem,QHeaderView
)
from PyQt6 import QtCore,QtGui


class MainFrame(QWidget):
    def __init__(self,qapp):
        super().__init__()
        self.__qapp = qapp
        self.initUI()
        self.initDB()
        self.loadConfigData()

    def initUI(self):
        self.setWindowTitle("Tsv Zugangskonfiguration")
        self.setGeometry(100, 100, 800, 400)
        
        layout = QVBoxLayout()
        
        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(9) 
        self.tableWidget.setHorizontalHeaderLabels([
            "ID","Ort", "Aktivität", "Abteilung", "Gruppen", "Aus-Zeit", "Tag", "Zeit von", "Zeit bis"
        ])
        header= self.tableWidget.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.tableWidget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tableWidget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tableWidget.itemSelectionChanged.connect(self.updateConfigButtons)
        self.tableWidget.verticalHeader().setVisible(False)
        layout.addWidget(self.tableWidget)
        
        btnLayout = QHBoxLayout()
        self.btnConfigAdd = QPushButton("Neu")
        self.btnConfigEdit = QPushButton("Bearbeiten")
        self.btnConfigDelete = QPushButton("Löschen")
        
        self.btnConfigEdit.setEnabled(False)
        self.btnConfigDelete.setEnabled(False)
        
        self.btnConfigAdd.clicked.connect(self.addConfigEntry)
        self.btnConfigEdit.clicked.connect(self.editConfigEntry)
        self.btnConfigDelete.clicked.connect(self.deleteConfigEntry)
        
        btnLayout.addWidget(self.btnConfigAdd)
        btnLayout.addWidget(self.btnConfigEdit)
        btnLayout.addWidget(self.btnConfigDelete)
        layout.addLayout(btnLayout)

        self.locationWidget = QTableWidget()
        self.locationWidget.setColumnCount(2)
        self.locationWidget.setHorizontalHeaderLabels(['Zugang',"Konfiguration"])
        self.locationWidget.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.locationWidget.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.locationWidget.itemSelectionChanged.connect(self.updateLocationButtons)
        self.locationWidget.verticalHeader().setVisible(False)        
        layout.addWidget(self.locationWidget)
        
        btnLayout = QHBoxLayout()
        self.btnLocationAdd = QPushButton("Neu")
        self.btnLocationEdit = QPushButton("Bearbeiten")
        self.btnLocationDelete = QPushButton("Löschen")
        
        self.btnLocationEdit.setEnabled(False)
        self.btnLocationDelete.setEnabled(False)
        
        self.btnLocationAdd.clicked.connect(self.addLocationEntry)
        self.btnLocationEdit.clicked.connect(self.editLocationEntry)
        self.btnLocationDelete.clicked.connect(self.deleteLocationEntry)
        btnLayout.addWidget(self.btnLocationAdd)
        btnLayout.addWidget(self.btnLocationEdit)
        btnLayout.addWidget(self.btnLocationDelete)
        layout.addLayout(btnLayout)
        
        layout.addLayout(btnLayout)
        #todo same for location: Delete, add and edit
        self.setLayout(layout)
    
    def initDB(self):
        self.model = Model()
        if self.model.connect():
            Log.info("Connected to db")
            self.model.readTables()
        else:
            Log.info("No database - exiting")
            exit(0)


    def loadConfigData(self):
        rows = self.model.configData
        self.tableWidget.setRowCount(len(rows))
        for rowIdx, row in enumerate(rows):
            for colIdx, cell in enumerate(row[0:]): 
                item = QTableWidgetItem(str(cell))
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)  # Make cells read-only
                self.tableWidget.setItem(rowIdx, colIdx, item)
    
        rows = self.model.locationData
        self.locationWidget.setRowCount(len(rows))
        for rowIdx, row in enumerate(rows):
            for colIdx, cell in enumerate(row[1:]):  # Skip config_id
                item = QTableWidgetItem(str(cell))
                item.setFlags(item.flags() & ~QtCore.Qt.ItemFlag.ItemIsEditable)  # Make cells read-only
                self.locationWidget.setItem(rowIdx, colIdx, item)
        
    
    
    def updateConfigButtons(self):
        hasSelection = self.tableWidget.currentRow() >= 0
        self.btnConfigEdit.setEnabled(hasSelection)
        self.btnConfigDelete.setEnabled(hasSelection)

    
    def updateLocationButtons(self):
        hasSelection = self.locationWidget.currentRow() >= 0
        self.btnLocationEdit.setEnabled(hasSelection)
        self.btnLocationDelete.setEnabled(hasSelection)
    

    def addConfigEntry(self):
        dialog = ConfigEntryDialog(self)
        if dialog.exec():
            #TODO save the stuff. 
            self.loadConfigData()
    
    def editConfigEntry(self):
        selected = self.tableWidget.currentRow()
        if selected >= 0:
            rowData = [self.tableWidget.item(selected, i).text() for i in range(8)]
            dialog = ConfigEntryDialog(self, rowData)
            if dialog.exec():
                #TODO save the stuff. 
                self.loadConfigData()
    
    def deleteConfigEntry(self):
        selected = self.tableWidget.currentRow()
        if selected >= 0:
            confirm = QMessageBox.question(self, "Confirm Delete", "Are you sure you want to delete this entry?", 
                                           QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if confirm == QMessageBox.StandardButton.Yes:
                stmt = f"DELETE FROM Konfig WHERE config_id=(SELECT config_id FROM Konfig LIMIT 1 OFFSET {selected})"
                self.model.db.select(stmt)
                self.loadConfigData()


    def addLocationEntry(self):
        print("Loc add")
        
    def editLocationEntry(self):
        print ("Loc edit")

    def deleteLocationEntry(self):
        print ("Loc del")


class ConfigEntryDialog(QDialog):
    def __init__(self, parent, rowData=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Entry" if rowData else "Add Entry")
        layout = QFormLayout()
        
        self.room = QComboBox()
        self.room.addItems(["Room A", "Room B", "Room C"])  # Example options
        layout.addRow("Room:", self.room)
        
        self.activity = QComboBox()
        self.activity.addItems(["Yoga", "Dance", "Meditation"])  # Example options
        layout.addRow("Activity:", self.activity)
        
        self.paySection = QComboBox()
        self.paySection.addItems(["Free", "Premium", "VIP"])  # Example options
        layout.addRow("Pay Section:", self.paySection)
        
        self.groups = QListWidget()
        self.groups.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for group in ["Group 1", "Group 2", "Group 3"]:  # Example groups
            item = QListWidgetItem(group)
            item.setCheckState(QtCore.Qt.CheckState.Unchecked)
            self.groups.addItem(item)
        layout.addRow("Groups:", self.groups)
        
        self.grace_time = QLineEdit()
        layout.addRow("Grace Time:", self.grace_time)
        
        self.weekday = QLineEdit()
        layout.addRow("Weekday:", self.weekday)
        
        self.from_time = QLineEdit()
        layout.addRow("From Time:", self.from_time)
        
        self.to_time = QLineEdit()
        layout.addRow("To Time:", self.to_time)
        
        if rowData:
            self.room.setCurrentText(rowData[0])
            self.activity.setCurrentText(rowData[1])
            self.paySection.setCurrentText(rowData[2])
            selected_groups = rowData[3].split(", ")
            for index in range(self.groups.count()):
                item = self.groups.item(index)
                if item.text() in selected_groups:
                    item.setCheckState(QtCore.Qt.CheckState.Checked)
            self.grace_time.setText(rowData[4])
            self.weekday.setText(rowData[5])
            self.from_time.setText(rowData[6])
            self.to_time.setText(rowData[7])
        
        btnLayout = QHBoxLayout()
        self.btnSave = QPushButton("Save")
        self.btnSave.clicked.connect(self.saveEntry)
        self.btnCancel = QPushButton("Cancel")
        self.btnCancel.clicked.connect(self.reject)
        
        btnLayout.addWidget(self.btnSave)
        btnLayout.addWidget(self.btnCancel)
        layout.addRow(btnLayout)
        
        self.setLayout(layout)
    
    def saveEntry(self):
        selected_groups = [self.groups.item(i).text() for i in range(self.groups.count()) if self.groups.item(i).checkState() == QtCore.Qt.CheckState.Checked]
        values = [
            self.room.currentText(), self.activity.currentText(), self.paySection.currentText(), ", ".join(selected_groups),
            self.grace_time.text(), self.weekday.text(), self.from_time.text(), self.to_time.text()
        ]
        self.accept()



'''
The model - keeps the database conection and holds all devices with their configs. 
Should be able to add new Konfigs and new devices with their relationships 
TODO provide list of all rooms, groups and activities
['KR','ÜL','GROUP','SKR0','SKR03','SKR05','SKR3','SKR03','SKR5','SKR05','SKR035'] ->  self.regmodel.accessTypes() which we dont use here
>>     def accessTypes(self):
        stmt = "select distinct access from %s" % (SetUpTSVDB.MAINTABLE)
        rows = self.db.select(stmt)
        return [access[0] for access in rows if len(access[0])>1]
'''
class Model():
    LOCATIONS=[LOC_KRAFTRAUM,LOC_DOJO,LOC_MZR,LOC_NORD,LOC_SAUNA,LOC_SPIEGELSAAL]
    ACTIVITIES=[ACTIVITY_GYM,ACTIVITY_KR,ACTIVITY_SAUNA]
    SECTIONS=[SECTION_FIT,SECTION_SAUNA]
    ACC_CODES=['KR','ÜL','GROUP','SKR0','SKR03','SKR05','SKR3','SKR03','SKR5','SKR05','SKR035'] #siehe "accesTypes" in comment
    def __init__(self):
        pass
        
    def connect(self):
        Log.info("Connect to db")
        self.dbSystem = DBAccess() 
        self.db = self.dbSystem.connectToDatabase()
        if self.dbSystem.isConnected(self.db):
            return True
        return False        

    def readTables(self):
        table1 = SetUpTSVDB.LOCATIONTABLE
        table2 = SetUpTSVDB.CONFIGTABLE
        fields=','.join(Konfig.FIELD_DEF)
        #stmt = "select %s from %s conf join %s loc where loc.host_name='%s' and conf.config_id =loc.config order by(conf.config_id)"%(fields,table2,table1,client)
        #client is the hw device to which the konfig is connected! 
        #tsvaccessx->Konfig?
        
        stmt = 'select * from '+ table1
        #host + list of configs:
        #select host_name, GROUP_CONCAT(config order by config) as configs from Location group by host_name;
        #this gives you the prim keys as well (if needed):
        #select host_name, GROUP_CONCAT(config order by config) as configs,GROUP_CONCAT(id order by id) as pkeys from Location group by host_name;
        self.locationData = self.db.select(stmt)
        #[(1, 'tsvaccess1', 0), (2, 'tsvaccess1', 1), (3, 'tsvaccess1', 2),.. id name, konfigID
        print(self.locationData)
        stmt = 'select * from '+ table2
        self.configData = self.db.select(stmt)
        #[(0, 'Kraftraum', 'Kraftraum', 'Fit & Fun', "['KR','ÜL']", 900, None, None, None),.. id,room,activity,paysection,groups gracetime,weekday, from, to
        #room=Ort, activity=Art(KR,Group,Sauna),paysection=Abteilung)
        print(self.configData)
        
def parse():
    parser = argparse.ArgumentParser(description="AccessConfig")
    parser.add_argument('-d', dest="debug", action='store_true', help="Debug logs")
    return parser.parse_args()

def getAppIcon():
    return QtGui.QIcon('./web/static/TsvConfig.png') 

def handle_exception(exc_type, exc_value, exc_traceback):
    """ handle all exceptions """
    if WIN is not None:
        infoText = str(exc_value)
        detailText = "*".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        WIN.getErrorDialog("Unexpected error", infoText, detailText).show()
        Log.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


def main(args):
    if OSTools.checkIfInstanceRunning("TsvConfigAccess"):
        print("App already running")
        sys.exit()
    try:
        global Log
        global WIN
        wd = OSTools.getLocalPath(__file__)
        OSTools.setMainWorkDir(wd)
        OSTools.setupRotatingLogger("TSVCFG", args.debug)
        Log = DBTools.Log
        if args.debug:
            OSTools.setLogLevel("Debug")
        else:
            OSTools.setLogLevel("Info")
        Log.info("--- Start TsvConfigAccess ---")
        argv = sys.argv
        app = QApplication(argv)
        app.setWindowIcon(getAppIcon())
        WIN = MainFrame(app)
        WIN.show() 
        app.exec()
    except:
        with open('/tmp/error.log', 'a') as f:
            f.write(traceback.format_exc())
        traceback.print_exc(file=sys.stdout)
        Log.exception("Error in main:")
        # ex_type, ex_value, ex_traceback
        sys_tuple = sys.exc_info()
        QMessageBox.critical(None, "Error!", str(sys_tuple[1]))


if __name__ == "__main__":
    sys.excepthook = handle_exception
    sys.exit(main(parse()))
