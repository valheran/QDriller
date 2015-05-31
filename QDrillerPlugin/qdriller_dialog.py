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
import math
import sys
import shutil
import csv

try:
    import xml.etree.cElementTree as ET
except ImportError:
    import xml.etree.ElementTree as ET

import GdalTools_utils as gTools
from PyQt4 import QtGui, uic, QtCore, Qt
from PyQt4.QtGui import * 

from qgis.core import *
from qgis.gui import *

#import module with all the technical backend code
import QDriller_Utilities as QDUtils
#import composer.qdrillercomposer as qcomp
from composer import qdriller_composer as qcomp
sys.excepthook = sys.__excepthook__

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'qdriller_dialog_base.ui'))


class QDrillerDialog(QtGui.QMainWindow, FORM_CLASS):

    
    sectionview = None
    datastore = None
    def __init__(self, iface, parent=None):
        """Constructor."""
        super(QDrillerDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.iface = iface
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
        self.btnAddtoCanvas.clicked.connect(self.addtoCanvas)
        self.btnValidate.clicked.connect(self.validateData)
        
        
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
        self.chkIsNegDip.toggled.connect(lambda: self.setVariable("isNegDip", self.chkIsNegDip.isChecked()))
        #self.chkEohlab.toggled.connect()
        #self.chkDHTick.toggled.connect()
        
        ##Other Signals###
        QDrillerDialog.datastore.fileCreated.connect(self.addtoLayerList)
        QDrillerDialog.datastore.projectLoaded.connect(self.onProjectLoad)
        
    #functions for running the gui
    def validateData(self):
    
        self.valDlg = ValidateFiles(QDrillerDialog.datastore.collarfile,
                                    QDrillerDialog.datastore.surveyfile, 
                                    QDrillerDialog.datastore.logfiles, 
                                    QDrillerDialog.datastore.isNegDip)
                                    
        self.valDlg.validationPassed.connect(self.btnCreatePrj.setEnabled)
        self.valDlg.show()
        
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
        elif target == "isNegDip":
            QDrillerDialog.datastore.isNegDip = value
            
        
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
            
    def addtoCanvas(self):
        #add layers from the existing layers list to the main map canvas
        addlist=[]
        for item in self.lstExistingLayers.selectedItems():
            addlist.append(item.text())
            
        for names in addlist:
            path = QDrillerDialog.datastore.existingLayersDict[names]
            layer = QgsVectorLayer(path, names, "ogr")
            QgsMapLayerRegistry.instance().addMapLayer(layer)
            
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
            mapregList = QgsMapLayerRegistry.instance().mapLayersByName(names)
            for lyr in mapregList:
                QgsMapLayerRegistry.instance().removeMapLayer(lyr.id())
                
        #delete shapefiles
        for names in delList:
            path = QDrillerDialog.datastore.existingLayersDict[names]
            QgsVectorFileWriter.deleteShapeFile(path)
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
        self.chkIsNegDip.setChecked(QDrillerDialog.datastore.isNegDip)
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
        getCRS = QgsGenericProjectionSelector()
        getCRS.exec_()
        #initialise blank CRS
        selCRS = QgsCoordinateReferenceSystem()
        #turn blank CRS into desired CRS using the authority identifier selected above
        selCRS.createFromUserInput(getCRS.selectedAuthId())
        #set the projectCRS to the selected CRS (this is a QgsCRS type object)
        QDrillerDialog.datastore.projectCRS = selCRS
        self.ledCRS.setText(QDrillerDialog.datastore.projectCRS.authid())
        
    def openSectionView(self):
        QDrillerDialog.sectionview = SectionView(self.iface)
        QDrillerDialog.sectionview.show()
        #need to deal with the registry when the window closes
        
        
    def printout(self):
        print QDrillerDialog.datastore.collarfile
        

class DataStore(QtCore.QObject):
    #class for handling the data inputs. This will store data inputs, as well as 
    #provide the capability for loading and saving projects 
    #ie previous variable setups)
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
        self.isNegDip = True
        
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
        isNegString = root.find("isNegDip").text
        if isNegString == "False":
            self.isNegDip = False
        else:
            self.isNegDip = True
          
        selCRS = QgsCoordinateReferenceSystem()
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
            
        self.availSectionDict ={}
        for sects in root.findall("sections"):
            name = sects.get("name")
            path = sects.text
            self.availSectionDict[name] = path
        
        #emit signal
        self.projectLoaded.emit()
        
    def saveProjectData(self):
    #a function to write current settings to current project file
        
        root = ET.Element("savefile")
        ET.SubElement(root, "prjdir").text = self.projectdir
        ET.SubElement(root, "collar").text = self.collarfile
        ET.SubElement(root, "survey").text = self.surveyfile
        ET.SubElement(root, "prjname").text = self.projectname
        ET.SubElement(root, "prjcrs").text = self.projectCRS.authid()
        ET.SubElement(root, "isNegDip").text = str(self.isNegDip)
        
        for logs in self.logfiles:
            ET.SubElement(root, "log").text = logs
            
        for k in self.existingLayersDict:
            ET.SubElement(root, "existlyr",{"name":k}).text = self.existingLayersDict[k]
            
        for s in self.availSectionDict:
            ET.SubElement(root, "sections",{"name":s}).text = self.availSectionDict[s]
            
        savefile = ET.ElementTree(root)
        savefile.write(self.savefilepath)
        
        
    def calcDrillholes(self):
    #read in from file and create the drillhole arrays for use
        self.drillholes = QDUtils.readFromFile(self.collarfile, self.surveyfile)
        self.drillholesXYZ = QDUtils.calcXYZ(self.drillholes, self.isNegDip)
        
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
        
        
        
SECT_FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'sectionview_base.ui'))


