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
        self.btnLoadPrj.clicked.connect(self.printout)
        self.btnPrjDirbrowse.clicked.connect(lambda:self.showFileBrowser("projdir"))
        self.btnRemlog.clicked.connect(self.removefromLoglist)
        #self.btnSavePrj.clicked.connect()
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
            self.lstDHlogs.takeItem(self.lstDHlogs.row(item))
        templist = []    
        for i in xrange(self.lstDHlogs.count()):
            templist.append(self.lstDHlogs.item(i).text())
            
        QDrillerDialog.datastore.logfiles = templist
        self.refreshGui()
        
    
    def addtoLayerList(self, ):
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
            self.lstExistingLayers.takeItem(self.lstExistingLayers.row(item))
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
        self.gpbxPlanview.setEnabled(True)
        QDrillerDialog.datastore.createProjectFile()
        QDrillerDialog.datastore.calcDrillholes()
        
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

    def __init__(self):
        super(DataStore, self).__init__()
        #variables to do with the backend calculations
        #container for drillhole data as read from file
        self.drillholes={}
        #container for the calculated XYZ coordinates
        self.drillholesXYZ={}
        
        #variables for running project
        self.projectdir = None
        self.projectname = None
        self.projectCRS = None  #consider initialising this to a real projection?
        
        #variables important to calculations/backend
        self.collarfile = None
        self.surveyfile = None
        self.logfiles = []
        self.logtarget = None
        self.trace2can = True
        self.log2can = True
        self.coll2can = True
        
        #variables for keeping track of created layers
        self.planLogLayers = []
        self.existingLayersDict ={}
        
    def createProjectFile(self):
    #a function to create a project file to save settings etc to
        print "this doesnt do anything yet"
    def loadProject():
    #a function to load settings from a saved project file
        empty=None  
    def saveProject():
    #a function to write current settings to current project file
        empty=None
        
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
        
        
        # create toolbar
        self.toolbar = self.addToolBar("Map Tools")
        self.toolbar.addAction(self.actionZoom_in)
        self.toolbar.addAction(self.actionZoom_out)
        self.toolbar.addAction(self.actionTouch)
        self.toolbar.addAction(self.actionPan)

        # connect the tool(s)
        self.actionZoom_in.triggered.connect(self.zoom_in)
        self.actionZoom_out.triggered.connect(self.zoom_out)
        self.actionPan.triggered.connect(self.mapPan)
        self.actionTouch.triggered.connect(self.mapTouch)
        
        # create the map tool(s)
        self.tool_zoomin = qgis.gui.QgsMapToolZoom(self.sectionCanvas, False)
        self.tool_zoomout = qgis.gui.QgsMapToolZoom(self.sectionCanvas, True)
        self.tool_pan = qgis.gui.QgsMapToolPan(self.sectionCanvas)
        self.tool_touch = qgis.gui.QgsMapToolTouch(self.sectionCanvas)
        
        layer = qgis.core.QgsVectorLayer(r"E:\GitHub\Test\test_collars.shp", "test collars", 'ogr')
        print "layer valid", layer.isValid()
        qgis.core.QgsMapLayerRegistry.instance().addMapLayer(layer, addToLegend=False)
        print "register", qgis.core.QgsMapLayerRegistry.instance().count()
        canvas_layer = qgis.gui.QgsMapCanvasLayer(layer)
        canvas_layer.setVisible(True)
        print "layer visibility", canvas_layer.isVisible()
        self.sectionCanvas.setLayerSet([canvas_layer])
        extent = layer.extent()
        print "layer extents", extent
        self.sectionCanvas.setExtent(extent)
        print "canvas extent", self.sectionCanvas.extent()
        self.sectionCanvas.refresh()
        
    def mapPan(self):
        self.sectionCanvas.setMapTool(self.tool_pan)
        print "pan action triggered"
        centre = self.sectionCanvas.center()
        print "centre of canvas", centre.toString()
        
    def mapTouch(self):
        self.sectionCanvas.setMapTool(self.tool_touch)
        print "touch action triggered"
        centre = self.sectionCanvas.center()
        print "centre of canvas", centre.toString()
        
    def zoom_in(self): #could these type things be set up in a lambda connection
        self.sectionCanvas.setMapTool(self.tool_zoomin)
        print "zoom in action triggered"
        
    def zoom_out(self): #could these type things be set up in a lambda connection
        self.sectionCanvas.setMapTool(self.tool_zoomout)
        print "zoom out action triggered"
            
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
