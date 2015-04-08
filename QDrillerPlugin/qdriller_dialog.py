# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QDrillerDialog
                                 A QGIS plugin
 Drillhole visualisation tools
                             -------------------
        begin                : 2015-03-30
        git sha              : $Format:%H$
        copyright            : (C) 2015 by Alex Brown
        email                : email
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET


from PyQt4 import QtGui, uic, QtCore
from PyQt4.QtGui import * 

import qgis.core
import qgis.gui

#import module with all the technical backend code
import QDriller_Utilities as QDUtils

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qdriller_dialog_base.ui'))


class QDrillerDialog(QtGui.QMainWindow, FORM_CLASS):

    
    
    datastore = None
    def __init__(self, parent=None):
        """Constructor."""
        super(QDrillerDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        ##Initialise data Store Class###
        QDrillerDialog.datastore = DataStore()
       
        ###set up button actions###
        self.btnSectionWindow.clicked.connect(self.openSectionView)
        #Project Setup Buttons
        
        self.btnAddLog.clicked.connect(self.addtoLoglist)
        self.btnColbrowse.clicked.connect(lambda:self.showFileBrowser("collarfile"))
        self.btnCreatePrj.clicked.connect(self.createProject)
        self.btnDHlogbrowse.clicked.connect(lambda:self.showFileBrowser("logfile"))
        self.btnLoadPrj.clicked.connect(self.loadProject)
        self.btnPrjDirbrowse.clicked.connect(lambda:self.showFileBrowser("projdir"))
        self.btnRemlog.clicked.connect(self.removefromLoglist)
        self.btnSavePrj.clicked.connect(self.saveProject)
        self.btnSurvbrowse.clicked.connect(lambda:self.showFileBrowser("surveyfile"))
        self.btnCRS.clicked.connect(self.fetchCRS)
        
        
        #Plan View Objects Buttons
        self.btnCreateCol.clicked.connect(lambda: QDrillerDialog.datastore.createCollarPoints())
        self.btnCreateTrace.clicked.connect(lambda: QDrillerDialog.datastore.createPlanTrace())
        self.btnCreateLog.clicked.connect(lambda: QDrillerDialog.datastore.createPlanLog())
        self.cmbLogSelector.currentIndexChanged.connect(lambda:self.setVariable("logtarget", self.cmbLogSelector.currentText()))
        self.btnDelLayer.clicked.connect(self.deleteLayerFromList)
        
        ###LineEdit Signals###
        self.ledCol.textChanged.connect(lambda: self.setVariable("collarfile", self.ledCol.text()))
        self.ledProjDir.textChanged.connect(lambda: self.setVariable("projdir", self.ledProjDir.text()))
        self.ledSur.textChanged.connect(lambda: self.setVariable("surveyfile", self.ledSur.text()))
        self.ledProjName.textChanged.connect(lambda: self.setVariable("projectname", self.ledProjName.text()))
        
        ###Checkbox Signals###
        self.chkTrace2can.toggled.connect(lambda: self.setVariable("trace2can", self.chkTrace2can.isChecked()))
        self.chkColl2can.toggled.connect(lambda: self.setVariable("coll2can", self.chkColl2can.isChecked()))
        self.chkLog2can.toggled.connect(lambda: self.setVariable("log2can", self.chkLog2can.isChecked()))
        #self.chkEohlab.toggled.connect()
        #self.chkDHTick.toggled.connect()
        
        ##Other Signals###
        QDrillerDialog.datastore.fileCreated.connect(self.addtoLayerList)
        QDrillerDialog.datastore.projectLoaded.connect(self.onProjectLoad)
        
    #functions for running the gui
        
    def showFileBrowser(self,target):
    #call up a file browser with filter for extension. 
    #target is the Gui element to set text to
        if QDrillerDialog.datastore.projectdir is not None:
            rootdir = QDrillerDialog.datastore.projectdir
        else:
            rootdir = "/"
       
        if target == "collarfile":
            self.ledCol.setText(QtGui.QFileDialog.getOpenFileName(self, 'Select Collar File', rootdir, "*.csv"))
        elif target == "surveyfile":
            self.ledSur.setText(QtGui.QFileDialog.getOpenFileName(self, 'Select Survey File', rootdir, "*.csv"))
        elif target == "projdir":
            self.ledProjDir.setText(QtGui.QFileDialog.getExistingDirectory(self, 'Select Project Directory', rootdir,QtGui.QFileDialog.ShowDirsOnly))
        elif target == "logfile":
            self.ledDHlogs.setText(QtGui.QFileDialog.getOpenFileName(self, 'Select Downhole Log File', rootdir, "*.csv"))
            
    def showSaveFile(self):
        if QDrillerDialog.datastore.projectdir is not None:
            rootdir = QDrillerDialog.datastore.projectdir
        else:
            rootdir = "/"
            
        QDrillerDialog.datastore.savefilepath = (QtGui.QFileDialog.getSaveFileName(self, 'Save Project Definition', rootdir, "*.qdsv"))
        
    def setVariable(self, target, value):
        
        if target == "collarfile":
            QDrillerDialog.datastore.collarfile = value
        elif target == "surveyfile":
            QDrillerDialog.datastore.surveyfile = value
        elif target == "projdir":
            QDrillerDialog.datastore.projectdir = value
        elif target == "projectname":
            QDrillerDialog.datastore.projectname = value
        elif target == "trace2can":
            QDrillerDialog.datastore.trace2can = value
        elif target == "log2can":
            QDrillerDialog.datastore.log2can = value
        elif target == "coll2can":
            QDrillerDialog.datastore.coll2can = value
        elif target == "logtarget":
            QDrillerDialog.datastore.logtarget = value
            
        
    def addtoLoglist(self):
        self.lstDHlogs.addItem(self.ledDHlogs.text())
        self.ledDHlogs.clear()
        
        templist = []    
        for i in xrange(self.lstDHlogs.count()):
            templist.append(self.lstDHlogs.item(i).text())
            
        QDrillerDialog.datastore.logfiles = templist
        self.refreshGui()
        
    def removefromLoglist(self):
        for item in self.lstDHlogs.selectedItems():
            trash = self.lstDHlogs.takeItem(self.lstDHlogs.row(item))
            trash = None
            
        templist = []    
        for i in xrange(self.lstDHlogs.count()):
            templist.append(self.lstDHlogs.item(i).text())
            
        QDrillerDialog.datastore.logfiles = templist
        self.refreshGui()
        
    
    def addtoLayerList(self):
        self.lstExistingLayers.clear()
        for keys in QDrillerDialog.datastore.existingLayersDict:
            newitem = self.lstExistingLayers.addItem(keys)
            
    def deleteLayerFromList(self):
        # a function to delete log shapefile from disk, remove from List widget 
        # and remove from the internal existing layers list
        
        #create list of layers to delete, and remove them from the widget
        delList = []
        for item in self.lstExistingLayers.selectedItems():
            delList.append(item.text())
            trash = self.lstExistingLayers.takeItem(self.lstExistingLayers.row(item))
            trash = None
        #close layers if they are open
        for names in delList:
            mapregList = qgis.core.QgsMapLayerRegistry.instance().mapLayersByName(names)
            for lyr in mapregList:
                qgis.core.QgsMapLayerRegistry.instance().removeMapLayer(lyr.id())
                
        #delete shapefiles
        for names in delList:
            path = QDrillerDialog.datastore.existingLayersDict[names]
            qgis.core.QgsVectorFileWriter.deleteShapeFile(path)
            #remove from existing layer dictionary
            del QDrillerDialog.datastore.existingLayersDict[names]
        #regenerate the list
        self.lstExistingLayers.clear()
        for keys in QDrillerDialog.datastore.existingLayersDict:
            newitem = self.lstExistingLayers.addItem(keys)
        
    def refreshGui(self):
        self.cmbLogSelector.clear()
        self.cmbLogSelector.addItems(QDrillerDialog.datastore.logfiles)
        
    def createProject(self):
        
        print "project created"
         
        self.showSaveFile()
        QDrillerDialog.datastore.saveProjectData()
        QDrillerDialog.datastore.calcDrillholes()
        self.gpbxPlanview.setEnabled(True)
        # also set up enabling the save button and the sectionview 
        
    def saveProject(self):
        QDrillerDialog.datastore.saveProjectData()
        
    def loadProject(self):
        QDrillerDialog.datastore.savefilepath = (QtGui.QFileDialog.getOpenFileName(self, 'Open from Project Definition', "/", "*.qdsv"))
        QDrillerDialog.datastore.loadProjectData()
        
    def onProjectLoad(self):
        self.ledCol.setText(QDrillerDialog.datastore.collarfile)
        self.ledProjDir.setText(QDrillerDialog.datastore.projectdir)
        self.ledSur.setText(QDrillerDialog.datastore.surveyfile)
        self.ledProjName.setText(QDrillerDialog.datastore.projectname)
        self.ledCRS.setText(QDrillerDialog.datastore.projectCRS.authid())
        self.addtoLayerList()
        self.lstDHlogs.clear()
        for keys in QDrillerDialog.datastore.logfiles:
            newitem = self.lstDHlogs.addItem(keys)
        self.refreshGui()
        #consider working out a more efficient way of having the drillhole data ready
        # to use, but not needing to be calculated if its not used
        QDrillerDialog.datastore.calcDrillholes()
        
        #enable buttons and planview groupbox
        self.gpbxPlanview.setEnabled(True)
        
    def fetchCRS(self):
        #call on the QGIS GUI CRS selection Dialog
        getCRS = qgis.gui.QgsGenericProjectionSelector()
        getCRS.exec_()
        #initialise blank CRS
        selCRS = qgis.core.QgsCoordinateReferenceSystem()
        #turn blank CRS into desired CRS using the authority identifier selected above
        selCRS.createFromUserInput(getCRS.selectedAuthId())
        #set the projectCRS to the selected CRS (this is a QgsCRS type object)
        QDrillerDialog.datastore.projectCRS = selCRS
        self.ledCRS.setText(QDrillerDialog.datastore.projectCRS.authid())
        
    def openSectionView(self):
        self.sectionview = SectionView()
        self.sectionview.show()
        
    def printout(self):
        print QDrillerDialog.datastore.collarfile
        
#class for handling the data inputs. This will store data inputs, as well as 
#provide the capability for loading and saving projects 
#ie previous variable setups)
class DataStore(QtCore.QObject):
    #define signals
    fileCreated = QtCore.pyqtSignal()
    projectLoaded = QtCore.pyqtSignal()

    def __init__(self):
        super(DataStore, self).__init__()
        #variables to do with the backend calculations
        #container for drillhole data as read from file
        self.drillholes={}
        #container for the calculated XYZ coordinates
        self.drillholesXYZ={}
        
        #variables for running project
        self.savefilepath = None
        self.projectdir = None
        self.projectname = None
        self.projectCRS = None  #consider initialising this to a real projection?
        # a variable to store the list of section definition files used by section viewer?
        
        #variables important to calculations/backend
        self.collarfile = None
        self.surveyfile = None
        self.logfiles = []      #list of downhole log file paths
        self.logtarget = None
        self.trace2can = True
        self.log2can = True
        self.coll2can = True
        
        #variables for keeping track of created layers
        self.planLogLayers = []
        self.existingLayersDict ={}
        self.availSectionDict = {}
        
    
    def loadProjectData(self):
    #a function to load settings from a saved project file
        savefile = ET.parse(self.savefilepath)  #need to implement a openfile dialog in QDrillerDialog
        root = savefile.getroot()

        #assign variable from savefile datastore
        self.projectdir = root.find("prjdir").text
        self.projectname = root.find("prjname").text
        self.collarfile = root.find("collar").text
        self.surveyfile = root.find("survey").text
        
        selCRS = qgis.core.QgsCoordinateReferenceSystem()
        #turn blank CRS into desired CRS using the authority identifier
        crsid =root.find("prjcrs").text
        selCRS.createFromUserInput(crsid)
        #set the projectCRS to the selected CRS (this is a QgsCRS type object)
        self.projectCRS = selCRS
        
       
        self.logfiles = []
        for logs in root.findall("log"):
            self.logfiles.append(logs.text)
            
        self.existingLayersDict ={}
        for exlayers in root.findall("existlyr"):
            name = exlayers.get("name")
            path = exlayers.text
            self.existingLayersDict[name] = path
        
        #emit signal?
        self.projectLoaded.emit()
        
    def saveProjectData(self):
    #a function to write current settings to current project file
        
        root = ET.Element("savefile")
        ET.SubElement(root, "prjdir").text = self.projectdir
        ET.SubElement(root, "collar").text = self.collarfile
        ET.SubElement(root, "survey").text = self.surveyfile
        ET.SubElement(root, "prjname").text = self.projectname
        ET.SubElement(root, "prjcrs").text = self.projectCRS.authid()
        
        for logs in self.logfiles:
            ET.SubElement(root, "log").text = logs
            
        for k in self.existingLayersDict:
            ET.SubElement(root, "existlyr",{"name":k}).text = self.existingLayersDict[k]
        
        savefile = ET.ElementTree(root)
        savefile.write(self.savefilepath)
        #also set up for sectionviewer to throw a list of section definition files to the datastore and be written here
        
    def calcDrillholes(self):
    #read in from file and create the drillhole arrays for use
        self.drillholes = QDUtils.readFromFile(self.collarfile, self.surveyfile)
        self.drillholesXYZ = QDUtils.calcXYZ(self.drillholes)
        
    def createPlanTrace(self):
    #a function to create drill traces in plan view
        outputlayer = os.path.normpath(r"{}\{}_traces_P.shp".format(self.projectdir, self.projectname))
        
        QDUtils.writeTraceLayer(self.drillholesXYZ, outputlayer, loadcanvas = self.trace2can, crs=self.projectCRS)
        layername = os.path.splitext(os.path.basename(outputlayer))[0]
        self.existingLayersDict[layername]= outputlayer
        self.fileCreated.emit()
        
    def createPlanLog(self):
    #a function to create attributed logs in plan view
        logname = os.path.splitext(os.path.basename(self.logtarget))[0]
        outputlayer = os.path.normpath("{}\\{}_{}_P.shp".format(self.projectdir, self.projectname, logname))
        
        QDUtils.LogDrawer(self.drillholesXYZ, self.logtarget, outputlayer, plan=True, sectionplane=None, crs=self.projectCRS, loadcanvas=self.log2can)
        
        layername = os.path.splitext(os.path.basename(outputlayer))[0]
        self.existingLayersDict[layername]= outputlayer
        self.fileCreated.emit()
        
    def createCollarPoints(self):
    #a function to create a shapefile of collars
        outputlayer = os.path.normpath(r"{}\{}_collars.shp".format(self.projectdir, self.projectname))
        QDUtils.createCollarLayer(self.drillholes, outputlayer, loadcanvas=self.coll2can, crs=self.projectCRS)
        
        layername = os.path.splitext(os.path.basename(outputlayer))[0]
        self.existingLayersDict[layername]= outputlayer
        self.fileCreated.emit()
        
    def selectCollars(self, envelope):
        #a function to select collars that fall within an envelope, and return a drillhole XYS dictionary
        pass
        

SECT_FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'sectionview_base.ui'))