class SectionView(QtGui.QMainWindow, SECT_FORM_CLASS):
    def __init__(self, iface, parent=None):
        """Constructor."""
        super(SectionView, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.iface = iface
        
        #initialise mapcanvas
        self.sectionCanvas = QgsMapCanvas()
        self.sectionCanvas.enableAntiAliasing(True)
        #self.sectionCanvas.setCanvasColour(Qt.white)
        self.lytMap.addWidget(self.sectionCanvas)
        self.crs= QgsCoordinateReferenceSystem()
        self.crs.createFromUserInput("EPSG:4328")
        self.sectionCanvas.setDestinationCrs(self.crs)
        self.sectionCanvas.setMapUnits(0)
        
        #setup the legend
        self.layertreeRoot = QgsLayerTreeGroup()
        self.bridge = QgsLayerTreeMapCanvasBridge(self.layertreeRoot, self.sectionCanvas)
        self.bridge.setAutoSetupOnFirstLayer(False)  #stop the CRS and units being changed when loading layers
        self.model = QgsLayerTreeModel(self.layertreeRoot)
        self.model.setFlag(QgsLayerTreeModel.AllowNodeChangeVisibility)
        self.model.setFlag(QgsLayerTreeModel.AllowNodeReorder)
        #self.model.setFlag(QgsLayerTreeModel.AllowLegendChangeState)
        #self.model.setFlag(QgsLayerTreeModel.ShowLegend)
        self.legendView = QgsLayerTreeView()
        self.legendView.setModel(self.model)
        self.menupr = SVMenuProvider(self.legendView, self.iface)
        self.legendView.setMenuProvider(self.menupr)
        self.lytLegend.addWidget(self.legendView)
        
        #setup identify box NOTE has been set up in designer, given the name identTree
        #self.identTree = QtGui.QTreeWidget()
        #self.lytIdentify.addWidget(self.identTree)
        
        #setup scale combobox widget
        self.scaleBox = QgsScaleWidget()
        self.scaleBox.setMapCanvas(self.sectionCanvas)
        self.lytScale.addWidget(self.scaleBox)
        self.sectionCanvas.scaleChanged.connect(self.scaleBox.setScaleFromCanvas)
        self.scaleBox.scaleChanged.connect(self.setScale) #doesnt seem to work yet
        
        #setup mouse coord tracking
        self.sectionCanvas.xyCoordinates.connect(self.dispCoords)
        
        # create toolbars
        self.navToolbar = self.addToolBar("Map Tools")
        self.mapNavActions = QActionGroup(self)
        self.mapNavActions.addAction(self.actionZoom_in)
        self.mapNavActions.addAction(self.actionZoom_out)
        self.mapNavActions.addAction(self.actionTouch)
        self.mapNavActions.addAction(self.actionPan)
        self.navToolbar.addActions(self.mapNavActions.actions())
        self.sectionBar = self.addToolBar("Section Tools")
        self.sectionBar.addAction(self.actionGenerateSection)
        self.sectionBar.addAction(self.actionManageSections)
        self.sectionBar.addAction(self.actionAddLayer)
        self.featureTools = self.addToolBar("Feature Tools")
        self.featureTools.addAction(self.actionIdentify)
        self.featureTools.addAction(self.actionMeasureTool)
        self.featureTools.addAction(self.actionMeasureArea)
        self.featureTools.addAction(self.actionSaveAsImage)
        self.mapNavActions.addAction(self.actionIdentify)
        self.mapNavActions.addAction(self.actionMeasureTool)
        self.mapNavActions.addAction(self.actionMeasureArea)
        #set up grid toolbars
        self.gridToolbar = self.addToolBar("Grid Tools")
        self.gridToolbar.addAction(self.actionGrid)
        self.validator = QDoubleValidator(0, 100000, 0)
        self.ledXspace = QLineEdit()
        self.ledYspace = QLineEdit()
        self.ledXspace.setFixedSize(40, 20)
        self.ledXspace.setText("0")
        self.ledYspace.setText("0")
        self.ledYspace.setFixedSize(40, 20)
        self.ledXspace.setValidator(self.validator)
        self.ledYspace.setValidator(self.validator)
        self.gridToolbar.addWidget(self.ledXspace)
        self.gridToolbar.addWidget(self.ledYspace)
        self.gridRB = QgsRubberBand(self.sectionCanvas)
        self.gridRB.setColor(QtCore.Qt.black)
        #set up editing toolbars
        self.editingToolbar = self.addToolBar("Editing Tools")
        self.editingToolbar.addAction(self.actionToggleEditing) 
        self.editingActions = QActionGroup(self)
        self.editingActions.addAction(self.actionSaveEdits)
        self.editingActions.addAction(self.actionRollBackEdits)
        self.editingActions.addAction(self.actionAddPoint)
        self.editingActions.addAction(self.actionAddLine)
        self.editingActions.addAction(self.actionAddPolygon)
        self.editingActions.addAction(self.actionMoveFeature)
        self.editingActions.addAction(self.actionNodeTool)

        self.editingToolbar.addActions(self.editingActions.actions())
        self.editingActions.setDisabled(True)
        self.actionAddLine.setVisible(False)
        self.actionAddPolygon.setVisible(False)
        
        # connect the tool(s)
        self.actionZoom_in.triggered.connect(self.zoom_in)
        self.actionZoom_out.triggered.connect(self.zoom_out)
        self.actionPan.triggered.connect(self.mapPan)
        self.actionTouch.triggered.connect(self.mapTouch)
        self.actionGenerateSection.triggered.connect(self.genSec)
        self.actionIdentify.triggered.connect(self.mapIdentify)
        self.actionManageSections.triggered.connect(self.manageSections)
        self.actionMeasureTool.triggered.connect(self.measureLength)
        self.actionMeasureArea.triggered.connect(self.measureArea)
        self.actionGrid.toggled.connect(self.addCanvasGrid)
        self.actionSaveAsImage.triggered.connect(self.saveImage)
        self.actionAddLayer.triggered.connect(self.addSectionLayer)
        self.actionToggleEditing.triggered.connect(self.toggleEdits)
        self.actionAddPoint.toggled.connect(self.on_addPoint)
        self.actionAddLine.toggled.connect(self.on_addLine)
        self.actionAddPolygon.toggled.connect(self.on_addPolygon)
        self.actionSaveEdits.triggered.connect(self.on_saveEdits)
        self.actionRollBackEdits.triggered.connect(self.on_rollBack)
        self.actionMoveFeature.triggered.connect(self.on_moveFeature)
        self.actionNodeTool.triggered.connect(self.on_nodeTool)
        
        # create the map tool(s)
        self.tool_zoomin = QgsMapToolZoom(self.sectionCanvas, False)
        self.tool_zoomout = QgsMapToolZoom(self.sectionCanvas, True)
        self.tool_pan = QgsMapToolPan(self.sectionCanvas)
        self.tool_touch = QgsMapToolTouch(self.sectionCanvas)
        self.tool_identify = IdentifyTool(self.sectionCanvas, self.identTree)
        self.tool_measLength = MeasureLineTool(self.sectionCanvas, self.ledSegLen, self.ledTotalLen, self.lstSeg)
        self.tool_measArea = MeasureAreaTool(self.sectionCanvas, self.ledTotalLen)      
        
        #set default tool to touch
        self.mapTouch()
        #maptool signals
        self.tool_measLength.dialogOpened.connect(self.activateWindow)
        self.refreshGui()
        #listen for signals
        self.layertreeRoot.visibilityChanged.connect(self.visibilitySetter)
        self.legendView.currentLayerChanged.connect(self.getFacing)
        self.legendView.currentLayerChanged.connect(self.onSelLayerChange)
        self.sectionCanvas.extentsChanged.connect(self.refreshGrid)
        self.sectionCanvas.mapToolSet.connect(self.onToolChange)
        self.ledXspace.editingFinished.connect(self.refreshGrid)
        self.ledYspace.editingFinished.connect(self.refreshGrid)
       # self.legendView.currentLayerChanged.connect(self.model.refreshLayerLegend)
        #load up any pre-existing sections
        
    def setScale(self):
        scale = 1 / self.scaleBox.scale()
        self.sectionCanvas.zoomScale(scale)
    def mapIdentify(self):
        self.sectionCanvas.setMapTool(self.tool_identify)
        self.dockIdent.setVisible(True)

    def mapPan(self):
        self.sectionCanvas.setMapTool(self.tool_pan)
        
    def mapTouch(self):
        self.sectionCanvas.setMapTool(self.tool_touch)
        self.statusbar.clear()
        self.statusbar.showMessage("Current Map Tool: Touch")
        
    def zoom_in(self): #could these type things be set up in a lambda connection
        self.sectionCanvas.setMapTool(self.tool_zoomin)
        
    def zoom_out(self): #could these type things be set up in a lambda connection
        self.sectionCanvas.setMapTool(self.tool_zoomout)
        
    def measureLength(self):
        self.sectionCanvas.setMapTool(self.tool_measLength)
        self.statusbar.clear()
        self.statusbar.showMessage("Current Map Tool: Line Measure. LMB to add segment, RMB to finish")
    def measureArea(self):
        self.sectionCanvas.setMapTool(self.tool_measArea)
        self.statusbar.clear()
        self.statusbar.showMessage("Current Map Tool: Area Measure. LMB to add vertex, RMB to finish")
        
    def dispCoords(self, point):
        xCoord = int(point.x())
        yCoord = int(point.y())
        display = "{}m, {}mRL".format(xCoord, yCoord)
        self.ledCoord.setText(display)
        
    def genSec(self):
        
        self.genSecDialog = GenerateSection(self.iface)
        #listen out for sections to be generated
        self.genSecDialog.sectionGenerated.connect(self.refreshGui)
        
        self.genSecDialog.show()
        
    def manageSections(self):
        self.manSecDialog = SectionManager(self)
        self.manSecDialog.sectionDeleted.connect(self.refreshGui)
        self.manSecDialog.show()
        
    def loadSection(self, sectionpath):
        #function to load all the layers of a generated section using the Section Definition File
        #read the definition file
        #self.layertreeRoot.blockSignals(True)
        tree = ET.parse(sectionpath)
        dfn = tree.getroot()
        #pull all the layer paths from the definition file
        layerlist = []
        for lyrs in dfn.findall("layer"):
            layerlist.append(lyrs.text)
        
        #create group in layertree to hold layers --could collapse this into the above loop-?
        lgroup = self.layertreeRoot.addGroup(dfn.get("name"))
        #open all the files, and add to canvas
        for lyr in layerlist:
            lname =os.path.splitext(os.path.basename(lyr))[0]
            l = QgsVectorLayer(lyr, lname,"ogr")
            QgsMapLayerRegistry.instance().addMapLayer(l, False)
            lgroup.addLayer(l)
            extent= l.extent()
        self.visibilitySetter(lgroup, QtCore.Qt.Checked)
        #self.layertreeRoot.blockSignals(False)
        self.sectionCanvas.setExtent(extent)

    def refreshGui(self):
        #Reload the sections
        print "Section View Refresh Called"
        #clear out any current layers
        self.layertreeRoot.removeAllChildren()
        
        #Load each section from the availSectionDict
        for sects in QDrillerDialog.datastore.availSectionDict:
            self.loadSection(QDrillerDialog.datastore.availSectionDict[sects])
        
    def visibilitySetter(self, node, state):
        #funstion to ensure only one section at a time is shown
        #designed to respond to the visibility changed signal emitted 
        #determine if signal came from group or not
        if (node.nodeType()==0) and (state == QtCore.Qt.Checked):
            for groups in self.layertreeRoot.children():
                groups.setVisible(QtCore.Qt.Unchecked)
                groups.setExpanded(False)
                
            node.setVisible(QtCore.Qt.Checked)
            node.setExpanded(True)
    
    def getFacing(self):
        #this could be collapsed into onSelLayerChange?
        group = self.legendView.currentGroupNode()
        groupname = group.name()
        path = os.path.normpath("{}\\{}\\{}.qdsd".format(QDrillerDialog.datastore.projectdir, groupname, groupname))
        tree = ET.parse(path)
        root = tree.getroot()
        try:
            secFacing = root.find("facing").text
            self.ledFacing.setText(str(secFacing))
        except AttributeError:
            self.ledFacing.setText("N/A")
            
    def addCanvasGrid(self, plot):
    
        if plot:
            self.gridRB.reset(QGis.Line)
            CanvasGrid(self.sectionCanvas, self.ledXspace.text(), self.ledYspace.text(), self.gridRB)
            self.gridRB.show()
        elif not plot:
            self.gridRB.reset(QGis.Line)
            
    def refreshGrid(self):
        if self.actionGrid.isChecked():
            try:
                float(self.ledYspace.text())
            except ValueError:
                self.ledYspace.setText("0")
            try:
                float(self.ledXspace.text())
            except ValueError:
                self.ledXspace.setText("0")
                
            self.addCanvasGrid(True)
            
    def saveImage(self):
        ExportImage(self.sectionCanvas, self.iface.mapCanvas())

    def addSectionLayer(self):
        #add a blank layer to a section to allow for annotation, interpretation etc
        
        #call up dialog to get parameters
        paraDlg = AddNewLayerDialog()
        if paraDlg.exec_()==1:
            #create file path
            #if self.legendView.currentGroupNode() is not None:
             #   currGroup =self.legendView.currentGroupNode()
            #else:
            for groups in self.layertreeRoot.children():
                #print groups.isVisible
                if groups.isVisible() == QtCore.Qt.Checked:
                    currGroup = groups
            secName = currGroup.name()
            lyrName = paraDlg.lyrName
            filepath = os.path.normpath("{}\\{}\\{}.shp".format(QDrillerDialog.datastore.projectdir, secName, lyrName))
            #create empty file
            writer = QgsVectorFileWriter(filepath, "CP1250", paraDlg.fields, paraDlg.geometryType, self.crs, "ESRI Shapefile")
            del writer
            #add to section definition
            defnTree = ET.parse(os.path.normpath("{}\\{}\\{}.qdsd".format(QDrillerDialog.datastore.projectdir, secName, secName)))
            defnRoot = defnTree.getroot()
            ET.SubElement(defnRoot, "layer").text = filepath
            tree = ET.ElementTree(defnRoot)
            tree.write(os.path.normpath("{}\\{}\\{}.qdsd".format(QDrillerDialog.datastore.projectdir, secName, secName)))
            #add to sectionview
            l = QgsVectorLayer(filepath, lyrName,"ogr")
            QgsMapLayerRegistry.instance().addMapLayer(l, False)
            currGroup.addLayer(l)
           
    def onToolChange(self, newtool):
        try:
            self.statusbar.clear()
            self.statusbar.showMessage("Current Map Tool:{}".format(newtool.toolName()))
            #print "oldtool", oldtool.toolName()
            if not newtool.isEditTool():
                self.actionAddLine.setChecked(False)
                self.actionAddPoint.setChecked(False)
                self.actionAddPolygon.setChecked(False)
                self.actionNodeTool.setChecked(False)
                self.actionMoveFeature.setChecked(False)
        except AttributeError:
            pass
            
    def onSelLayerChange(self):
        layer = self.legendView.currentLayer()
        geotype = layer.geometryType()
        #set the right combination of editing buttons and button checkstates
        self.actionMoveFeature.setChecked(False)
        if geotype == QGis.Point:
            self.actionAddPoint.setVisible(True)
            self.actionAddPoint.setChecked(False)
            self.actionAddLine.setVisible(False)
            self.actionAddPolygon.setVisible(False)
        elif geotype == QGis.Line:
            self.actionAddPoint.setVisible(False)
            self.actionAddLine.setVisible(True)
            self.actionAddLine.setChecked(False)
            self.actionAddPolygon.setVisible(False)
        elif geotype == QGis.Polygon:
            self.actionAddPoint.setVisible(False)
            self.actionAddLine.setVisible(False)
            self.actionAddPolygon.setVisible(True)
            self.actionAddPolygon.setChecked(False)
                
        #set the toggleEdits button to the right state
        if layer.isEditable():
            self.actionToggleEditing.setChecked(True)
            self.editingActions.setEnabled(True)
        else:
            self.actionToggleEditing.setChecked(False)
            self.editingActions.setEnabled(False)
        
        #enable/disable saving/rollback edits depending on modified state of the layer
        if layer.isModified():
            self.actionSaveEdits.setEnabled(True)
            self.actionRollBackEdits.setEnabled(True)
        else:
            self.actionSaveEdits.setEnabled(False)
            self.actionRollBackEdits.setEnabled(False)
        #set signal to listen for changes
        layer.layerModified.connect(lambda: self.enableSaveActions(layer))
        
        #disable editing tools to prevent using a tool on an unintended layer
        currMaptool = self.sectionCanvas.mapTool()
        if currMaptool.isEditTool():
            self.mapTouch()
            
    def toggleEdits(self):
        #turn on/off editing for the currently selected layer
        #set current layer as editable/not editable
        layer = self.legendView.currentLayer()
        if self.actionToggleEditing.isChecked():
            #start editing
            layer.startEditing()
            self.editingActions.setEnabled(True)
            #set map tool to touch to stop accidentally using another edit tool
            self.mapTouch()
            self.actionTouch.setChecked(True)
        else:
            #stop editing
            if layer.isModified():
                #prompt user for input for what to do with unsaved edits
                msgbox = QMessageBox()
                msgbox.setWindowTitle("Stop Editing")
                msgbox.setIcon(QMessageBox.Information)
                msgbox.setText("{} has unsaved changes".format(layer.name()))
                msgbox.setInformativeText("Do you want to save the changes?")
                msgbox.setStandardButtons(QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
                result = msgbox.exec_()
                
                if result == QMessageBox.Save:
                    layer.commitChanges()
                    self.editingActions.setEnabled(False)
                    self.mapTouch()
                    
                elif result == QMessageBox.Discard:
                    layer.rollBack()
                    self.editingActions.setEnabled(False)
                    self.mapTouch()
                    
                elif result == QMessageBox.Cancel:
                    self.actionToggleEditing.setChecked(True)
            else:
                layer.commitChanges()
                self.editingActions.setEnabled(False)
                self.mapTouch()
                self.actionTouch.setChecked(True)
           
    def enableSaveActions(self, layer):
        if layer.isModified():
            self.actionSaveEdits.setEnabled(True)
            self.actionRollBackEdits.setEnabled(True)
        else:
            self.actionSaveEdits.setEnabled(False)
            self.actionRollBackEdits.setEnabled(False)
            
    def on_saveEdits(self):
        #save changes to current layer
        layer = self.legendView.currentLayer()
        layer.commitChanges()
        self.actionSaveEdits.setEnabled(False)
        self.actionRollBackEdits.setEnabled(False)
        layer.startEditing()
        
    def on_rollBack(self):
        #roll back changes to current layer
        layer = self.legendView.currentLayer()
        layer.rollBack()
        self.actionRollBackEdits.setEnabled(False)
        self.actionSaveEdits.setEnabled(False)
        layer.startEditing()
        
    def on_addPoint(self):
        # call map tool to add new features to current layer
        layer = self.legendView.currentLayer()
        
        if layer.isEditable():
            self.tool_addPoint = AddNewPointFeature(self.sectionCanvas, layer )
            self.sectionCanvas.setMapTool(self.tool_addPoint)
            self.statusbar.clear()
            self.statusbar.showMessage("Add Point: LMB to add vertex")
            
        else:
            print "layer {} is not editable".format(layer.name())
            
    def on_addLine(self):
        # call map tool to add new features to current layer
        layer = self.legendView.currentLayer()
        
        if layer.isEditable():
            self.tool_addLine = AddNewPolyFeature(self.sectionCanvas, layer, "Line" )
            self.sectionCanvas.setMapTool(self.tool_addLine)
            self.statusbar.clear()
            self.statusbar.showMessage("Add Line: LMB to add vertex, RMB to accept feature ")
        else:
            print "layer {} is not editable".format(layer.name())
            
    def on_addPolygon(self):
        # call map tool to add new features to current layer
        layer = self.legendView.currentLayer()
        
        if layer.isEditable():
            self.tool_addPoly = AddNewPolyFeature(self.sectionCanvas, layer, "Polygon" )
            self.sectionCanvas.setMapTool(self.tool_addPoly)
            self.statusbar.clear()
            self.statusbar.showMessage("Add Polygon: LMB to add vertex, RMB to accept feature ")
        else:
            print "layer {} is not editable".format(layer.name())
            
    def on_moveFeature(self):
        layer = self.legendView.currentLayer()
        
        if layer.isEditable():
            self.tool_moveFeature = MoveFeatureTool(self.sectionCanvas, layer)
            self.sectionCanvas.setMapTool(self.tool_moveFeature)
            self.statusbar.clear()
            self.statusbar.showMessage("Move Feature Tool: Drag to move feature; Hold CTRL to multiselect")
        else:
            print "layer {} is not editable".format(layer.name())
            
    def on_nodeTool(self):
        layer = self.legendView.currentLayer()
        
        if layer.isEditable():
            self.tool_nodeTool = NodeTool(self.sectionCanvas, layer)
            self.sectionCanvas.setMapTool(self.tool_nodeTool)
            self.statusbar.clear()
            self.statusbar.showMessage("Node Tool: LMB select Feature; drag to move vertex; double click to add vertex; DEL/BKSP to remove vertex")
        else:
            self.statusbar.clear()
            self.statusbar.showMessage("layer {} is not editable".format(layer.name()))
            
    def closeEvent(self, event):
        #clean up map registry of files that were opened in section view
        layerstoclose = self.layertreeRoot.findLayerIds()
        QgsMapLayerRegistry.instance().removeMapLayers(layerstoclose)
        
        
GEN_FORM_CLASS, _ = uic.loadUiType(os.path.join(
os.path.dirname(__file__), 'generatesection_dialog_base.ui'))

class GenerateSection(QtGui.QDialog, GEN_FORM_CLASS):

    sectionGenerated = QtCore.pyqtSignal()

    def __init__(self, iface, parent=None):
        """Constructor."""
        super(GenerateSection, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        self.iface = iface
        self.canvas = self.iface.mapCanvas()
        
        #initialise variables to store settings
        self.secName = None
        self.originX = None
        self.originY = None
        self.secAzi = None      #may need to investigate the maths behind this more to get facing
        self.secFacing = None
        self.envWidth = 25
        self.secLength = None
        self.holes2plotXYZ = {}
        self.availLogs ={}
        self.selectedLogs = []
        self.availDrillholes = []
        self.selDrillholes = []
        self.demPath = None
        self.useEnvelope = False
        
        #set the crs using the same hardcode as in the section viewer
        self.crs= QgsCoordinateReferenceSystem()
        self.crs.createFromUserInput("EPSG:4328")
        
        self.messageBar = QgsMessageBar()
        self.lytMessage.addWidget(self.messageBar)
        
        #connect GUI buttons
        self.btnAddDHLog.clicked.connect(self.addDHLog)
        self.btnRemDHLog.clicked.connect(self.remDHLog)
        self.btnAddDH.clicked.connect(self.addDH)
        self.btnRemDH.clicked.connect(self.remDH)
        self.btnDraw.clicked.connect(self.generateSection)
        self.btnFilterHoles.clicked.connect(self.filterHoles)
        self.btnOrigin.clicked.connect(self.drawSectionLine)
        self.btnFromLine.clicked.connect(self.fromSelectedLine)
        self.btnDem.clicked.connect(self.showRasterFileBrowser)
        
        #setup map tools
        self.tool_drawline = SectionFromDrawTool(self.iface.mapCanvas())
        self.envRB = QgsRubberBand(self.canvas, QGis.Polygon)
        self.sectionRB = QgsRubberBand(self.canvas, QGis.Line)
        
        #connect GUI with variables
        self.ledSecName.textChanged.connect(lambda: self.setVars("name", self.ledSecName.text()))
        self.ledOriginX.textChanged.connect(lambda: self.setVars("originX", self.ledOriginX.text()))
        self.ledOriginY.textChanged.connect(lambda: self.setVars("originY", self.ledOriginY.text()))
        self.ledAzi.textChanged.connect(lambda: self.setVars("azi", self.ledAzi.text()))
        self.ledEnv.textChanged.connect(lambda: self.setVars("Env", self.ledEnv.text()))
        self.ledSecLength.textChanged.connect(lambda: self.setVars("seclength", self.ledSecLength.text()))
        self.ledDem.textChanged.connect(lambda: self.setVars("DEM", self.ledDem.text()))
        self.chkUseEnv.toggled.connect(self.setEnvelope)
        
        #populate lists
        self.populateDHloglist()
        
        #listen for signals
        self.tool_drawline.calcDone.connect(self.updateFromDraw)
        self.ledEnv.textChanged.connect(self.showEnvelope)
        self.ledOriginX.textChanged.connect(self.showEnvelope)
        self.ledOriginY.textChanged.connect(self.showEnvelope)
        self.ledAzi.textChanged.connect(self.showEnvelope)
        self.ledSecLength.textChanged.connect(self.showEnvelope)
        
        self.buttonBox.rejected.connect(lambda: self.canvas.scene().removeItem(self.envRB))  #clean up rubber bands on close
        self.buttonBox.rejected.connect(lambda: self.canvas.scene().removeItem(self.sectionRB))
        
    def setVars(self, target, value):
        try:
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
                self.secLength = float(value)
            elif target == "DEM":
                self.demPath = value
        except ValueError:
            pass
    def setEnvelope(self, value):
        self.useEnvelope = value
        
    def subsetDrillholes(self):
        #create the subset of drill XYZ to plot
        #pull Collar names from the selection list
        templist = []    
        for i in xrange(self.lstSelDH.count()):
            templist.append(self.lstSelDH.item(i).text())
        #flush out drillhole dictionary
        self.holes2plotXYZ={}
        #read in subset to be plotted to dictionary
        for DH in templist:
            self.holes2plotXYZ[DH]= QDrillerDialog.datastore.drillholesXYZ[DH]
    
    def createEnvelope(self):
        #define envelope - consider having this in a function of its own that can be called and display envelope
        # as a preveiw in the main canvas
        razi = math.radians(self.secAzi)
        raziminus = math.radians(self.secAzi - 90)
        raziplus = math.radians(self.secAzi + 90)
        
        Ex = self.originX + math.sin(razi) * self.secLength
        Ey = self.originY + math.cos(razi) * self.secLength

        Ax = self.originX + math.sin(raziminus) * self.envWidth
        Ay= self.originY + math.cos(raziminus) * self.envWidth

        Bx = self.originX + math.sin(raziplus) * self.envWidth
        By= self.originY + math.cos(raziplus) * self.envWidth

        Cx = Ex + math.sin(raziplus) * self.envWidth
        Cy= Ey + math.cos(raziplus) * self.envWidth

        Dx = Ex + math.sin(raziminus) * self.envWidth
        Dy= Ey + math.cos(raziminus) * self.envWidth
        
        coords = [[[Ax,Ay],[Bx,By],[Cx,Cy],[Dx,Dy]],[self.originX, self.originY],[Ex,Ey]]
        
  
        return coords
    def showEnvelope(self):
        #check that all required info is present
        if self.originX is None:
            return
        if self.originY is None:
            return
        if self.secAzi is None:
            return
        if self.secLength is None:
            return
        if self.envWidth is None:
            return
            
        coords = self.createEnvelope()
        
        self.envRB.reset(QGis.Polygon)
        self.sectionRB.reset(QGis.Line)
        
        self.envRB.setBorderColor(QtCore.Qt.red)
        self.sectionRB.setColor(QtCore.Qt.red)
        self.sectionRB.setWidth(1)

        for c in coords[0]:
            point = QgsPoint(c[0], c[1])
            geom = QgsGeometry.fromPoint(point)
            self.envRB.addPoint(point, True)
            
        self.sectionRB.addPoint(QgsPoint(coords[1][0], coords[1][1]), False)
        self.sectionRB.addPoint(QgsPoint(coords[2][0], coords[2][1]), True)
        
        self.sectionRB.show()
        self.envRB.show()
        
    def filterHoles(self):
        #function to filter the available holes to that within the envelope and set the selected drillholes to this
        """
        #try clearing any previous instance of the envelope layer this is only necessary if it is being added to the 
        #map registry here
        testlyr = QgsMapLayerRegistry.instance().mapLayersByName("temp Envelope")
        
        if len(testlyr)>0:
            for lyr in testlyr:
                QgsMapLayerRegistry.instance().removeMapLayer(lyr.id())"""
        #define envelope 
        eCoords = self.createEnvelope()
        
        uri = "polygon?crs={}".format(QDrillerDialog.datastore.projectCRS.authid())
        envLayer = QgsVectorLayer(uri, "temp Envelope", "memory")
        pr = envLayer.dataProvider()
        
        points = []

        for c in eCoords[0]:
            point = QgsPoint(c[0], c[1])
            geom = QgsGeometry.fromPoint(point)
            points.append(point)
    

        feat = QgsFeature()
        penvelope = QgsGeometry.fromPolygon([points])
        feat.setGeometry(penvelope)
                    
        pr.addFeatures([feat])
        #QgsMapLayerRegistry.instance().addMapLayer(envelope) #mainly for debug
        
        #access drill trace file- generate if not done already- dont forget to add to the list of files if generated from here
        #or consider generating it dynamically again?
        tracelayerpath = os.path.normpath(r"{}\{}_traces_P.shp".format(QDrillerDialog.datastore.projectdir, QDrillerDialog.datastore.projectname))
        traceLayer = QgsVectorLayer(tracelayerpath, "traces", 'ogr')
        
        if not traceLayer.isValid():
            print "layer from shape file and path invalid"
            QDrillerDialog.datastore.createPlanTrace()
            traceLayer = QgsVectorLayer(tracelayerpath, "traces", 'ogr')
        else:
            #perform intersection and create list of drillhole ID's
            enviter = envLayer.getFeatures()
            traceiter = traceLayer.getFeatures()
            intersectionTraces = []

            for env in enviter:
                penv = env.geometry()
                #check if collars fall inside
                        
                for trace in traceiter:
                    gtrace = trace.geometry()
                    trace.attribute("HoleID")
                    if gtrace.intersects(penv):
                        intersectionTraces.append(trace.attribute("HoleID"))
                        print "trace added", trace.attribute("HoleID") 
        
        #reset selected list so only holes picked up by the filter will populate it
        #for i in xrange(self.lstSelDH.count()):
        #the for loop is not used because it doesnt keep up with the row number changes as items are removed
        #resulting in some being left behind
        while self.lstSelDH.count()>0:
            self.lstAvailDH.addItem(self.lstSelDH.takeItem(0))
            
        #send list to the selected drillholes list in the gui
        for holes in intersectionTraces:
        #this is not right need to look into
            isavail = self.lstAvailDH.findItems(holes, QtCore.Qt.MatchExactly)
            if len(isavail) >0:
                print "is avail", holes
                self.lstSelDH.addItem(self.lstAvailDH.takeItem(
                                    self.lstAvailDH.row(isavail[0]))
                                    )
            trash = None
        
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

        for item in self.lstAvailLogs.selectedItems():
            self.lstSelLogs.addItem(self.lstAvailLogs.takeItem(self.lstAvailLogs.row(item)))
       
    def remDHLog(self):

        for item in self.lstSelLogs.selectedItems():
            self.lstAvailLogs.addItem(self.lstSelLogs.takeItem(self.lstSelLogs.row(item)))
            
    def addDH(self):

        for item in self.lstAvailDH.selectedItems():
            self.lstSelDH.addItem(self.lstAvailDH.takeItem(self.lstAvailDH.row(item)))
        
    def remDH(self):
    
        for item in self.lstSelDH.selectedItems():
            self.lstAvailDH.addItem(self.lstSelDH.takeItem(self.lstSelDH.row(item)))

    def drawSectionLine(self):
        self.iface.mapCanvas().setMapTool(self.tool_drawline)
        
    def updateFromDraw(self):
        #deactivate the drawing tool
        self.iface.actionPan().trigger()
        #refocus window
        self.activateWindow()
        #update all the variables
        self.ledOriginX.setText(str(round(self.tool_drawline.origX,0)))
        self.ledOriginY.setText(str(round(self.tool_drawline.origY,0)))
        self.ledAzi.setText(str(round(self.tool_drawline.azi,0)))
        self.ledSecLength.setText(str(round(self.tool_drawline.length, 0)))
        
        self.showEnvelope()
        
    def fromSelectedLine (self):
        #generate section parameters from currently selected linecache
        acLayer = self.iface.activeLayer()
        if acLayer.geometryType() != 1:
            self.messageBar.pushMessage("must be a line")
        elif acLayer.selectedFeatureCount() != 1:
            self.messageBar.pushMessage("please select 1 line feature")
        else:
            feats = acLayer.selectedFeatures()
            feat = feats[0]
            geom = feat.geometry()
            start = geom.vertexAt(0)
            end = geom.vertexAt(1)
            self. ledAzi.setText(str(round(start.azimuth(end), 0)))
            self.ledSecLength.setText(str(round(math.sqrt(start.sqrDist(end)),0)))
            self.ledOriginX.setText(str(round(start.x())))
            self.ledOriginY.setText(str(round(start.y())))
            
        self.showEnvelope()
            
    def generateSection(self):
              
        if self.secName is None:
            self.messageBar.pushMessage("Must have a Section Name")
            return
            
        newdir = os.path.normpath(r"{}\{}".format(
                                        QDrillerDialog.datastore.projectdir,self.secName,)
                                )
        if os.path.isdir(newdir):
            self.messageBar.pushMessage("Section already Exists")
            return
        if self.originX is None:
            self.messageBar.pushMessage("Section Location Missing Parameters")
            return
        if self.originY is None:
            self.messageBar.pushMessage("Section Location Missing Parameters")
            return
        if self.secAzi is None:
            self.messageBar.pushMessage("Section Location Missing Parameters")
            return
        if self.secLength is None:
            self.messageBar.pushMessage("Section Location Missing Parameters")
            return
        if self.envWidth is None:
            self.messageBar.pushMessage("Section Location Missing Parameters")
            return
        if self.lstSelDH.count() == 0:
            self.messageBar.pushMessage("No Drillholes have been Selected")
            return
        print "dem checkbox", self.chkDem.isChecked
        if self.chkDem.isChecked(): 
            if self.demPath is None:
                self.messageBar.pushMessage("No DEM has been Selected")
                return
        #run the methods to draw the files
        self.subsetDrillholes()
        #create drill traces
        sectionLayers=[]
        outputlayer = os.path.normpath(r"{}\{}\{}_traces_S.shp".format(
                                        QDrillerDialog.datastore.projectdir,self.secName,
                                        QDrillerDialog.datastore.projectname)
                                        )
        #create directory to store the relevant section files
        sectiondirectory = os.path.dirname(outputlayer)
        try: 
            os.makedirs(sectiondirectory)
        except OSError:
            if not os.path.isdir(sectiondirectory):
                raise
                
        #create drill traces
        secplane = [self.originX, self.originY, self.secAzi]
        QDUtils.writeTraceLayer(self.holes2plotXYZ, outputlayer, useEnvelope=self.useEnvelope,
                                envelope=self.envWidth, plan=False, sectionplane=secplane, 
                                loadcanvas=False, crs=self.crs)

        # collect info for writing to section definition file
        sectionLayers.append(outputlayer)
        
        #create downhole logs
        #Pull the desired downhole logs
        logtargetDict = {}
        for i in xrange(self.lstSelLogs.count()):
            name = self.lstSelLogs.item(i).text()
            logtargetDict[name] = self.availLogs[name] 
        
        #code to generate log 
        for k in logtargetDict:
            
            logname = k
            logtarget = logtargetDict[k]
            outputlayer = os.path.normpath("{}\\{}\\{}_{}_S.shp".format(QDrillerDialog.datastore.projectdir,
                                            self.secName, QDrillerDialog.datastore.projectname, logname)
                                            )

            secplane = [self.originX, self.originY, self.secAzi]
            
            QDUtils.LogDrawer(self.holes2plotXYZ, logtarget, outputlayer, plan=False,
                                useEnvelope=self.useEnvelope, envelope=self.envWidth,
                                sectionplane=secplane, crs=self.crs, loadcanvas=False)
            
            sectionLayers.append(outputlayer)
        
        if self.secAzi > 90:
            secFacing = self.secAzi - 90
        else:
            secFacing = (self.secAzi +360) - 90
            
        #create surface profile if requested
        if self.chkDem.isChecked():
            outputlayer = os.path.normpath(r"{}\{}\{}_DEM.shp".format(
                                        QDrillerDialog.datastore.projectdir,self.secName,
                                        QDrillerDialog.datastore.projectname)
                                        )
            rlayer = QgsRasterLayer(self.demPath, "DEM")
            QDUtils.ProfileFromRaster(self.originX, self.originY, self.secAzi, self.secLength, rlayer, outputlayer)
            sectionLayers.append(outputlayer)
            
        # write to section definition file
        secDef= ET.Element("sectionDefinition", {"name":self.secName})
        for lyrs in sectionLayers:
            ET.SubElement(secDef, "layer").text = lyrs
        ET.SubElement(secDef, "originX").text = str(self.originX)
        ET.SubElement(secDef, "originY").text = str(self.originY)
        ET.SubElement(secDef, "secAzi").text = str(self.secAzi)
        ET.SubElement(secDef, "secLength").text = str(self.secLength)
        ET.SubElement(secDef, "envelope").text = str(self.envWidth)
        ET.SubElement(secDef, "DEM").text = str(self.demPath)
        ET.SubElement(secDef, "facing").text = str(self.secFacing)
        #may need to include info on other raster layers used for profiles or as images
        
        #create path for section definition file
        secDefPath = os.path.normpath("{}\\{}.qdsd".format(os.path.dirname(outputlayer),self.secName))
        #write definition to file in xml format
        tree = ET.ElementTree(secDef)
        tree.write(secDefPath)
        #send infomation to the datastore about the created section
        QDrillerDialog.datastore.availSectionDict[self.secName]= secDefPath  #could this be set up with signals instead
        #relaod the sections in SectionView
        self.sectionGenerated.emit()
        self.ledSecName.setText("")
        self.secName = None
        QDrillerDialog.datastore.saveProjectData()
        
        
    def showRasterFileBrowser(self):
        #still to implement
             
        lastUsedFilter = gTools.FileFilter.lastUsedRasterFilter()
        inputFile = gTools.FileDialog.getOpenFileName(self, self.tr( "Select DEM" ), gTools.FileFilter.allRastersFilter(), lastUsedFilter )
        if not inputFile:
            return
        gTools.FileFilter.setLastUsedRasterFilter(lastUsedFilter)
        
        self.ledDem.setText(inputFile)
        
    def printout(self):
        print "deactivated signal triggered"
        
    def closeEvent(self, event):
    #clean up rubber bands on close
        self.canvas.scene().removeItem(self.envRB)
        self.canvas.scene().removeItem(self.sectionRB)

MAN_FORM_CLASS, _ = uic.loadUiType(os.path.join(
os.path.dirname(__file__), 'managesections_dialog_base.ui'))

class SectionManager(QtGui.QDialog, MAN_FORM_CLASS):
    sectionDeleted = QtCore.pyqtSignal()
    def __init__(self, parent=None):
        """Constructor."""
        super(SectionManager, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)  
        
        self.messageBar = QgsMessageBar()
        self.lytMessage.addWidget(self.messageBar)
        #connect buttons    
        self.btnDelete.clicked.connect(self.delSection)
        self.btnDeleteLayer.clicked.connect(self.delLayer)
        self.popList()
        
    def popList(self):
        """
        self.lstSections.clear()
        for sections in QDrillerDialog.datastore.availSectionDict:
            self.lstSections.addItem(sections)
        """
        self.treeSections.clear()
        #get all sections in project
        for section in QDrillerDialog.datastore.availSectionDict:
            #open the sec def file
            defpath = QDrillerDialog.datastore.availSectionDict[section]
            secdeftree = ET.parse(defpath)
            defroot = secdeftree.getroot()
            treeSec = QTreeWidgetItem(self.treeSections)
            treeSec.setText(0, section)
            for lyrs in defroot.findall("layer"):
                #print lyrs
                #print lyrs.text()
                lname =os.path.splitext(os.path.basename(lyrs.text))[0]
                treeSecLayer = QTreeWidgetItem(treeSec)
                treeSecLayer.setText(0, lname)
                
    def delLayer(self):
        #get selected layers and delete them
        for item in self.treeSections.selectedItems():
            layername = item.text(0)
            sectionname = item.parent().text(0)
            sectionpath = QDrillerDialog.datastore.availSectionDict[sectionname] #path to the secdef file
            sectiondir = os.path.dirname(sectionpath)
            layerpath = os.path.normpath("{}\\{}.shp".format(sectiondir, layername))
            #remove file from registry
            ltoclose = QgsMapLayerRegistry.instance().mapLayersByName(layername)
            layerstoclose = []
            for i in ltoclose:
                layerstoclose.append(i.id())
            QgsMapLayerRegistry.instance().removeMapLayers(layerstoclose)
            #delete the shapefile
            QgsVectorFileWriter.deleteShapeFile(layerpath)
            #remove reference in section definition file
            secdeftree = ET.parse(sectionpath)
            defroot = secdeftree.getroot()
            for lyrs in defroot.findall("layer"):
                if lyrs.text == layerpath:
                    defroot.remove(lyrs)
            secdeftree.write(sectionpath)
            #refresh list, send message and refresh SectionView
            self.popList()
            QDrillerDialog.datastore.saveProjectData()
            msg = " Layer {} has been removed from Section {} and project saved".format(layername, sectionname)
            self.messageBar.pushMessage(msg)
            self.sectionDeleted.emit()
            
    def delSection(self):
        for item in self.treeSections.selectedItems():
            defpath = QDrillerDialog.datastore.availSectionDict[item.text(0)]
            
            tree = ET.parse(defpath)
            dfn = tree.getroot()
            #pull all the layer paths from the definition file
            layerlist = []
            for lyrs in dfn.findall("layer"):
                layerlist.append(lyrs.text)
            
            #Remove layers from registry
            layerstoclose = []
            for lyr in layerlist:
                lname =os.path.splitext(os.path.basename(lyr))[0]
                ltoclose = QgsMapLayerRegistry.instance().mapLayersByName(lname)
                for i in ltoclose:
                    layerstoclose.append(i.id())
                        
            QgsMapLayerRegistry.instance().removeMapLayers(layerstoclose)
            dirtodel = os.path.dirname(defpath)
            shutil.rmtree(dirtodel)
            #remove from section dictionary
            del QDrillerDialog.datastore.availSectionDict[item.text()]
            self.popList()
            QDrillerDialog.datastore.saveProjectData()
            msg = " Section {} has been removed and project saved".format(lname)
            self.messageBar.pushMessage(msg)
            self.sectionDeleted.emit()
                       
class SVMenuProvider(QgsLayerTreeViewMenuProvider):
    def __init__(self, view, iface):
        QgsLayerTreeViewMenuProvider.__init__(self)
        self.view = view
        self.defaultactions = QgsLayerTreeViewDefaultActions(self.view)
        self.iface = iface
    def createContextMenu(self):
        if not self.view.currentLayer():
            return None
        
        m = QMenu()
        m.addAction("Properties", self.showProperties)
        m.addAction("Remove Layer", self.removeLayer)
        m.addAction("Show Feature Count", self.featureCount)
        m.addAction("Zoom to Layer", self.zoomtoLayer)
        m.addAction("Attribute Table",self.showAttributes)
        return m

    def zoomtoLayer(self):
        print "show extent menu button hit"
        self.defaultactions.zoomToLayer(QDrillerDialog.sectionview.sectionCanvas)
        
    def featureCount(self):
        self.defaultactions.showFeatureCount()
        
    def removeLayer(self):
        self.defaultactions.removeGroupOrLayer()
        
    def showProperties(self):
        self.iface.showLayerProperties(self.view.currentLayer())
        
    def showAttributes(self):
        self.iface.showAttributeTable(self.view.currentLayer())

class IdentifyTool(QgsMapToolIdentify):
    def __init__(self, canvas, treewidget):
        self.canvas = canvas
        self.treewidget = treewidget
        self.treewidget.clear()

        QgsMapToolIdentify.__init__(self, canvas)
    
    def canvasReleaseEvent(self, mouseEvent):
        results = self.identify(mouseEvent.x(), mouseEvent.y(), self.LayerSelection)
        print "feature identify click"
        print "results", results[0].mLayer, results[0].mFields, results[0].mFeature
    
        #build a tree to display
        resDict = {}
        for result in results:
            lyrname = result.mLayer.name()
            
            if resDict.has_key(lyrname):
                olist = resDict[lyrname]
                olist.append(result)
                resDict[lyrname] = olist
            else:
                resDict[lyrname] = [result]
            
        self.treewidget.clear()
        for lyr in resDict:
            treeLayer = QTreeWidgetItem(self.treewidget)
            treeLayer.setText(0,lyr)
            treeLayer.setExpanded(True)
            for res in resDict[lyr]:
                fet = res.mFeature
                fld = fet.fields().toList()
                featres = QTreeWidgetItem(treeLayer)
                featres.setText(0, fet.attribute(fld[0].name()))
                for f in fld:
                    fname = f.name()
                    attr = fet.attribute(fname)
                    featdata = QTreeWidgetItem(featres)
                    featdata.setText(0, fname)
                    featdata.setText(1, str(attr))
                    print "layer :{}, Feature:{}, Attrib:{}:{}".format(lyr, fet.id(), fname, attr)
    
class SectionFromDrawTool(QgsMapToolEmitPoint):
    calcDone = QtCore.pyqtSignal()
    def __init__(self, canvas):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, canvas)
        self.rubberBand = QgsRubberBand(canvas, QGis.Line)
        self.rubberBand.setColor(QtCore.Qt.red)
        self.rubberBand.setWidth(1)
        
        self.origX = None
        self.origY = None
        self.azi = None
        self.length = None
        self.points = []
        self.reset()
        
    def reset(self):
        self.startPoint = self.endPoint = None
        self.isEmittingPoint = False
        self.rubberBand.reset(QGis.Line)
        
    def canvasPressEvent(self, mouseEvent):
        self.startPoint = self.toMapCoordinates(mouseEvent.pos())
        self.isEmittingPoint = True
        
    def canvasReleaseEvent(self, mouseEvent):
        self.endPoint = self.toMapCoordinates(mouseEvent.pos())
        self.isEmittingPoint = False
        self.calculateExtents()
       
    def canvasMoveEvent(self, e):
        if not self.isEmittingPoint:
            return
        self.endPoint = self.toMapCoordinates(e.pos())
        self.showLine(self.startPoint, self.endPoint)
    
    def showLine(self, start, end):
        self.rubberBand.reset(QGis.Line)
        self.rubberBand.addPoint(self.startPoint, False)
        self.rubberBand.addPoint(self.endPoint, True)
        self.rubberBand.show()
        
    def calculateExtents(self):
        self.origX = self.startPoint.x()
        self.origY = self.startPoint.y()
        self.azi = self.startPoint.azimuth(self.endPoint)
        self.length = math.sqrt(self.startPoint.sqrDist(self.endPoint))
        self.calcDone.emit()
        
    def deactivate(self):
        self.canvas.scene().removeItem(self.rubberBand)
        QgsMapTool.deactivate(self)
        self.deactivated.emit()
        
class MeasureLineTool(QgsMapToolEmitPoint):
    dialogOpened = QtCore.pyqtSignal()
    def __init__(self, canvas, seg, total, list):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, canvas)
        self.rubberBand = QgsRubberBand(canvas, QGis.Line)
        self.rubberBand.setColor(QtCore.Qt.red)
        self.rubberBand.setWidth(1)
        
        self.origX = None
        self.origY = None
        self.length = None
        self.totalLength = None
        self.points = []
        self.isEmittingPoint = False
        self.seg = seg
        self.total = total
        self.list = list
    
      
    def reset(self):
        self.startPoint = self.endPoint = None
        self.points = []
        self.isEmittingPoint = False
        self.rubberBand.reset(QGis.Line)
        self.list.clear()
        self.seg.clear()
        self.total.clear()
        
    def canvasPressEvent(self, mouseEvent):
        if mouseEvent.button() == QtCore.Qt.RightButton:
            print "condition 1"
           
            self.endPoint = self.toMapCoordinates(mouseEvent.pos())
            self.seg.setText(self.formatText(self.calculateSeg()))
            self.list.addItem(self.formatText(self.calculateSeg()))
            self.showLine()
            self.isEmittingPoint = False
            
            
        elif not self.isEmittingPoint:
            print "condition 2"
            self.reset()
            self.startPoint = self.endPoint = self.toMapCoordinates(mouseEvent.pos())
            self.seg.setText(self.formatText(self.calculateSeg()))
            self.isEmittingPoint = True
            self.points.append(self.startPoint)
            
        else:
            print "condition 3"
            self.list.addItem(self.formatText(self.calculateSeg()))
            self.startPoint = self.toMapCoordinates(mouseEvent.pos())
            self.seg.setText(self.formatText(self.calculateSeg()))
            self.isEmittingPoint = True
            self.points.append(self.startPoint)
            self.showLine()
            
    def canvasMoveEvent(self, e):
        if not self.isEmittingPoint:
            return
        self.endPoint = self.toMapCoordinates(e.pos())
        self.seg.setText(self.formatText(self.calculateSeg()))
        self.showLine()
        self.total.setText(self.formatText(self.calculateTotal()))
        
    def showLine(self):
        self.rubberBand.reset(QGis.Line)
        for point in self.points:
            self.rubberBand.addPoint(point, False)
        self.rubberBand.addPoint(self.endPoint, True)
        self.rubberBand.show()
        
    def calculateSeg(self):
        #current leg
        length = math.sqrt(self.startPoint.sqrDist(self.endPoint))
        return length
        
    def calculateTotal(self):
        #total length
        geom = self.rubberBand.asGeometry()
        totalLength = geom.length()
        return totalLength
      
    def formatText(self, input):
        if input <10:
            text = "{}m".format(round(input, 1))
        elif input <10000:
            text = "{}m".format(round(input, 0))
        elif input >10000:
            text = "{}km".format(round((input / 1000), 3))
            
        return text
        
    def deactivate(self):
        #self.canvas.scene().removeItem(self.rubberBand)
        self.reset()
        QgsMapTool.deactivate(self)
        self.deactivated.emit()
        
class MeasureAreaTool(QgsMapToolEmitPoint):
    dialogOpened = QtCore.pyqtSignal()
    def __init__(self, canvas, total):
        self.canvas = canvas
        QgsMapToolEmitPoint.__init__(self, canvas)
        self.rubberBand = QgsRubberBand(canvas, QGis.Polygon)
        self.rubberBand.setBorderColor(QtCore.Qt.red)
        
        
        self.origX = None
        self.origY = None
        self.area = None
        self.points = []
        self.isEmittingPoint = False
        self.total = total
    
    def reset(self):
        self.startPoint = self.endPoint = None
        self.points = []
        self.isEmittingPoint = False
        self.rubberBand.reset(QGis.Polygon)
        self.total.clear()
        
    def canvasPressEvent(self, mouseEvent):
        if mouseEvent.button() == QtCore.Qt.RightButton:
            self.endPoint = self.toMapCoordinates(mouseEvent.pos())
            self.total.setText(self.formatText(self.calculateTotal()))
            self.showLine()
            self.isEmittingPoint = False
            
            
        elif not self.isEmittingPoint:
            self.reset()
            self.startPoint = self.endPoint = self.toMapCoordinates(mouseEvent.pos())
            #self.seg.setText(self.formatText(self.calculateSeg()))
            self.isEmittingPoint = True
            self.points.append(self.startPoint)
            
        else:
            self.startPoint = self.toMapCoordinates(mouseEvent.pos())
            #self.seg.setText(self.formatText(self.calculateSeg()))
            self.isEmittingPoint = True
            self.points.append(self.startPoint)
            self.showLine()
            
    def canvasMoveEvent(self, e):
        if not self.isEmittingPoint:
            return
        self.endPoint = self.toMapCoordinates(e.pos())
        self.showLine()
        self.total.setText(self.formatText(self.calculateTotal()))
        
    def showLine(self):
        self.rubberBand.reset(QGis.Polygon)
        for point in self.points:
            self.rubberBand.addPoint(point, False)
        self.rubberBand.addPoint(self.endPoint, True)
        self.rubberBand.show()
           
    def calculateTotal(self):
        #total length
        geom = self.rubberBand.asGeometry()
        if not geom is None:
            area = geom.area()
            return area
        else:
            return 0
      
    def formatText(self, input):
        if input <100:
            text = "{}sqm".format(round(input, 1))
        elif input <20000:
            text = "{}sqm".format(round((input), 0))
        elif input <500000:
            text = "{}ha".format(round((input / 10000), 1))
        elif input >500000:
            text = "{}sqkm".format(round((input / 1000000), 3))
            
        return text
        
    def deactivate(self):
        self.reset()
        #self.canvas.scene().removeItem(self.rubberBand)
        QgsMapTool.deactivate(self)
        self.deactivated.emit()
        
class AddNewPointFeature(QgsMapToolEmitPoint):
    def __init__(self, canvas, layer):
        QgsMapToolEmitPoint.__init__(self, canvas)
        self.canvas = canvas
        self.layer = layer
        self.provider = self.layer.dataProvider()
        self.fields = self.provider.fields()
        self.buffer = self.layer.editBuffer()
        #connect signal to restart buffer if edits are saved while tool is active
        self.layer.editingStarted.connect(self.restartBuffer)
        #initialise parameters
        
    def isEditTool(self):
        #overridden mapTool function to identify this as an editing tool
        return True
            
    def toolName(self):
        return "AddPointFeature"
        
    def restartBuffer(self):
        self.buffer = self.layer.editBuffer()
        
    def canvasPressEvent(self, mouseEvent):
        point = self.toMapCoordinates(mouseEvent.pos())
        feat = QgsFeature(self.fields)
        geom = QgsGeometry.fromPoint(point)
        feat.setGeometry(geom)
        self.buffer.addFeature(feat)
        self.layer.triggerRepaint()
        
    def deactivate(self):
        print "point add tool deactivated"
        QgsMapTool.deactivate(self)

class AddNewPolyFeature(QgsMapToolEmitPoint):
    #add new polyline or polygon feature
    def __init__(self, canvas, layer, geometryType):
        QgsMapToolEmitPoint.__init__(self, canvas)
        self.canvas = canvas
        self.layer = layer
        self.geometryType = geometryType
        self.provider = self.layer.dataProvider()
        self.fields = self.provider.fields()
        self.buffer = self.layer.editBuffer()
        #self.buffer.layerModified.connect(self.layer.triggerRepaint)
        #connect signal to restart buffer if edits are saved while tool is active
        self.layer.editingStarted.connect(self.restartBuffer)
        #initialise parameters
        if self.geometryType == "Line":
            self.rubberBand = QgsRubberBand(canvas, QGis.Line)
            self.rubberBand.setColor(QtCore.Qt.red)
        elif self.geometryType == "Polygon":
            self.rubberBand = QgsRubberBand(canvas, QGis.Polygon)
            self.rubberBand.setBorderColor(QtCore.Qt.red)
            self.rubberBand.setWidth(1)
            
        self.points = []
        self.endPoint = None
        self.isEmittingPoint = False
        
    def isEditTool(self):
        #overridden mapTool function to identify this as an editing tool
        return True
        
    def toolName(self):
        return "AddPolyFeature"
        
    def reset(self):
        self.points = []
        self.endPoint = None
        self.isEmittingPoint = False
        if self.geometryType == "Line":
            self.rubberBand.reset(QGis.Line)
        elif self.geometryType == "Polygon":
            self.rubberBand.reset(QGis.Polygon)
            
    def restartBuffer(self):
        self.buffer = self.layer.editBuffer()
        
    def keyPressEvent(self, keyEvent):
        #Use Backspace to remove the last added nodeType    
        print keyEvent
        if keyEvent.key() == QtCore.Qt.Key_Backspace:
            self.points.pop()
            self.showBand()
        #Use escape key to cancel current feature 
        if keyEvent.key() == QtCore.Qt.Key_Escape:
            self.reset()
            
    def canvasPressEvent(self, mouseEvent):
        if mouseEvent.button() == QtCore.Qt.RightButton:
            self.addFeature()
            self.isEmittingPoint = False
            self.reset()
            
        elif not self.isEmittingPoint:
            self.isEmittingPoint = True
            self.points.append(self.toMapCoordinates(mouseEvent.pos()))
            
        else:
            self.isEmittingPoint = True
            self.points.append(self.toMapCoordinates(mouseEvent.pos()))
            self.showBand()
            
    def canvasMoveEvent(self, e):
        if not self.isEmittingPoint:
            return
        self.endPoint = self.toMapCoordinates(e.pos())
        self.showBand(fromCursor=True)
        
    def showBand(self, fromCursor=False):
        if self.geometryType == "Line":
            self.rubberBand.reset(QGis.Line)
        elif self.geometryType == "Polygon":
            self.rubberBand.reset(QGis.Polygon)
        for point in self.points:
            self.rubberBand.addPoint(point, True) #was false
        if fromCursor == True:
            self.rubberBand.addPoint(self.endPoint, True)
        self.rubberBand.show()
    
    def addFeature(self):
        feat = QgsFeature(self.fields)
        print feat.isValid()
        if self.geometryType == "Line":
            geom = QgsGeometry.fromPolyline(self.points)
            print geom.isGeosValid()
        elif self.geometryType == "Polygon":
            geom = QgsGeometry.fromPolygon([self.points])
            print geom.isGeosValid()
        feat.setGeometry(geom)
        print feat.isValid()
        addfeat = self.buffer.addFeature(feat)
        print "addfeat", addfeat
        self.layer.triggerRepaint()
        
    def deactivate(self):
        self.reset()
        print "poly add tool deactivated"
        #self.canvas.scene().removeItem(self.rubberBand)
        QgsMapTool.deactivate(self)
        
class MoveFeatureTool(QgsMapToolEmitPoint):
    #tool to move the selected feature in a click and drag fashion
    def __init__(self, canvas, layer):
        QgsMapToolEmitPoint.__init__(self, canvas)
        self.canvas = canvas
        self.layer = layer
        self.startpoint= None
        self.endpoint = None
        self.selFeat = None
        self.emitting = False
        self.multiselect = False
        self.buffer = self.layer.editBuffer()
        #connect signal to restart buffer if edits are saved while tool is active
        self.layer.editingStarted.connect(self.restartBuffer)
        if self.layer.geometryType() == QGis.Line:
            self.rubberBand = QgsRubberBand(canvas, QGis.Line)
            self.rubberBand.setColor(QtCore.Qt.red)
        elif self.layer.geometryType() == QGis.Polygon:
            self.rubberBand = QgsRubberBand(canvas, QGis.Polygon)
            self.rubberBand.setBorderColor(QtCore.Qt.red)
            self.rubberBand.setWidth(1)
        elif self.layer.geometryType() == QGis.Point:
            self.rubberBand = QgsRubberBand(canvas, QGis.Point)
            self.rubberBand.setColor(QtCore.Qt.red)

    def isEditTool(self):
        #overridden mapTool function to identify this as an editing tool
        return True
        
    def toolName(self):
        return "Move Feature"
        
    def reset(self):
        #reset parameters to allow for next move
        if self.layer.geometryType() == QGis.Line:
            self.rubberBand.reset(QGis.Line)
        elif self.layer.geometryType() == QGis.Polygon:
            self.rubberBand.reset(QGis.Polygon)
        elif self.layer.geometryType() == QGis.Point:
            self.rubberBand.reset(QGis.Point)
        self.startpoint= None
        self.endpoint = None
        self.selFeat = None
        self.emitting = False

    def restartBuffer(self):
        self.buffer = self.layer.editBuffer()
        
    def canvasPressEvent(self, mouseEvent):
        #select the desired feature
        #get the mouse coordinates, also store these
        
        self.startpoint = self.toMapCoordinates(mouseEvent.pos())
        #convert coordinates into search box
        radius = self.searchRadiusMU(self.canvas)
        p1 = QgsPoint(self.startpoint.x()-radius, self.startpoint.y()-radius)
        p2 = QgsPoint(self.startpoint.x()+radius, self.startpoint.y()+radius)
        searchbox = self.toLayerCoordinates(self.layer, QgsRectangle(p1,p2))
        #select feature within search box, also stor the features geometry
        self.layer.select(searchbox, False) #False means only one feature can be selected at a time
        self.selFeat = self.layer.selectedFeatures()
        if not self.multiselect:
            self.emitting = True
    def canvasMoveEvent(self, mouseEvent):
        #create a rubberband to represent the feature while it is being moved
        if self.emitting:
            #get current cursor position
            currPoint = self.toMapCoordinates(mouseEvent.pos())
            transX = currPoint.x() - self.startpoint.x()
            transY = currPoint.y() - self.startpoint.y()
            
            for feat in self.selFeat:
                #create rubberband from geometry
                geom = feat.geometry()
                self.rubberBand.addGeometry(geom, self.layer)
            #apply translating to current position
            self.rubberBand.setTranslationOffset(transX, transY)
        
    def canvasReleaseEvent(self, mouseEvent):
        #perform the feature move using translate determined by start position and end position
        if not self.multiselect:
            #get current cursor location
            currPoint = self.toMapCoordinates(mouseEvent.pos())
            #calculate the translation from startpoint
            transX = currPoint.x() - self.startpoint.x()
            transY = currPoint.y() - self.startpoint.y()
            #performtranslation
            for feat in self.selFeat:
                geom = feat.geometry()
                geom.translate(transX, transY)
                self.buffer.changeGeometry(feat.id(), geom)
            #reset parameters ready for next move
            self.layer.removeSelection()
            self.layer.triggerRepaint()
            self.reset()
        
    def keyPressEvent(self, keyEvent):
        #Use the Escape key to cancel the action
        if keyEvent.key() == QtCore.Qt.Key_Escape:
            self.reset()
        #Use holding the control key down to allow multi selection
        if keyEvent.key() == QtCore.Qt.Key_Control:
            self.multiselect = True
    def keyReleaseEvent(self, keyEvent):
        if keyEvent.key() == QtCore.Qt.Key_Control:
            self.multiselect = False
    def deactivate(self):
        self.reset()
        print "move tool deactivated"
        #self.canvas.scene().removeItem(self.rubberBand)
        QgsMapTool.deactivate(self)
        
class NodeTool(QgsMapToolEmitPoint):
    def __init__(self, canvas, layer):
        QgsMapToolEmitPoint.__init__(self, canvas)
        self.canvas = canvas
        self.layer = layer
        self.startpoint= None
        self.selFeat = None
        self.targetgeom = None
        self.tarvert = None
        self.emitting = False
        self.buffer = self.layer.editBuffer()
        #connect signal to restart buffer if edits are saved while tool is active
        self.layer.editingStarted.connect(self.restartBuffer)
        if self.layer.geometryType() == QGis.Line:
            self.rubberBand = QgsRubberBand(canvas, QGis.Line)
            self.rubberBand.setColor(QtCore.Qt.red)
            self.rubberBand.setIcon(QgsRubberBand.ICON_BOX)
        elif self.layer.geometryType() == QGis.Polygon:
            self.rubberBand = QgsRubberBand(canvas, QGis.Polygon)
            self.rubberBand.setBorderColor(QtCore.Qt.red)
            self.rubberBand.setWidth(1)
            self.rubberBand.setIcon(QgsRubberBand.ICON_BOX)
        self.vertMarker = QgsVertexMarker(canvas)
        self.vertMarker.setIconType(QgsVertexMarker.ICON_BOX)
        self.vertMarker.setColor(QtCore.Qt.blue)

    def isEditTool(self):
        #overridden mapTool function to identify this as an editing tool
        return True
        
    def toolName(self):
        return "Node Tool"
        
    def reset(self):
        #reset parameters to allow for next move
        if self.layer.geometryType() == QGis.Line:
            self.rubberBand.reset(QGis.Line)
        elif self.layer.geometryType() == QGis.Polygon:
            self.rubberBand.reset(QGis.Polygon)

        self.startpoint= None
        self.selFeat = None
        self.emitting = False
        self.targetgeom = None
        self.tarvert = None
        #self.vertMarker.hide()

    def restartBuffer(self):
        self.buffer = self.layer.editBuffer()
        
    def canvasPressEvent(self, mouseEvent):
        #select vertex ready to move it
        if self.targetgeom is not None:
            currPoint = self.toMapCoordinates(mouseEvent.pos())
            #dist, self.tarvert = self.targetgeom.closestVertexWithContext(currPoint)
            vertp, self.tarvert, bvert, avert, dist = self.targetgeom.closestVertex(currPoint)
            try:
                if math.sqrt(dist) > self.searchRadiusMU(self.canvas):
                    self.tarvert = None
                    self.layer.removeSelection()
                    
                else:
                    #create a rubberband item for currently selected vertex
                    self.vertMarker.setCenter(self.targetgeom.vertexAt(self.tarvert))
                    self.emitting = True
            except ValueError:
                pass
        
    def canvasMoveEvent(self, mouseEvent):
        #update rubberband
        if self.emitting:
            currPoint = self.toLayerCoordinates(self.layer, self.toMapCoordinates(mouseEvent.pos()))
            self.targetgeom.moveVertex(currPoint.x(), currPoint.y(), self.tarvert)
            self.rubberBand.setToGeometry(self.targetgeom, self.layer)
            self.vertMarker.setCenter(self.targetgeom.vertexAt(self.tarvert))

            
    def canvasReleaseEvent(self, mouseEvent):
    #functionality dependent on whether tool is "emitting"
        if not self.emitting:
            #select a feature to edit
            self.reset()
            self.startpoint = self.toMapCoordinates(mouseEvent.pos())
            #convert coordinates into search box
            radius = self.searchRadiusMU(self.canvas)
            p1 = QgsPoint(self.startpoint.x()-radius, self.startpoint.y()-radius)
            p2 = QgsPoint(self.startpoint.x()+radius, self.startpoint.y()+radius)
            searchbox = self.toLayerCoordinates(self.layer, QgsRectangle(p1,p2))
            #select feature within search box
            self.layer.select(searchbox, False) #False means only one feature can be selected at a time
            featlist = self.layer.selectedFeatures()
            if featlist:
                self.selFeat = featlist[0]
                #create rubberband from geometry
                self.targetgeom = self.selFeat.geometry()
                self.rubberBand.addGeometry(self.targetgeom, self.layer)
                
        elif self.emitting:
            currPoint = self.toLayerCoordinates(self.layer, self.toMapCoordinates(mouseEvent.pos()))
            self.targetgeom.moveVertex(currPoint.x(), currPoint.y(), self.tarvert)
            self.buffer.changeGeometry(self.selFeat.id(), self.targetgeom)
            self.rubberBand.setToGeometry(self.targetgeom, self.layer)
            self.vertMarker.setCenter(self.targetgeom.vertexAt(self.tarvert))
            self.layer.triggerRepaint()
            self.emitting = False
            
    def canvasDoubleClickEvent(self, mouseEvent):
        #select vertex ready to move it
        currPoint = self.toMapCoordinates(mouseEvent.pos())
        dist, segPoint, afterVert = self.targetgeom.closestSegmentWithContext(currPoint)
        if math.sqrt(dist) > self.searchRadiusMU(self.canvas):
            self.tarvert = None
            
        else:
            self.targetgeom.insertVertex(segPoint.x(), segPoint.y(), afterVert)
            self.buffer.changeGeometry(self.selFeat.id(), self.targetgeom)
            self.rubberBand.setToGeometry(self.targetgeom, self.layer)
            self.vertMarker.setCenter(self.targetgeom.vertexAt(afterVert))
            self.layer.triggerRepaint()
            
    def keyPressEvent(self, keyEvent):
        if keyEvent.key() == QtCore.Qt.Key_Escape:
            self.reset()
            self.layer.removeSelection()
        #use backspace to remove vertex and select next vertex closer to origin
        if keyEvent.key() == QtCore.Qt.Key_Backspace and self.tarvert is not None:
            self.targetgeom.deleteVertex(self.tarvert)
            self.tarvert -= 1
            self.vertMarker.setCenter(self.targetgeom.vertexAt(self.tarvert))
            self.buffer.changeGeometry(self.selFeat.id(), self.targetgeom)
            self.rubberBand.setToGeometry(self.targetgeom, self.layer)
            self.layer.triggerRepaint()
        #use delete to remove vertex and select next vertex closest to the end
        if keyEvent.key() == QtCore.Qt.Key_Delete and self.tarvert is not None:
            self.targetgeom.deleteVertex(self.tarvert)
            self.vertMarker.setCenter(self.targetgeom.vertexAt(self.tarvert))
            self.buffer.changeGeometry(self.selFeat.id(), self.targetgeom)
            self.rubberBand.setToGeometry(self.targetgeom, self.layer)
            self.layer.triggerRepaint()

    def deactivate(self):
        self.reset()
        print "node tool deactivated"
        self.canvas.scene().removeItem(self.rubberBand)
        self.canvas.scene().removeItem(self.vertMarker)
        self.layer.removeSelection()
        QgsMapTool.deactivate(self)
    
class CanvasGrid:

    def __init__(self, canvas, xspace, yspace, rubberband):
        #get canvas extents
        extent = canvas.extent()
        xmin = extent.xMinimum()
        xmax = extent.xMaximum()
        ymin = extent.yMinimum()
        ymax = extent.yMaximum()
        
        #create memory layer to hold grid
        glayer = QgsVectorLayer("LineString?crs=epsg:4328", "grid", "memory")
        #gpr = glayer.dataProvider
        rubberband.reset(QGis.Line)
        #generate gridlines
        if float(xspace) > 0:
            xCo = self.rounder(xmin, float(xspace))
            #gridlist = []
            
            while xCo < xmax:
                geom = QgsGeometry.fromPolyline([QgsPoint(xCo, ymin), QgsPoint(xCo,ymax)])
                #feat = QgsFeature()
                #feat.setGeometry(geom)
                #gridlist.append(feat)
                rubberband.addGeometry(geom, glayer)
                xCo += float(xspace)
        if float(yspace) > 0:
            yCo = self.rounder(ymin, float(yspace))
            
            while yCo < ymax:
                geom = QgsGeometry.fromPolyline([QgsPoint(xmin, yCo), QgsPoint(xmax,yCo)])
                #feat = QgsFeature()
                #feat.setGeometry(geom)
                #gridlist.append(feat)
                rubberband.addGeometry(geom, glayer)
                yCo += float(yspace)
            
        #gpr.addFeatures(gridlist)
        
            
    def rounder(self, number, roundto):
        return (round(number / roundto) * roundto)
        
class ExportImage:
    #this is not working very well yet
    def __init__(self, canvas, maincanvas):
        
        canvas.saveAsImage(r"E:\GitHub\render.tiff", None, "TIFF")
        qcomp.makeComposition(canvas, maincanvas)
        #pull layers
        #layers = canvas.layers()
        #layerlist = []
        #for lyr in layers:
         #   layerlist.append(lyr.id())

            #create image
        #mapsettings = canvas.mapSettings()
        #mapsettings.setOutputDpi(300)
        #size = mapsettings.outputSize()
        #img = QImage(QtCore.QSize(800, 600), QImage.Format_ARGB32_Premultiplied)
        #color = QColor(255, 255, 255)
        #img.fill(color.rgb())
        #create painter
        #p = QPainter()
        #p.begin(img)
        #p.setRenderHint(QPainter.Antialiasing)

        #create renderer
        #render = canvas.mapRenderer()
        
        #set layers and extent
        #render.setLayerSet(layerlist)
        #render.setExtent(canvas.extent())
        
        #set output size
        #render.setOutputSize(img.size(), 300)
        
        #render 
        #render.render(p)
        
        #p.end()
        #save image
        #img.save(r"E:\GitHub\Test\render.png","png")

VAL_FORM_CLASS, _ = uic.loadUiType(os.path.join(
os.path.dirname(__file__), 'validation log.ui'))        

class ValidateFiles(QDialog,VAL_FORM_CLASS):
    validationPassed = QtCore.pyqtSignal(bool)
    
    def __init__(self, collarfile, surveyfile, logfiles, dipsignNeg, parent=None):
        """Constructor."""
        super(ValidateFiles, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        self.collarfile = collarfile
        self.surveyfile = surveyfile
        self.logfiles = logfiles
        self.dipsignNeg = dipsignNeg
        self.eohDict = {}
        self.canProceed = True
        self.warningsExist = False
        self.btnValidate.clicked.connect(self.runValidation)
        
    def runValidation(self):
        #run compulsory checks
        self.checkCollar()
        self.progressBar.setValue(25)
        self.checkSurvey()
        self.progressBar.setValue(50)#run optional checks
        if self.chkDev.isChecked():
            if self.canProceed:
                self.printToLog("\n Checking survey deviations")
                self.checkDeviation()
            else:
                self.printToLog("\n Input Data needs to be fixed before deviations are checked")
        if self.chkSpread.isChecked():
            if self.canProceed:
                self.printToLog("\n Checking Collar spread")
                self.checkLocationSpread()
            else:
                self.printToLog("\n Input Data needs to be fixed before collar spread is checked")
        #run logdata checks
        self.progressBar.setValue(75)
        for log in self.logfiles:
            self.checkLogfiles(log)
        
        
        self.progressBar.setValue(100)
        #post finishing messages and allow to continue if passed
        if self.canProceed:
            if self.warningsExist:
                self.printToLog(" \n Error Checking Complete. Please check warnings above before proceeding")
                self.validationPassed.emit(True)
            else:
                self.printToLog(" \n Error Checking Complete, ready to create project")
                self.validationPassed.emit(True)
        else:
            self.printToLog(" \n Error Checking Complete. Critical Errors were found. Please rectify the data and run validation again before creating project")
                            
    def printToLog(self, mesg):
        self.logOutput.appendPlainText(mesg)
        
    def checkCollar(self):
        allowableHID = ["HoleID", "holeid","HoleId", "Hole_Id","Hole_ID", "hole_id", "Hole", "hole"]
        allowableX = ["Easting","East", "X", "x", "EASTING", "EAST"]
        allowableY = ["Northing", "Y", "y", "NORTHING", "NORTH", "North"]
        allowableZ = ["RL", "Elevation", "elevation", "Z", "z"]
        allowableEOH = ["EOH", "eoh", "FinalDepth", "Final_Depth", "Depth"]
        
        self.printToLog("\n Checking Collars")
        with open(self.collarfile, 'r') as col:
            #next(col)
            readercol=csv.reader(col)
            headings = readercol.next()
            if len(headings) > 5:
                self.printToLog("Too many columns, only HoleID, Easting, Northing, Elevation and EOH required")
                self.canProceed = False
            if allowableHID.count(headings[0]) == 0:
                self.printToLog("Hole ID not recognized, must be first column")
                self.canProceed = False
            if allowableX.count(headings[1]) == 0:
                self.printToLog("Easting not recognized, must be second column")
                self.canProceed = False
            if allowableY.count(headings[2]) == 0:
                self.printToLog("Northing not recognized, must be third column")
                self.canProceed = False
            if allowableZ.count(headings[3]) == 0:
                self.printToLog("Elevation not recognized, must be fourth column")
                self.canProceed = False
            if allowableEOH.count(headings[4]) == 0:
                self.printToLog("EOH not recognized, must be fifth column")
                self.canProceed = False
            i = 2
            try:
                for holeid,x,y,z,EOH in readercol:
                
                    if len(holeid) == 0:
                        self.printToLog("HoleID missing, line {}".format(i))
                       
                    try:
                        test = float(x)
                        test = float(y)
                        test = float(z)
                        test = float(EOH)
                    except ValueError:
                        self.printToLog("non numeric or missing values detected in Easting, Northing, Elevation or EOH, line {}".format(i))
                        self.canProceed = False
                    i += 1
                    self.eohDict[holeid]= EOH
            except ValueError:
                self.printToLog("data or column missing at line {}".format(i))
                
    def checkSurvey(self):
        allowableHID = ["HoleID", "holeid","HoleId", "Hole_Id","Hole_ID", "hole_id", "Hole", "hole", "HOLE", "HOLEID"]
        allowableDepth = ["Depth", "depth", "from", "DEPTH"]
        allowableDip = ["Dip", "dip", "inclination", "DIP"]
        allowableAzi = ["Azimuth", "azimuth", "Azi", "azi", "Bearing","bearing", "AZI", "AZIMUTH"]
        holelist = []
        self.printToLog("\n Checking Surveys")
        
        with open(self.surveyfile, 'r') as sur:
            #next(col)
            readersur=csv.reader(sur)
            headings = readersur.next()
            if len(headings) > 4:
                self.printToLog("Too many columns, only HoleID, Depth, Dip and Azimuth required")
                self.canProceed = False
            if allowableHID.count(headings[0]) == 0:
                self.printToLog("Hole ID not recognized, must be first column")
                self.canProceed = False
            if allowableDepth.count(headings[1]) == 0:
                self.printToLog("Depth not recognized, must be second column")
                self.canProceed = False
            if allowableDip.count(headings[2]) == 0:
                self.printToLog("Dip not recognized, must be third column")
                self.canProceed = False
            if allowableAzi.count(headings[3]) == 0:
                self.printToLog("Azimuth not recognized, must be fourth column")
                self.canProceed = False
            checkDict = {}            
            i = 2
            try:
                for holeid,depth, dip, azi in readersur:
                                   
                    if len(holeid) == 0:
                        self.printToLog("HoleID missing, line {}".format(i))
                        self.canProceed = False
                    try:
                        test = float(depth)
                        test = float(azi)
                        test = float(dip)
                        #see if the sign of the dip matches that declared by user
                        if self.dipsignNeg:
                            if test > 0:
                                self.printToLog("Warning: Positive Dip sign detected in {} at {}".format(holeid, depth))
                                self.warningsExist = True
                        else:
                            if test < 0:
                                self.printToLog("Warning: Negative sign detected in {} at {}".format(holeid, depth))
                                self.warningsExist = True
                                
                    except ValueError:
                        self.printToLog("non numeric or missing values detected in Easting, Northing, Elevation or EOH, line {}".format(i))
                        self.canProceed = False
                    try:
                        if float(depth) > float(self.eohDict[holeid]):
                            self.printToLog("survey ({}) past EOH ({}) for {}, line {}".format(depth, self.eohDict[holeid], holeid, i))
                            self.canProceed = False
                    except KeyError:
                        self.printToLog("Hole ID does not exist in collar file '{}', line {}".format(holeid, i))
                        self.canProceed = False
                        
                    if checkDict.has_key(holeid):
                        checkDict[holeid].append(depth)
                    else:
                        checkDict[holeid] = [depth]
                        
                    holelist.append(holeid)
                    i += 1
            except ValueError:
                self.printToLog("data or column missing at line {}".format(i))
            #check for duplicate surveys
            for holes in checkDict:
                depthList = checkDict[holes]
                for d in depthList:
                    if depthList.count(d) != 1:
                        self.printToLog("Duplicate Survey depth identified in {} at {}".format(holes, d))
                        self.canProceed = False
            #check for holes with no survey data
            for key in self.eohDict:
                if not checkDict.has_key(key):
                    self.printToLog("Hole {} has no survey data".format(key))
                    self.canProceed = False
                    
    def checkLogfiles(self, log):
        self.printToLog("\n Checking {}".format(log))
        csvfile = open(log, 'rb')
        reader = csv.reader(csvfile)
        header = reader.next()
        # Get sample
        sample = reader.next()
        fieldsample = dict(zip(header, sample))
        a = False
        if not fieldsample.has_key("HoleID"):
            a = True
            self.printToLog("log file {} must have column named HoleID".format(log))
            self.canProceed = False
        if not fieldsample.has_key("From"):
            a = True
            self.printToLog("log file {} must have column named From".format(log))
            self.canProceed = False
        if not fieldsample.has_key("To"):
            a = True
            self.printToLog("log file {} must have column named To".format(log))
            self.canProceed = False
        if a:
            self.printToLog("file format errors in {} must be fixed before continuing".format(log))
            return
        
        logdata = QgsVectorLayer(log, 'log', 'ogr')
        
        #create iterator
        logiter = logdata.getFeatures()
       
        #iterate over all log entries and create the trace geometries into the new shapefile
        i=2
        holelist = []
        intervalDict = {}
        for logfeature in logiter:
            #initialise variables
            holeid = logfeature.attributes()[logfeature.fieldNameIndex('HoleID')]
            
            if not self.eohDict.has_key(holeid):
                self.printToLog("Data for hole with no collar {} detected line {}".format (holeid, i))
                self.canProceed = False
                i += 1
                continue
            
            try:
                lsampfrom =float( logfeature.attributes()[logfeature.fieldNameIndex('From')])
                lsampto = float(logfeature.attributes()[logfeature.fieldNameIndex('To')])
                if lsampto > float(self.eohDict[holeid]):
                    self.printToLog("log interval {} to {} exceeds EOH, {}, line {}".format(lsampfrom, lsampto, holeid, i))
                    self.canProceed = False
            except (ValueError, TypeError):
                self.printToLog("non numeric From - To detected in line {}".format(i))
                self.canProceed = False
            holelist.append(holeid)
            
            if intervalDict.has_key(holeid):
                intervalDict[holeid].append([lsampfrom, lsampto])
            else:
                intervalDict[holeid] = [[lsampfrom, lsampto]]
                
            i += 1
            
        for key in self.eohDict:
            if holelist.count(key) == 0:
                self.printToLog("Warning: Hole {} has no entries in {}".format(key, log))
                self.warningsExist = True
        try:
            #print intervalDict
            for h in intervalDict:
            
                intervalList = intervalDict[h]
                for k in intervalList:
                    top = k[0]
                    bottom = k[1]
                    for j in intervalList:
                        #print "hole {}, checking interval {} against {}. j[0] = {}".format(h, k, j, j[0])
                        if (j[0] > top) and (j[0] < bottom):
                            self.printToLog("Warning: overlapping intervals detected in hole {} ({} to{}) in {}".format(h, top, bottom, log))
                            self.warningsExist = True
        except (ValueError, TypeError):
            self.printToLog("Overlapping interval check failed due to bad data. See previous errors")
            
    def checkDeviation(self):
        
        
        with open(self.collarfile, 'r') as col:
            next(col)
            readercol=csv.reader(col)
            
            for holeid,x,y,z,EOH in readercol:
                #print "holeid", holeid
                collars=[x,y,z,EOH]
                a = holeid
                i=0
                        
                with open(self.surveyfile, 'r') as sur:
                    next(sur)
                    readersur = csv.reader(sur)
                    surveys={}
                    for hole, depth,dip,azi in readersur:
                        if hole ==a:
                            surv = [float(depth), float(dip), float(azi)]
                            surveys[i]=surv
                            i=i+1
                            
                j=0
                while j+1 < len(surveys): 
                    depthb = surveys[(j+1)][0]
                    deptht = surveys[j][0]
                    interval = depthb - deptht
                    #prevent throwing exception if interval is 0
                    if interval == 0:
                        self.printToLog("Warning: Interval between surveys is Zero between {} and {} in {}".format(deptht, depthb, holeid))
                        j += 1
                        continue
                    delDip = surveys[(j+1)][1] - surveys[j][1]
                    if surveys[(j+1)][0] >330:
                        azi1 = surveys[(j+1)][0] -360
                    else:
                        azi1 = surveys[j][0]
                    if surveys[(j+1)][0] >330:
                        azi2 = surveys[j][0] -360
                    else:
                        azi2 = surveys[j][0]
                    delazi = azi2 - azi1
                    devrate = abs((delDip/interval) * 30)
                    swingrate = abs((delazi/interval) * 30)
                    if devrate > 5:
                        self.printToLog("Warning: Excessive dip change of {} per 30m between {} and {} in {}".format(devrate, deptht, depthb, holeid))
                        
                        self.warningsExist =True
                    if swingrate > 10:
                        self.printToLog("Warning: Excessive dip change of {} per 30m between {} and {} in {}".format(swingrate, deptht, depthb, holeid))
                        self.warningsExist = True
                    j +=1
                    
    def checkLocationSpread(self):
        
        with open(self.collarfile, 'r') as col:
            next(col)
            readercol=csv.reader(col)
            xlist = []
            ylist = []
            zlist = []
            
            for holeid,x,y,z,EOH in readercol:
                #print "holeid", holeid
                xlist.append(float(x))
                ylist.append(float(y))
                zlist.append(float(z))
            
            xrange = max(xlist) - min(xlist)
            yrange = max(ylist) - min(ylist)
            zrange = max(zlist) - min(zlist)
            
            if (xrange >10000) or (yrange > 10000):
                self.printToLog("Warning: A large collar spread of greater than 10km was detected")
                self.warningsExist = True
            if zrange > 500:
                self.printToLog("Warning: A  vertical spread of more than 500m between collars was detected")
                self.warningsExist = True
                
ANL_FORM_CLASS, _ = uic.loadUiType(os.path.join(
os.path.dirname(__file__), 'addnewlayer_dialog_base.ui'))

class AddNewLayerDialog(QtGui.QDialog, ANL_FORM_CLASS):
    #dialog to assist with creating a new blank layer to a section
    def __init__(self, parent=None):
        """Constructor."""
        super(AddNewLayerDialog, self).__init__(parent)
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        #set up parameters to store
        self.lyrName = None
        self.fields = QgsFields()
        field = QgsField(name="id", type=QtCore.QVariant.Int, len=6 )
        self.fields.append(field)
        self.geometryType = QGis.WKBPoint
        
        self.cbxType.addItem("Text Data")
        self.cbxType.addItem("Whole Number")
        self.cbxType.addItem("Decimal Number")
        #set up signals
        self.rbnPoint.toggled.connect(self.setType)
        self.rbnLine.toggled.connect(self.setType)
        self.rbnPoly.toggled.connect(self.setType)
        self.ledLyrName.textChanged.connect(self.setName)
        self.btnAddAttribute.clicked.connect(self.addFields)
        self.btnRemAttribute.clicked.connect(self.remFields)
        self.cbxType.currentIndexChanged.connect(self.enablePrec)
        
    def setType(self):
        if self.rbnLine.isChecked():
            self.geometryType = QGis.WKBLineString
        elif self.rbnPoint.isChecked():
            self.geometryType = QGis.WKBPoint
        elif self.rbnPoly.isChecked():
            self.geometryType = QGis.WKBPolygon
    def setName(self):
        self.lyrName = self.ledLyrName.text()
        
    def enablePrec(self):
        if self.cbxType.currentText() == "Decimal Number":
            self.ledPrecision.setEnabled(True)
        else:
            self.ledPrecision.setEnabled(False)
            
    def addFields(self):
        if self.cbxType.currentText() == "Text Data":
            ftype = QtCore.QVariant.String
        elif self.cbxType.currentText() == "Whole Number":
            ftype = QtCore.QVariant.Int
        elif self.cbxType.currentText() == "Decimal Number":
            ftype = QtCore.QVariant.Double
            
        if self.cbxType == "Decimal Number":
            fprec = int(self.ledPrecision.text())
        else:
            fprec = 0
        
        fname=self.ledAttName.text()
        fwidth = int(self.ledWidth.text())
            
        field = QgsField(name=fname, type=ftype, len=fwidth, prec=fprec )
        self.fields.append(field)
        treeitem = QtGui.QTreeWidgetItem()
        treeitem.setText(0, fname)
        treeitem.setText(1, self.cbxType.currentText())
        treeitem.setText(2, str(fwidth))
        treeitem.setText(3, str(fprec))
        self.AttributeView.addTopLevelItem(treeitem)
        
    def remFields(self):
        treeitem = self.AttributeView.selectedItems()
        
        for item in treeitem:
            fname = item.text(0)
            idx = self.fields.indexFromName(fname)
            self.fields.remove(idx)
            trash = self.AttributeView.takeTopLevelItem(self.AttributeView.indexOfTopLevelItem(item))
            del trash
    