class SectionView(QtGui.QMainWindow, SECT_FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(SectionView, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        #initialise mapcanvas
        self.sectionCanvas = qgis.gui.QgsMapCanvas()
        #self.sectionCanvas.setCanvasColour(Qt.white)
        self.lytMap.addWidget(self.sectionCanvas)
        self.crs= qgis.core.QgsCoordinateReferenceSystem()
        self.crs.createFromUserInput("EPSG:4978")
        self.sectionCanvas.setDestinationCrs(self.crs)
        self.sectionCanvas.setMapUnits(0)
        
        #setup the legend
        
        
        
        
        
        
        #setup scale combobox widget
        self.scaleBox = qgis.gui.QgsScaleWidget()
        self.scaleBox.setMapCanvas(self.sectionCanvas)
        self.lytScale.addWidget(self.scaleBox)
        self.sectionCanvas.scaleChanged.connect(self.scaleBox.setScaleFromCanvas)
        self.scaleBox.scaleChanged.connect(lambda: self.sectionCanvas.zoomScale(self.scaleBox.scale())) #doesnt seem to work yet
        
        #setup mouse coord tracking
        self.sectionCanvas.xyCoordinates.connect(self.dispCoords)
        
        # create toolbar
        self.navToolbar = self.addToolBar("Map Tools")
        self.mapNavActions = QActionGroup(self)
        self.mapNavActions.addAction(self.actionZoom_in)
        self.mapNavActions.addAction(self.actionZoom_out)
        self.mapNavActions.addAction(self.actionTouch)
        self.mapNavActions.addAction(self.actionPan)
        self.navToolbar.addActions(self.mapNavActions.actions())
        self.sectionBar = self.addToolBar("Section Tools")
        self.sectionBar.addAction(self.actionGenerateSection)

        # connect the tool(s)
        self.actionZoom_in.triggered.connect(self.zoom_in)
        self.actionZoom_out.triggered.connect(self.zoom_out)
        self.actionPan.triggered.connect(self.mapPan)
        self.actionTouch.triggered.connect(self.mapTouch)
        self.actionGenerateSection.triggered.connect(self.genSec)
        
        # create the map tool(s)
        self.tool_zoomin = qgis.gui.QgsMapToolZoom(self.sectionCanvas, False)
        self.tool_zoomout = qgis.gui.QgsMapToolZoom(self.sectionCanvas, True)
        self.tool_pan = qgis.gui.QgsMapToolPan(self.sectionCanvas)
        self.tool_touch = qgis.gui.QgsMapToolTouch(self.sectionCanvas)
        
        
        
    def mapPan(self):
        self.sectionCanvas.setMapTool(self.tool_pan)
        print "pan action triggered"
        centre = self.sectionCanvas.center()
        print "centre of canvas", centre.toString()
        
    def mapTouch(self):
        self.sectionCanvas.setMapTool(self.tool_touch)
        print "touch action triggered"
        self.mapInformation()
        
    def zoom_in(self): #could these type things be set up in a lambda connection
        self.sectionCanvas.setMapTool(self.tool_zoomin)
        print "zoom in action triggered"
        
    def zoom_out(self): #could these type things be set up in a lambda connection
        self.sectionCanvas.setMapTool(self.tool_zoomout)
        print "zoom out action triggered"
        
    def dispCoords(self, point):
        xCoord = int(point.x())
        yCoord = int(point.y())
        display = "{}m,{}mRL".format(xCoord, yCoord)
        self.ledCoord.setText(display)
        
    def genSec(self):
        print "gensec action triggered"
        self.genSecDialog = GenerateSection()
        self.genSecDialog.show()
        
    def chooseSection(self):
        #funstion to handle the GUI call to load a section
        sectionname = self.cbxSelSection.text()
        sectionpath = QDrillerDialog.datastore.availSectionDict[sectionname] #filepath to the definition fileCreated
        self.loadSection(sectionpath)
        
    def loadSection(self, sectionpath):
        #function to load all the layers of a generated section using the Section Definition File
        #read the definition file
        tree = ET.parse(sectionpath)
        root = tree.getroot()
        #pull all the layer paths from the definition file
        layerlist = []
        for lyrs in root.findall("layer"):
            layerlist.append(lyrs.text)
            
        #open all the files, and add to canvas
            
    def mapInformation(self):
        print "canvas extent", self.sectionCanvas.extent()
        self.sectionCanvas.refresh()
        print "canvas unit", self.sectionCanvas.mapUnits()
        centre = self.sectionCanvas.center()
        print "centre of canvas", centre.toString()
        print "canvas projection ", self.sectionCanvas.mapSettings().destinationCrs().authid()
        print "Canvas Scale", self.sectionCanvas.scale()
        print"canvas setting scale", self.sectionCanvas.mapSettings().scale()
            
GEN_FORM_CLASS, _ = uic.loadUiType(os.path.join(
os.path.dirname(__file__), 'generatesection_dialog_base.ui'))


class GenerateSection(QtGui.QDialog, GEN_FORM_CLASS):
    def __init__(self, parent=None):
        """Constructor."""
        super(GenerateSection, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        #initialise variables to store settings
        self.secName = None
        self.originX = None
        self.originY = None
        self.secAzi = None      #may need to investigate the maths behind this more to get facing
        self.secFacing = None
        self.envWidth = None
        self.secLength = None
        self.holes2plotXYZ = None
        self.availLogs ={}
        self.selectedLogs = []
        self.availDrillholes = []
        self.selDrillholes = []
        
        
        
        
        #set the crs using the same hardcode as in the section viewer
        self.crs= qgis.core.QgsCoordinateReferenceSystem()
        self.crs.createFromUserInput("EPSG:4978")
        
        #connect GUI buttons
        self.btnAddDHLog.clicked.connect(self.addDHLog)
        self.btnRemDHLog.clicked.connect(self.remDHLog)
        self.btnAddDH.clicked.connect(self.addDH)
        self.btnRemDH.clicked.connect(self.remDH)
        self.btnDraw.clicked.connect(self.generateSection)
        self.btnFilterHoles.clicked.connect(self.filterHoles)
        
        
        #connect GUI with variables
        self.ledSecName.textChanged.connect(lambda: self.setVars("name", self.ledSecName.text()))
        self.ledOriginX.textChanged.connect(lambda: self.setVars("originX", self.ledOriginX.text()))
        self.ledOriginY.textChanged.connect(lambda: self.setVars("originY", self.ledOriginY.text()))
        self.ledAzi.textChanged.connect(lambda: self.setVars("azi", self.ledAzi.text()))
        self.ledEnv.textChanged.connect(lambda: self.setVars("Env", self.ledEnv.text()))
        self.ledSecLength.textChanged.connect(lambda: self.setVars("seclength", self.ledSecLength.text()))
        
        #populate lists
        self.populateDHloglist()
        
    def setVars(self, target, value):
        
        if target == "originX":
           self.originX = float(value)
        elif target == "originY":
            self.originY = float(value)
        elif target == "azi":
            self.secAzi = float(value)
        elif target == "name":
            self.secName = value
        elif target == "Env":
            self.envWidth = float(value)
        elif target == "seclength":
            self.secLength = value
            
    def subsetDrillholes(self):
        #create the subset of drill XYZ to plot
        self.holes2plotXYZ = QDrillerDialog.datastore.drillholesXYZ #placeholder only, need to make function to perform subset
        
    def filterHoles(self):
        #function to filter the available holes to that within the envelope and set the selected drillholes to this
        print "filtering not implemented yet"
        
    def populateDHloglist(self):
        #generate a list of available downhole log datasets
        availLogNames =[]
        
        for entry in QDrillerDialog.datastore.logfiles:
            name = os.path.splitext(os.path.basename(entry))[0]
            self.availLogs[name] = entry
            availLogNames.append(name)
        
        for item in availLogNames:
            self.lstAvailLogs.addItem(item)
            
        #generate a list of available drillholes
        for holes in QDrillerDialog.datastore.drillholesXYZ.keys():
            self.lstAvailDH.addItem(holes)
        
            
    def addDHLog(self):
        print "addDHLog function called"
        for item in self.lstAvailLogs.selectedItems():
            self.lstSelLogs.addItem(self.lstAvailLogs.takeItem(self.lstAvailLogs.row(item)))
       
        
    def remDHLog(self):
        print "remDHLog function called"
        
        for item in self.lstSelLogs.selectedItems():
            self.lstAvailLogs.addItem(self.lstSelLogs.takeItem(self.lstSelLogs.row(item)))
            
    def addDH(self):
        print "addDH function called"

        for item in self.lstAvailDH.selectedItems():
            self.lstSelDH.addItem(self.lstAvailDH.takeItem(self.lstAvailDH.row(item)))
        
    def remDH(self):
        print "remDH function called"

        for item in self.lstSelDH.selectedItems():
            self.lstAvailDH.addItem(self.lstSelDH.takeItem(self.lstSelDH.row(item)))

    def generateSection(self):
        #create directory to store the relevant section files
        ### maybe at some point put in here a warning if the directory already exists?
        
        #run the methods to draw the files
        self.subsetDrillholes()
        #create drill traces
        sectionLayers=[]
        outputlayer = os.path.normpath(r"{}\{}\{}_traces_S.shp".format(
                                        QDrillerDialog.datastore.projectdir,self.secName,
                                        QDrillerDialog.datastore.projectname)
                                        )
        #create directory to store the relevant section files
        ### maybe at some point put in here a warning if the directory already exists?
        sectiondirectory = os.path.dirname(outputlayer)
        try: 
            os.makedirs(sectiondirectory)
        except OSError:
            if not os.path.isdir(sectiondirectory):
                raise

        secplane = [self.originX, self.originY, self.secAzi]
        print "secplane", secplane
            
        QDUtils.writeTraceLayer(self.holes2plotXYZ, outputlayer, plan=False, sectionplane=secplane, loadcanvas=False, crs=self.crs)
        sectionLayers
       
        # here need to include code to write to section definition file
        sectionLayers.append(outputlayer)
        
        #create downhole logs
        #Pull the desired downhole logs
        logtargetDict = {}
        for i in xrange(self.lstSelLogs.count()):
            name = self.lstSelLogs.item(i).text()
            logtargetDict[name] = self.availLogs[name] 
        
        print "logtargetDict", logtargetDict
        #code to generate log 
        for k in logtargetDict:
            
            logname = k
            logtarget = logtargetDict[k]
            outputlayer = os.path.normpath("{}\\{}\\{}_{}_S.shp".format(QDrillerDialog.datastore.projectdir,
                                            self.secName, QDrillerDialog.datastore.projectname, logname)
                                            )
            print "outputlayer", outputlayer
            secplane = [self.originX, self.originY, self.secAzi]
            print "secplane", secplane
            
            QDUtils.LogDrawer(self.holes2plotXYZ, logtarget, outputlayer, plan=False, 
                                sectionplane=secplane, crs=self.crs, loadcanvas=False)
            
            sectionLayers.append(outputlayer)

        # here need to include code to write to section definition file
        secDef= ET.Element("sectionDefinition", {"name":self.secName})
        for lyrs in sectionLayers:
            ET.SubElement(secDef, "layer").text = lyrs
            
        secDefPath = os.path.normpath("{}\\{}.qdsd".format(os.path.dirname(outputlayer),self.secName))
        tree = ET.ElementTree(secDef)
        tree.write(secDefPath)
        QDrillerDialog.datastore.availSectionDict[self.secName]= secDefPath
