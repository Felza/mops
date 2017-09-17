# -*- coding: utf-8 -*-
"""
/***************************************************************************
 mops
                                 A QGIS plugin
 N/A
                              -------------------
        begin                : 2016-10-22
        git sha              : $Format:%H$
        copyright            : (C) 2016 by LNH Water
        email                : kontakt at lnhwater dot dk
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
from PyQt4.QtCore import *
from qgis.gui import *
from qgis.core import *
from qgis.core import NULL, QgsLayerTreeGroup, QgsLayerTreeLayer
from PyQt4.QtGui import QAction, QIcon, QFileDialog, QMessageBox, QProgressBar, QPicture, QPainter, QImage, QPixmap, QColor
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialogs
from mops_module_name_dialog import importDialog
from mops_module_save import saveDialog
from mops_module_export_shapefiles import exportShapefilesDialog
from mops_module_export_polygon_to_text import exportPolygonToTextDialog
from mops_module_export_style import exportStyle
from mops_module_export_polygonChanges import exportPolygonChanges
from mops_module_calculate_raster import calculateRaster
from mops_module_import_project import importProjectDialog
from mops_module_profile import profilePicture
from mops_module_reload import reloadDialog
from mops_module_export_project import exportProjectDialog
from os.path import isfile, join, expanduser, isdir
import os.path
from os import listdir
import codecs
import traceback
import glob
from math import log10, floor
import xml.etree.ElementTree
from shutil import copyfile

class LNode(object):
    def __init__(self,feat, before, highlight):
        self.before = before
        self.after = None
        self.feat = feat
        self.highlight = highlight
    
    def add(self,feat):
        self.after = LNode(feat,self)
    
    def changeH(self,chosen):
        if chosen:
            self.highlight.setColor(QColor.fromRgb(0, 255, 0))
        else:
            self.highlight.setColor(QColor.fromRgb(255, 255, 0))
    
    def getLast(self):
        node = self
        while node.after is not None:
            node = node.after
        return node
    
    def delete(self):
        self.deleteAll(self)

    def deleteAll(self, node):
        if node.after is not None:
            self.deleteAll(node.after)
        node.before = node.after = None
            
class PointTool(QgsMapTool):   
    def __init__(self, canvas):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.state = 1
        self.possibleNodes = []
        

    def canvasPressEvent(self, event):
        pass

    def canvasMoveEvent(self, event):
        pass
        
    def startStateTwo(self):
        self.showPossibleNodes(self.firstNode)

    def showPossibleNodes(self,node):
        pointLayer = QgsMapLayerRegistry.instance().mapLayersByName("Node")[0]
        layers = self.canvas.layers()
        feature = node.feat
        self.possibleNodes = []
        possibleFeatures = []
        for lineLayer in layers:
            if lineLayer.wkbType()==2:
                muid = feature['MUID']
                if lineLayer.name() != "CatchCon" and lineLayer.name() != "LoadCon":
                    expr = QgsExpression( "\"FROMNODE\"='{}'".format(muid))
                    for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                        id = lineFeature['TONODE']
                        if id:
                            expr = QgsExpression( "\"MUID\"='{}'".format(id))
                            for feat in pointLayer.getFeatures( QgsFeatureRequest(expr)):
                                possibleFeatures.append(feat)
                    expr = QgsExpression( "\"TONODE\"='{}'".format(muid))
                    for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                        id = lineFeature['FROMNODE']
                        if id:
                            expr = QgsExpression( "\"MUID\"='{}'".format(id))
                            for feat in pointLayer.getFeatures( QgsFeatureRequest(expr)):
                                possibleFeatures.append(feat)
        #Append possibleNodes
        for pos in possibleFeatures:
            check = True
            nodeCheck = self.firstNode
            #Needed a do-while statement
            while True:
                if pos['MUID'] == nodeCheck.feat['MUID']:
                    check = False
                    break
                nodeCheck = nodeCheck.after
                if nodeCheck is None:
                    break
            if check:
                h = QgsHighlight(self.canvas,pos.geometry(),pointLayer)
                h.setColor(QColor.fromRgb(255, 255, 0))
                h.setWidth(8)
                self.possibleNodes.append(LNode(pos,None,h))
                self.canvas.refresh()

    def canvasReleaseEvent(self, event):
        layer = QgsMapLayerRegistry.instance().mapLayersByName("Node")[0]
        x = event.pos().x()
        y = event.pos().y()
        point = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)
        spIndex = QgsSpatialIndex()
        #State 1 for selecting the first node
        if self.state == 1:
            feats = layer.getFeatures()
            for feat in feats:
                spIndex.insertFeature(feat)
            nearestIds = spIndex.nearestNeighbor(point,1)
            featIte = layer.getFeatures(QgsFeatureRequest().setFilterFid(nearestIds[0]))
            feat = QgsFeature()
            featIte.nextFeature(feat)
            h = QgsHighlight(self.canvas,feat.geometry(),layer)
            h.setColor(QColor.fromRgb(0, 255, 0))
            h.setWidth(8)
            self.firstNode = LNode(feat,None,h)
            self.canvas.refresh()
        #State 2 for selecting the next nodes
        else:
            #Add all possibleNodes
            for node in self.possibleNodes:
                spIndex.insertFeature(node.feat)
            #Add the last node
            lastNode = self.firstNode.getLast()
            spIndex.insertFeature(lastNode.feat)
            nearestIds = spIndex.nearestNeighbor(point,1)
            featIte = layer.getFeatures(QgsFeatureRequest().setFilterFid(nearestIds[0]))
            feat = QgsFeature()
            featIte.nextFeature(feat)
            if feat['MUID'] == self.firstNode.feat['MUID']:
                pass
            elif feat['MUID'] == lastNode.feat['MUID']:
                self.firstNode.getLast().before.after = None
                h = QgsHighlight(self.canvas,feat.geometry(),layer)
                h.setColor(QColor.fromRgb(0, 255, 0))
                h.setWidth(8)
                self.showPossibleNodes(self.firstNode.getLast())
            else:
                h = QgsHighlight(self.canvas,feat.geometry(),layer)
                h.setColor(QColor.fromRgb(0, 255, 0))
                h.setWidth(8)
                lastNode.after = LNode(feat,lastNode,h)
                self.showPossibleNodes(self.firstNode.getLast())
            
            
    def activate(self):
        self.state = 1
        pass

    def deactivate(self):
        self.state = 1
        #Delete the nodes (This way all chosen nodes' highlights are deleted aswell)
        try:
            self.firstNode.delete()
            del self.firstNode
        except:
            pass
        #Also delete possible nodes
        try:
            del self.possibleNodes
        except:
            pass
        self.canvas.refresh()

    def isZoomTool(self):
        return False

    def isTransient(self):
        return False

    def isEditTool(self):
        return False

class mops:
    """QGIS Plugin Implementation."""


    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'mops_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)


        # Declare instance attributes

        self.actions = []
        self.menu = self.tr(u'&MOPS plugin')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'mops')
        self.toolbar.setObjectName(u'mops')
        

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('mops', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """
        # Create the dialogs and keep references
        self.dlg = importDialog()
        self.dlg.pushButton.clicked.connect(lambda: self.select_input_folder(self.dlg))
        self.dlg.checkBox.stateChanged.connect(self.importCheckBox)
        self.dlg.pushButton_2.clicked.connect(self.importCatchment)
        self.dlg2 = saveDialog()
        self.dlg2.pushButton.clicked.connect(lambda: self.select_output_file(self.dlg2,'*.txt', "Select output file"))
        self.dlg3 = exportShapefilesDialog()
        self.dlg3.pushButton.clicked.connect(lambda: self.select_output_folder(self.dlg3))
        self.dlg4 = exportPolygonToTextDialog()
        self.dlg4.pushButton.clicked.connect(lambda: self.select_output_folder(self.dlg4))
        self.dlg5 = exportPolygonChanges()
        self.dlg5.pushButton.clicked.connect(self.select_output_dlg5)
        self.dlg6 = exportStyle()
        self.dlg6.pushButton.clicked.connect(lambda: self.select_output_folder(self.dlg6))
        self.dlg7 = calculateRaster()
        self.dlg7.pushButton.clicked.connect(lambda: self.select_output_folder(self.dlg7))
        self.dlg8 = importProjectDialog()
        self.dlg8.pushButton.clicked.connect(lambda: self.select_input_file(self.dlg8, '*.qgs','Choose the project to open'))
        self.dlg9 = profilePicture()
        self.dlg10 = reloadDialog()
        self.dlg10.listWidget.setSelectionMode(2)
        self.dlg10.comboBox.currentIndexChanged.connect(self.groupChanged)
        self.dlg10.pushButton.clicked.connect(lambda: self.select_input_folder(self.dlg10))
        self.dlg11 = exportProjectDialog()
        self.dlg11.pushButton.clicked.connect(lambda: self.select_output_file(self.dlg11,'*.qgs',"Select output file"))
        # Add the mapTool for LengthProfile
        self.mapTool = PointTool(self.iface.mapCanvas())
        
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/mops/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Import'),
            callback=self.importdlg,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Save lines and points to textfile'),
            callback=self.exportdlg,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Save polygon layers to textfiles'),
            callback=self.exportPolygons,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Save selected layers as Shapefiles'),
            callback=self.exportShapefiles,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Save changes made in the polygon layer'),
            callback=self.savePolygonChanges,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Save or import styles'),
            callback=self.exportOrSaveStyle,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Calculate raster'),
            callback=self.calculateRaster,
            parent=self.iface.mainWindow())
        
        self.add_action(
            icon_path,
            text=self.tr(u'Open a QGIS-MOPS project'),
            callback=self.importProjectDialog,
            parent=self.iface.mainWindow())
            
        self.add_action(
            icon_path,
            text=self.tr(u'Save a QGIS-MOPS project'),
            callback=self.exportProjectDialog,
            parent=self.iface.mainWindow())        

        self.add_action(
            icon_path,
            text=self.tr(u'Length profile'),
            callback=self.lengthProfile,
            parent=self.iface.mainWindow())
            
        self.add_action(
            icon_path,
            text=self.tr(u'Reload selected layers'),
            callback=self.reloadData,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&MOPS plugin'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def reloadData(self):
        recentPaths = self.getRecentPaths(self.dlg10,0,3)
        self.dlg10.comboBox.clear()
        root = QgsProject.instance().layerTreeRoot()
        for group in root.children():
            if isinstance(group,QgsLayerTreeGroup):
                self.dlg10.comboBox.addItem(group.name())
        # show the dialog
        self.dlg10.show()
        # Run the dialog event loop
        result = self.dlg10.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            folderpath = self.dlg10.textEdit.currentText()
            try:
                #Get selected layers
                selectedItems = self.dlg10.listWidget.selectedItems()
                layerNames = []
                for name in selectedItems:
                    layerNames.append(name.text())
                stylesFolder = expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\tempstyles"
                #Delete tempstyles
                files = glob.glob(stylesFolder + "\\*")
                for f in files:
                    os.remove(f)                  
                #Get the group
                group = QgsProject.instance().layerTreeRoot().findGroup(self.dlg10.comboBox.currentText())
                #Save the order
                layerNameList = [c.layer().name() for c in group.children()]
                my_order = {}
                for i, layerName in enumerate(layerNameList):
                    my_order[layerName] = i
                #Save the styles and delete the selected layers
                for layer in group.children():
                    if isinstance(layer,QgsLayerTreeLayer) and layer.name() in layerNames:
                        layer.layer().saveNamedStyle(stylesFolder + "\\" + layer.name() + ".qml")
                        QgsMapLayerRegistry.instance().removeMapLayer(layer.layer())
                #Set progress
                self.iface.messageBar().clearWidgets()
                progressMessageBar = self.iface.messageBar()
                progress = QProgressBar()
                progress.setMaximum(100) 
                progress.setTextVisible(True)
                progressMessageBar.pushWidget(progress)
                
                errorList = ""
                j = 0
                #Go through all files in the folder and find the text file
                #Add the nodes
                progress.setFormat("Loading nodes..")
                for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                    if file[-4:] == ".txt":
                        input = open(folderpath + "\\" + file, 'r')
                        inputline = input.readline()
                        i=1
                        while (inputline != "ENDOFFILE"):
                            if inputline == "POINTS\n":
                                name = input.readline().rstrip('\n')
                                if name in layerNames:
                                    errorList = self.points(name, input, group, errorList)
                                    progress.setValue(100/3/3*i)
                                    i+=1
                            elif inputline == "LINES\n":
                                j+=1
                            inputline = input.readline()
                        input.close()
                #Go through all files in the folder and find the text file
                #Add the lines
                #This is done after, because the lines will need the points for field configuration
                progress.setFormat("Loading links..")
                for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                    if file[-4:] == ".txt":
                        input = open(folderpath + "\\" + file, 'r')
                        inputline = input.readline()
                        i=1
                        while (inputline != "ENDOFFILE"):
                            if inputline == "LINES\n":
                                name = input.readline().rstrip('\n')
                                if name in layerNames:
                                    errorList = self.lines(name, input, group, errorList)
                                    progress.setValue(100/3+100/3/j*i)
                                    i+=1
                            inputline = input.readline()
                        input.close()
                #Add the styles again
                for file in [f for f in listdir(stylesFolder) if isfile(join(stylesFolder, f))]:
                    if file[-4:] == ".qml":
                        for layer in group.children():
                            if isinstance(layer,QgsLayerTreeLayer) and layer.name() == file[:-4]:
                                layer.layer().loadNamedStyle(stylesFolder + "\\" + file)
                #Fix the order
                layerList = [c.layer() for c in group.children()]
                sortedList = sorted(layerList,key=lambda val: my_order[val.name()])
                for idx, lyr in enumerate(sortedList):
                    group.insertLayer(idx, lyr)
                group.removeChildren(len(layerList),len(layerList))
                
                #
                self.iface.messageBar().clearWidgets()
                self.iface.mapCanvas().refreshAllLayers()
                if errorList:
                    QMessageBox.about(self.dlg,"Error","The following line(s) were not added due to error:\n\n"+errorList)
            except (WindowsError, IOError):
                QMessageBox.about(self.dlg10,"Error","The folderpath could not be found")
            except:
                QMessageBox.about(self.dlg10,"Error","Unexpected error: " + str(traceback.format_exc()))
        
        
    def lengthProfile(self):
        #If tool is not already active, activate it
        if not self.iface.mapCanvas().mapTool() == self.mapTool:
            self.iface.mapCanvas().setMapTool(self.mapTool)
        #Else check state
        else:
            if self.mapTool.state == 1:
                self.mapTool.state = 2
                self.mapTool.startStateTwo()
            else:
                features = []
                node = self.mapTool.firstNode
                while node.after is not None:
                    features.append(node.feat)
                    node = node.after
                features.append(node.feat)
                self.profile(features)
                self.iface.mapCanvas().unsetMapTool(self.mapTool)







    def drawLine(self,x1,y1,x2,y2,style):
        a = self.x0+(float(x1)*self.scaleX)
        b = self.y0-(float(y1)*self.scaleY)
        c = self.x0+(float(x2)*self.scaleX)
        d = self.y0-(float(y2)*self.scaleY)
        self.painter.setPen(style)
        self.painter.drawLine(a,b,c,d)
        
    def drawVerticalText(self,x,y,text):
        self.painter.translate(x,y)
        self.painter.rotate(-90)
        x1 = self.x0+(float(x)*self.scaleX)
        y1 = self.y0-(float(y)*self.scaleY)
        self.painter.drawText(x1,y1,text)
        self.painter.rotate(90)
        self.painter.restore()
    
    def drawAxes(self,features):
        maxX = 1000
        maxY = 500
        self.drawLine(-20,-20,maxX,-20,1)
        self.drawLine(-20,-20,-20,maxY,1)
        maxGround = -9999.0
        self.minInvert = 9999.0
        lengths = []
        fromnode = None
        lines = []
        for f in features:
            featMaxGround = float(f['GroundLevel'])
            featMinInvertLevel = float(f['InvertLevel'])
            #set ground & invert max/min if higher/lower
            if  featMaxGround> maxGround:
                maxGround = featMaxGround
            if  featMinInvertLevel< self.minInvert:
                self.minInvert = featMinInvertLevel
            if fromnode is None:
                fromnode = f
                continue
            #Find the lines of the profiling
            layers = self.iface.legendInterface().layers()
            for lineLayer in layers:
                if lineLayer.wkbType()==2:
                    fromnodeid = fromnode['MUID']
                    tonodeid = f['MUID']
                    if lineLayer.name() != "CatchCon" and lineLayer.name() != "LoadCon":
                        currentLines = []
                        #Feature request for links going down
                        expr = QgsExpression( "\"FROMNODE\"='{}' AND \"TONODE\"='{}'".format(fromnodeid,tonodeid))
                        for lineFeature in lineLayer.getFeatures(QgsFeatureRequest(expr)):
                            currentLines.append((lineLayer.name(),lineFeature,True))
                        #Feature request for links going up
                        expr = QgsExpression( "\"TONODE\"='{}' AND \"FROMNODE\"='{}'".format(fromnodeid,tonodeid))
                        for lineFeature in lineLayer.getFeatures(QgsFeatureRequest(expr)):
                            currentLines.append((lineLayer.name(),lineFeature,False))
                        #If there's only 1 linefeature, just append the length
                        if len(currentLines) == 1:
                            lines.append(currentLines)
                            (lineLayerName,lineFeature,down) = currentLines[0]
                            if lineLayerName == "Link":
                                if lineFeature["Length"]:
                                    lengths.append(float(lineFeature["Length"]))
                                else:
                                    lengths.append(lineFeature.geometry().length())
                            else:
                                lengths.append(lineFeature.geometry().length())
                        #If there's more than 1 lineFeature we need the length of the shortest
                        elif len(currentLines) > 1:
                            lines.append(currentLines)
                            shortest = 99999.0
                            for (lineLayerName,lineFeature,down) in currentLines:
                                geoLength = lineFeature.geometry().length()
                                if lineLayerName == "Link":
                                    if lineFeature["Length"]:
                                        if float(lineFeature["Length"]) < shortest:
                                            shortest = float(lineFeature["Length"])
                                    else:
                                        if lineFeature.geometry().length() < shortest:
                                            shortest = geoLength
                                #Weirs need to be presented as atleast 10 meters
                                elif lineLayerName == "Weir":
                                    if geoLength < shortest:
                                        if geoLength < 10.0:
                                            shortest = 10.0
                                        else:
                                            shortest = geoLength
                                elif geoLength < shortest:
                                    shortest = geoLength
                            lengths.append(shortest)
            fromnode = f
        totalLength = 0.0
        for l in lengths:
            totalLength = totalLength + l
        self.scaleX = maxX/totalLength
        self.scaleY = maxY/(abs(maxGround-self.minInvert))
        self.y0 = self.y0 + (self.minInvert * self.scaleY)
        self.drawNumbers(totalLength,abs(maxGround-self.minInvert))
        return lines, lengths

    def drawNumbers(self,xLen,yLen):
        #create the interval for the axes
        x = round(xLen/10, -int(floor(log10(abs(xLen/10)))))
        y = round(yLen/10, -int(floor(log10(abs(yLen/10)))))
        x2 = 0
        while(x2<xLen):
            self.painter.drawText(self.x0+(x2*self.scaleX),self.height-25,str(x2))
            x2 = x2 + x
        y2 = 0
        while(y2<yLen):
            self.painter.drawText(self.x0-45,(self.y0-(self.minInvert*self.scaleY))-(y2*self.scaleY),str(y2+round(self.minInvert,1)))
            y2 = y2 + y        




    def drawNodes(self,nodes,lineLengths):
        lastNode = NULL
        lastLength = 0.0
        for i, n in enumerate(nodes):
            x = 0.0
            for length in lineLengths[:i]:
                x = x + length
            #Draw the node line
            y1 = float(n['GroundLevel'])
            y2 = float(n['InvertLevel'])
            self.drawLine(x,y1,x,y2,1)
            #Draw the node text
            #self.drawVerticalText(x,y1,n['MUID'])
            #Draw top lines
            if lastNode is not NULL:
                self.drawLine(lastLength,float(lastNode['GroundLevel']),x,float(n['GroundLevel']),1)
            lastNode = n
            lastLength = x
            
    def drawLinks(self,lineLists,nodes,lineLengths):
        for i, lineList in enumerate(lineLists):
            for (layername, feature,down) in lineList:
                if layername == "Link":
                    #Draw the bottom of the pipe
                    #y1 and y2
                    if feature['UpLevel']:
                        if down:
                            y1 = feature['UpLevel']
                        else:
                            y2 = feature['UpLevel']
                    else:
                        node = nodes[i]
                        y1 = node['InvertLevel']
                    
                    if feature['DwLevel']:
                        if down:
                            y2 = feature['DwLevel']
                        else:
                            y1 = feature['DwLevel']
                    else:
                        node = nodes[i+1]
                        y2 = node['InvertLevel']
                    #x1 and x2
                    x1 = 0.0
                    for length in lineLengths[:i]:
                        x1 = x1 + length
                    x2 = x1 + lineLengths[i]
                    self.drawLine(x1,y1,x2,y2,1)
                    #Draw the top of the pipe
                    self.drawLine(x1,float(y1)+float(feature['Diameter']),x2,float(y2)+float(feature['Diameter']),1)
                if layername == "Orifice":
                    #Draw the bottom of the pipe
                    type = feature['TypeNo']
                    node = nodes[i]
                    y1 = node['InvertLevel']
                    node = nodes[i+1]
                    y2 = node['InvertLevel']
                    x1 = 0.0
                    for length in lineLengths[:i]:
                        x1 = x1 + length
                    x2 = x1 + lineLengths[i]
                    self.drawLine(x1,y1,x2,y2,1)
                    #Draw the top of the pipe
                    top = 0.0
                    if type == 1:
                        top = float(feature['Diameter'])
                    elif type == 3:
                        top = float(feature['Height'])
                    self.drawLine(x1,float(y1)+top,x2,float(y2)+top,1)
                if layername == "Valve":
                    #Draw the bottom of the pipe
                    node = nodes[i]
                    y1 = node['InvertLevel']
                    node = nodes[i+1]
                    y2 = node['InvertLevel']
                    x1 = 0.0
                    for length in lineLengths[:i]:
                        x1 = x1 + length
                    x2 = x1 + lineLengths[i]
                    self.drawLine(x1,y1,x2,y2,1)
                    #Draw the top of the pipe
                    top = float(feature['Diameter'])
                    self.drawLine(x1,float(y1)+top,x2,float(y2)+top,1)
                if layername == "Weir":
                    #Draw the bottom of the pipe
                    x1 = 0.0
                    for length in lineLengths[:i]:
                        x1 = x1 + length
                    x2 = x1 + lineLengths[i]
                    y1 = y2 = feature['CrestLevel']
                    self.drawLine(x1,y1,x2,y2,1)
                if layername == "Pump":
                    #Draw the bottom of the pipe
                    node = nodes[i]
                    y1 = node['InvertLevel']
                    node = nodes[i+1]
                    y2 = node['InvertLevel']
                    x1 = 0.0
                    for length in lineLengths[:i]:
                        x1 = x1 + length
                    x2 = x1 + lineLengths[i]
                    self.drawLine(x1,y1,x2,y2,2)

    def profile(self, features):
        layer = QgsMapLayerRegistry.instance().mapLayersByName("Node")[0]
        #Create image and painter
        self.height = 600
        self.x0 = 60
        self.y0 = self.height-60
        self.scaleX = 1.0
        self.scaleY = 1.0
        image = QImage(1200,self.height,QImage.Format_RGB32)
        image.fill(Qt.white)
        self.painter = QPainter()
        self.painter.begin(image)
        #Draw axes and find line features+lengths
        lineFeatures, lineLengths = self.drawAxes(features)
        #Draw the nodes
        self.drawNodes(features, lineLengths)
        #Draw the lines
        self.drawLinks(lineFeatures,features,lineLengths)
        #Add the image and show
        self.painter.end()
        self.dlg9.label.setPixmap(QPixmap.fromImage(image))
        self.dlg9.show()

    def exportProjectDialog(self):
        recentPaths = self.getRecentPaths(self.dlg11,24,27)
        self.dlg11.show()
        result = self.dlg11.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            filepath = self.dlg11.textEdit.currentText()
            self.updateRecentPaths(filepath,24,27,recentPaths)
            try:
                project = QgsProject.instance()
                name = os.path.basename(os.path.normpath(filepath)).split('.')[0]
                #Save project
                project.write(QFileInfo(filepath))
                #Save polygon IDs
                copyfile(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\temp\\temp.txt",os.path.dirname(os.path.abspath(filepath)) + "\\" + name + ".txt")
            except (WindowsError, IOError):
                QMessageBox.about(self.dlg,"Error","The filepath could not be found")
            except:
                QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))
                
                
    def importProjectDialog(self):
        recentPaths = self.getRecentPaths(self.dlg8,21,24)
        # show the dialog
        self.dlg8.show()
        # Run the dialog event loop
        result = self.dlg8.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            filepath = self.dlg8.textEdit.currentText()
            self.updateRecentPaths(filepath,21,24,recentPaths)
            try:
                reply = QMessageBox.Yes
                project = QgsProject.instance()
                if project.isDirty():
                    reply = QMessageBox.question(self.iface.mainWindow(), 'Warning', 
                 'The current project has unsaved changes, continuing will result in these changes being lost.\nContinue?', QMessageBox.Yes, QMessageBox.No)
                if reply == QMessageBox.Yes:
                    #Load project
                    project.read(QFileInfo(filepath))
                    name = os.path.basename(os.path.normpath(filepath)).split('.')[0]
                    folderpath = os.path.dirname(os.path.abspath(filepath))
                    #Get the polygon IDs
                    for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                        if file == name + ".txt":
                            copyfile(folderpath + "\\" + file,expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\temp\\temp.txt")
                    #Add functionality
                    layers = self.iface.legendInterface().layers()
                    for layer in layers:
                        if type(layer) is QgsVectorLayer:
                            #Points
                            if layer.wkbType()==1:
                                layer.committedGeometriesChanges.connect(self.moveLines)
                            #Lines
                            if layer.wkbType()==2:
                                layer.committedAttributeValuesChanges.connect(self.moveLinesToNewNodes)
            except (WindowsError, IOError):
                QMessageBox.about(self.dlg,"Error","The filepath could not be found")
            except:
                QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))

    def calculateRaster(self):
        #Getting recentpaths
        recentPaths = self.getRecentPaths(self.dlg7,18,21)
        # show the dialog
        self.dlg7.show()
        # Run the dialog event loop
        result = self.dlg7.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            folderpath = self.dlg7.textEdit.currentText()
            self.updateRecentPaths(folderpath,18,21,recentPaths)
            #Get the dtm
            try:
                dtm_header = []
                h = 6
                dtm_data = []
                with open(folderpath + "\\dtm.txt") as fp:
                    for line in fp:
                        if h>0:
                            dtm_header.append(line)
                            h-=1
                        else:
                            dtm_data.append(line)
                dtm_data_lists = []
                for line in dtm_data:
                    list = []
                    for number in line.rstrip('\n').rstrip().split(" "):
                        list.append(number)
                    dtm_data_lists.append(list)
                #Get the hole data
                hole_header = []
                h = 6
                hole_data = []
                with open(folderpath + "\\hole.txt") as fp:
                    for line in fp:
                        if h>0:
                            hole_header.append(line)
                            h-=1
                        else:
                            hole_data.append(line)
                hole_data_lists = []
                for line in hole_data:
                    list = []
                    for number in line.rstrip('\n').rstrip().split(" "):
                        list.append(number)
                    hole_data_lists.append(list)
                #Get the hmax for hole
                hmax_header = []
                h = 1
                hmax_data = {}
                with open(folderpath + "\\hmax_hole.txt") as fp:
                    for line in fp:
                        if h>0:
                            hmax_header.append(line)
                            h-=1
                        else:
                            elements = line.split('\t')
                            hmax_data[elements[0]] = elements[1]
                #Get the no_data value
                replace = [hole_header[-1].rstrip('\n').split(" ")[-1]]
                no_data = replace[0]
                #Calculate
                for dtmLineList, holeLineList in zip(dtm_data_lists,hole_data_lists):
                    for i,(dtmnumber, holenumber) in enumerate(zip(dtmLineList,holeLineList)):
                        if holenumber == no_data:
                            dtmLineList[i] = no_data
                        elif holenumber in hmax_data.keys():
                            value = float(hmax_data[holenumber]) - float(dtmnumber) 
                            if value < 0.0:
                                dtmLineList[i] = no_data
                            else:
                                dtmLineList[i] = str(value)
                #Print the result to a new textfile
                listOfLines = []
                for list in dtm_data_lists:
                    listOfLines.append(" ".join(list))
                lineToWrite = ""
                for line in dtm_header:
                    lineToWrite += line
                lineToWrite += "\n".join(listOfLines)
                output_file = open(folderpath + "\\raster_result.txt", 'w')
                output_file.write(lineToWrite)
                output_file.close()
                layer = QgsRasterLayer(folderpath + "\\raster_result.txt", "Raster result")
                QgsMapLayerRegistry.instance().addMapLayer(layer)
            except (WindowsError, IOError):
                QMessageBox.about(self.dlg,"Error","The filepath could not be found")
            except:
                QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))

    def savePolygonChanges(self):
        #Getting recentpaths
        recentPaths = self.getRecentPaths(self.dlg5,15,18)
        # show the dialog
        self.dlg5.show()
        # Run the dialog event loop
        result = self.dlg5.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            filepath = self.dlg5.textEdit.currentText()
            self.updateRecentPaths(filepath,15,18,recentPaths)
            #Do stuff
            try:
                for small in self.iface.legendInterface().layers():
                    if small.wkbType()==3:
                        if small.name()[-5:] == "SMALL":
                            large = QgsVectorLayer(filepath, "namedoesnotmatter", "ogr")
                            text_file = open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\temp\\temp.txt", "r")
                            smallUnmodifiedMopsIDs = text_file.read().split('\n')[:-1]
                            text_file.close()
                            dict_large = {}
                            for f in large.getFeatures():
                                dict_large[f['MopsID']] = f
                            newFeatures = []
                            for k, v in dict_large.iteritems():
                                if k not in smallUnmodifiedMopsIDs:
                                    newFeatures.append(v)
                            newFeatures.extend(small.getFeatures())
                            new_layer = QgsVectorLayer("Polygon?crs=epsg:3044", "duplicated_layer", "memory")
                            new_layer_data = new_layer.dataProvider()
                            attr = large.dataProvider().fields().toList()
                            new_layer_data.addAttributes(attr)
                            new_layer.updateFields()
                            new_layer_data.addFeatures(newFeatures)

                            QgsVectorFileWriter.writeAsVectorFormat(new_layer, filepath[:-4] + "_NEW" + ".shp","ascii", large.crs() ,"ESRI Shapefile")
            except (WindowsError, IOError):
                QMessageBox.about(self.dlg,"Error","The folder could not be found")
            except:
                QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))

    def exportOrSaveStyle(self):
        #Getting recentpaths
        recentPaths = self.getRecentPaths(self.dlg6,12,15)
        #Get the groups for the comboBox
        groups = []
        for node in QgsProject.instance().layerTreeRoot().children():
            if isinstance(node,QgsLayerTreeGroup):
                groups.append(node.name())
        self.dlg6.groupBox.clear()
        self.dlg6.groupBox.addItems(groups)
        # show the dialog
        self.dlg6.choice_import.click()
        self.dlg6.show()
        # Run the dialog event loop
        result = self.dlg6.exec_()
        # See if OK was pressed
        if result:
            #Get the layers in the group
            group = QgsProject.instance().layerTreeRoot().findGroup(self.dlg6.groupBox.currentText())
            #Update combobox of recent paths by adding the new one
            folderpath = self.dlg6.textEdit.currentText()
            fileCounter = len(glob.glob1(folderpath,"*.qml"))
            reply = QMessageBox.Yes
            if fileCounter > 0 and self.dlg6.choice_save.isChecked():
                reply = QMessageBox.question(self.iface.mainWindow(), 'Warning', 
                 'This folder already contain styles. Styles with identical names will be overwritten.\nAre you sure you want to continue?', QMessageBox.Yes, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.updateRecentPaths(folderpath,12,15,recentPaths)
                #Do the work
                try:
                    if self.dlg6.choice_save.isChecked():
                        #Save styles in chosen folder
                        for layer in group.children():
                            if isinstance(layer,QgsLayerTreeLayer):
                                layer.layer().saveNamedStyle(folderpath + "\\" + layer.name() + ".qml")
                    else:
                        #Import styles from chosen folder
                        #Due to .qml files also containing other properties than styles, we need to remove these.
                        stylesFolder = expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\tempstyles"
                        #Delete tempstyles in folder
                        files = glob.glob(stylesFolder + "\\*")
                        for f in files:
                            os.remove(f)
                        for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                            if file[-4:] == ".qml":
                                for layer in group.children():
                                    if isinstance(layer,QgsLayerTreeLayer) and layer.name() == file[:-4]:
                                        #Remove the edittypes tag
                                        elem = xml.etree.ElementTree.parse(folderpath + "\\" + file)
                                        root = elem.getroot()
                                        for child in root:
                                            if child.tag == "edittypes":
                                                root.remove(child)
                                        elem.write(stylesFolder + "\\" + file)
                                        #Load the style
                                        layer.layer().loadNamedStyle(stylesFolder + "\\" + file)
                        self.iface.mapCanvas().refreshAllLayers()
                except (WindowsError, IOError):
                    QMessageBox.about(self.dlg,"Error","The folder could not be found")
                except:
                    QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))


    #to textfile
    def exportPolygons(self):
        #Getting recentpaths
        recentPaths = self.getRecentPaths(self.dlg4,6,9)
        # show the dialog
        self.dlg4.show()
        # Run the dialog event loop
        result = self.dlg4.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            folderpath = self.dlg4.textEdit.currentText()
            self.updateRecentPaths(folderpath,6,9,recentPaths)
            #Do the work
            try:
                layers = self.iface.legendInterface().layers()
                for layer in layers:
                    if layer.wkbType()==3:
                        output_file = codecs.open(folderpath + "\\" + layer.name() + ".txt", 'w',encoding='utf-8')
                        output_file.write("CatchID, Sqn, X, Y\n")
                        for feature in layer.getFeatures():
                            id = feature.attributes()[0]
                            i = 1
                            geo = feature.geometry()
                            #The first item of polygon is the polyline of the outer ring
                            if geo.isMultipart():
                                multi_polygon = geo.asMultiPolygon()
                                j = 1
                                for polygon in geo.asMultiPolygon():
                                    for point in polygon[0]:
                                        output_file.write(id + "&&" + str(j) + "\t" + str(i) + "\t" + str(point.x()) + "\t" + str(point.y()) + "\n")
                                        i += 1
                                    j+=1
                            else:
                                polygon = geo.asPolygon()
                                for point in polygon[0]:
                                    output_file.write(id + "&&1" + "\t" + str(i) + "\t" + str(point.x()) + "\t" + str(point.y()) + "\n")
                                    i += 1

                        output_file.close()
            except (WindowsError, IOError):
                QMessageBox.about(self.dlg,"Error","The folder could not be found")
            except:
                QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))

    def exportShapefiles(self):
        #Getting recentpaths
        recentPaths = self.getRecentPaths(self.dlg3,3,6)
        # show the dialog
        self.dlg3.show()
        # Run the dialog event loop
        result = self.dlg3.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            folderpath = self.dlg3.textEdit.currentText()
            self.updateRecentPaths(folderpath,3,6,recentPaths)
            try:
                #Save layers as shapefiles
                layers = self.iface.legendInterface().selectedLayers()
                for layer in layers:
                    if type(layer) is QgsVectorLayer:
                        QgsVectorFileWriter.writeAsVectorFormat(layer,
                            folderpath + "\\" + layer.name() + ".shp","ascii", layer.crs() ,"ESRI Shapefile")
            except (WindowsError, IOError):
                QMessageBox.about(self.dlg,"Error","The folder could not be found")
            except:
                QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))

    def moveLines(self, layerId, geoMap):
        pointLayer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        pr = pointLayer.dataProvider()
        changedPoints = {}
        for featureId, geo in geoMap.items():
            for feature in pointLayer.getFeatures(QgsFeatureRequest(featureId)):
                #Update pointLayer attribute values for X and Y
                changedAttributes = {}
                changedAttributes[pointLayer.fieldNameIndex('X_POINT')] = float(geo.asPoint().x())
                changedAttributes[pointLayer.fieldNameIndex('Y_POINT')] = float(geo.asPoint().y())
                changedPoints[featureId] = changedAttributes
                #Get and snap all relevant lines
                layers = self.iface.legendInterface().layers()
                for lineLayer in layers:
                    if lineLayer.wkbType()==2:
                        lineLayer.startEditing()
                        #Fix all "fromnodes" for Catchment
                        if pointLayer.name() == "Catchment":
                            if lineLayer.name() == "CatchCon":
                                catchmuid = feature['CatchMUID']
                                expr = QgsExpression( "\"CatchID\"='{}'".format(catchmuid))
                                for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                                    points = lineFeature.geometry().asPolyline()
                                    points = points[1:]
                                    points.insert(0,feature.geometry().asPoint())
                                    lineLayer.changeGeometry(lineFeature.id(),QgsGeometry.fromPolyline(points))
                        #Fix all "fromnodes" for Load
                        elif pointLayer.name() == "Load":
                            if lineLayer.name() == "LoadCon":
                                muid = feature['MUID']
                                expr = QgsExpression( "\"MUID\"='{}'".format(muid))
                                for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                                    points = lineFeature.geometry().asPolyline()
                                    points = points[1:]
                                    points.insert(0,feature.geometry().asPoint())
                                    lineLayer.changeGeometry(lineFeature.id(),QgsGeometry.fromPolyline(points))
                        elif pointLayer.name() == "Node":
                            #Fix all from- and tonode for Node
                            muid = feature['MUID']
                            if lineLayer.name() == "CatchCon":
                                expr = QgsExpression( "\"NodeID\"='{}'".format(muid))
                                for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                                    points = lineFeature.geometry().asPolyline()
                                    points = points[:-1]
                                    points.append(feature.geometry().asPoint())
                                    lineLayer.changeGeometry(lineFeature.id(),QgsGeometry.fromPolyline(points))
                            elif lineLayer.name() == "LoadCon":
                                expr = QgsExpression( "\"MOUSENodeID\"='{}'".format(muid))
                                for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                                    points = lineFeature.geometry().asPolyline()
                                    points = points[:-1]
                                    points.append(feature.geometry().asPoint())
                                    lineLayer.changeGeometry(lineFeature.id(),QgsGeometry.fromPolyline(points))
                            else:
                                expr = QgsExpression( "\"FROMNODE\"='{}'".format(muid))
                                for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                                    points = lineFeature.geometry().asPolyline()
                                    points = points[1:]
                                    points.insert(0,feature.geometry().asPoint())
                                    lineLayer.changeGeometry(lineFeature.id(),QgsGeometry.fromPolyline(points))
                                expr = QgsExpression( "\"TONODE\"='{}'".format(muid))
                                for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                                    points = lineFeature.geometry().asPolyline()
                                    points = points[:-1]
                                    points.append(feature.geometry().asPoint())
                                    lineLayer.changeGeometry(lineFeature.id(),QgsGeometry.fromPolyline(points))
                        lineLayer.commitChanges()
        pr.changeAttributeValues(changedPoints)
        self.iface.mapCanvas().refreshAllLayers()

    def moveLinesToNewNodes(self, layerId, changedAttributesMap):
        lineLayer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        layerName = lineLayer.name()
        pr = lineLayer.dataProvider()
        for featureId, qgsAttributeMap in changedAttributesMap.items():
            fromChanged = False
            #Getting the line feature
            for f in lineLayer.getFeatures(QgsFeatureRequest(featureId)):
                lineFeature = f
            for fieldID, newValue in qgsAttributeMap.items():
                field = lineLayer.attributeDisplayName(fieldID)
                if layerName=="CatchCon":
                    if field == "CatchID":
                        catchLayer = QgsMapLayerRegistry.instance().mapLayersByName("Catchment")[0]
                        expr = QgsExpression( "\"CatchMUID\"='{}'".format(newValue))
                        for catchFeature in catchLayer.getFeatures( QgsFeatureRequest(expr)):
                            points = lineFeature.geometry().asPolyline()
                            points = points[1:]
                            points.insert(0,catchFeature.geometry().asPoint())
                            geoMap = {}
                            geoMap[featureId] = QgsGeometry.fromPolyline(points)
                            pr.changeGeometryValues(geoMap)
                            fromChanged = True
                    if field == "NodeID":
                        nodeLayer = QgsMapLayerRegistry.instance().mapLayersByName("Node")[0]
                        expr = QgsExpression( "\"MUID\"='{}'".format(newValue))
                        for nodeFeature in nodeLayer.getFeatures( QgsFeatureRequest(expr)):
                            if not fromChanged:                                
                                points = lineFeature.geometry().asPolyline()
                            points = points[:-1]
                            points.append(nodeFeature.geometry().asPoint())
                            geoMap = {}
                            geoMap[featureId] = QgsGeometry.fromPolyline(points)
                            pr.changeGeometryValues(geoMap)
                elif layerName=="LoadCon":
                    if field == "MUID":
                        loadLayer = QgsMapLayerRegistry.instance().mapLayersByName("Load")[0]
                        expr = QgsExpression( "\"MUID\"='{}'".format(newValue))
                        for loadFeature in loadLayer.getFeatures( QgsFeatureRequest(expr)):
                            points = lineFeature.geometry().asPolyline()
                            points = points[1:]
                            points.insert(0,loadFeature.geometry().asPoint())
                            geoMap = {}
                            geoMap[featureId] = QgsGeometry.fromPolyline(points)
                            pr.changeGeometryValues(geoMap)
                            fromChanged = True
                    if field == "MOUSENodeID":
                        nodeLayer = QgsMapLayerRegistry.instance().mapLayersByName("Node")[0]
                        expr = QgsExpression( "\"MUID\"='{}'".format(newValue))
                        for nodeFeature in nodeLayer.getFeatures( QgsFeatureRequest(expr)):
                            if not fromChanged:                                
                                points = lineFeature.geometry().asPolyline()
                            points = points[:-1]
                            points.append(nodeFeature.geometry().asPoint())
                            geoMap = {}
                            geoMap[featureId] = QgsGeometry.fromPolyline(points)
                            pr.changeGeometryValues(geoMap)
                else:
                    nodeLayer = QgsMapLayerRegistry.instance().mapLayersByName("Node")[0]
                    expr = QgsExpression( "\"MUID\"='{}'".format(newValue))
                    for nodeFeature in nodeLayer.getFeatures( QgsFeatureRequest(expr)):
                        if field == "FROMNODE":
                            points = lineFeature.geometry().asPolyline()
                            points = points[1:]
                            points.insert(0,nodeFeature.geometry().asPoint())
                            geoMap = {}
                            geoMap[featureId] = QgsGeometry.fromPolyline(points)
                            pr.changeGeometryValues(geoMap)
                            fromChanged = True
                        if field == "TONODE":
                            if not fromChanged:                                
                                points = lineFeature.geometry().asPolyline()
                            points = points[:-1]
                            points.append(nodeFeature.geometry().asPoint())
                            geoMap = {}
                            geoMap[featureId] = QgsGeometry.fromPolyline(points)
                            pr.changeGeometryValues(geoMap)
        lineLayer.updateExtents()

    def importdlg(self):
        #Getting recentpaths
        recentPaths = self.getRecentPaths(self.dlg,0,3)
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            folderpath = self.dlg.textEdit.currentText()
            #Update combobox of recent paths by adding the new one
            self.updateRecentPaths(folderpath,0,3,recentPaths)

            #Adding progress bar
            self.iface.messageBar().clearWidgets()
            progressMessageBar = self.iface.messageBar()
            progress = QProgressBar()
            progress.setMaximum(100) 
            progress.setTextVisible(True)
            progressMessageBar.pushWidget(progress)

            #Set project title
            QgsProject.instance().setTitle(os.path.basename(os.path.normpath(folderpath)))
            #Adding a layer group
            group = QgsProject.instance().layerTreeRoot().insertGroup(0,os.path.basename(os.path.normpath(folderpath)))
            errorList = ""
            #Go through all files in the folder and find the text file
            try:
                #Add the points
                j = 0
                progress.setFormat("Loading nodes..")
                for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                    if file[-4:] == ".txt":
                        input = open(folderpath + "\\" + file, 'r')
                        inputline = input.readline()
                        i=1
                        while (inputline != "ENDOFFILE"):
                            if inputline == "POINTS\n":
                                errorList = self.points(input.readline().rstrip('\n'),input, group, errorList)
                                progress.setValue(100/3/3*i)
                                i+=1
                            elif inputline == "LINES\n":
                                j+=1
                            inputline = input.readline()
                        input.close()
                #Go through all files in the folder and find the text file
                #Add the lines
                #This is done after, because the lines will need the points for field configuration
                progress.setFormat("Loading links..")
                for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                    if file[-4:] == ".txt":
                        input = open(folderpath + "\\" + file, 'r')
                        inputline = input.readline()
                        i=1
                        while (inputline != "ENDOFFILE"):
                            if inputline == "LINES\n":
                                layername = input.readline().rstrip('\n')
                                errorList = self.lines(layername,input, group,errorList)
                                progress.setValue(100/3+100/3/j*i)
                                i+=1
                            inputline = input.readline()
                        input.close()
                #Get the polygon layer by a shapefile and create new "small polygon layer"
                progress.setFormat("Loading polygons..")
                progress.setValue(80)
                if self.dlg.checkBox.checkState():
                    large = QgsVectorLayer(self.dlg.textEdit_2.currentText(), os.path.basename(os.path.normpath(self.dlg.textEdit_2.currentText()))[:-4], "ogr")
                    self.polygonLayer(large)
                    
                else:
                    for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                        if file[-4:] == ".shp":
                            large = QgsVectorLayer(folderpath + "\\" + file, file[:-4], "ogr")
                            self.polygonLayer(large)
                #Setting styles if there
                folderpath = folderpath + "\\Style\\"
                if isdir(folderpath):
                    progress.setFormat("Applying styles..")
                    progress.setValue(90)
                    for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                        if file[-4:] == ".qml":
                            for layer in QgsMapLayerRegistry.instance().mapLayersByName(file[0:-4]):
                                layer.loadNamedStyle(folderpath+file)
                #If there's no style folder, use default style
                else:
                    stylepath = expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\DefaultStyles\\"
                    progress.setFormat("Applying styles..")
                    progress.setValue(90)
                    for file in [f for f in listdir(stylepath) if isfile(join(stylepath, f))]:
                        if file[-4:] == ".qml":
                            for layer in QgsMapLayerRegistry.instance().mapLayersByName(file[0:-4]):
                                layer.loadNamedStyle(stylepath+file)
                #Sorting layers
                layerList = [c.layer() for c in group.children()]
                my_order = {"Node":0,"Link":1,"Pump":2,"Weir":3,"Orifice":4,"Valve":5,"Catchment":6,"CatchCon":7,"Load":8,"LoadCon":9}
                sortedList = sorted(layerList,key=lambda val: my_order[val.name()])
                for idx, lyr in enumerate(sortedList):
                    group.insertLayer(idx, lyr)
                group.removeChildren(len(layerList),len(layerList))
                self.iface.mapCanvas().refreshAllLayers()
                #Display message if there were errors
                if errorList:
                    QMessageBox.about(self.dlg,"Error","The following line(s) were not added due to error:\n\n"+errorList)
            except (WindowsError, IOError):
                QMessageBox.about(self.dlg,"Error","The folder could not be found")
            except:
                QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))
            #removing progressBar
            self.iface.messageBar().clearWidgets()  

    #For importing
    def polygonLayer(self,large):
                dict_a = {}
                dict_feat_a = {}
                for feat in large.getFeatures():
                    dict_a[feat.id()] = feat['MopsID']
                    dict_feat_a[feat.id()] = feat
                catchLayer = QgsMapLayerRegistry.instance().mapLayersByName("Catchment")[0]
                dict_b = {}
                for ft in catchLayer.getFeatures():
                    dict_b[ft.id()] = ft['CatchMUID']
                int_list = list(set(dict_a.values()) & set(dict_b.values()))
                newFeatures = []

                for k, v in dict_a.iteritems():
                    if v  in int_list:
                        newFeatures.append(dict_feat_a[k])
                small = QgsVectorLayer("Polygon?crs=epsg:3044", large.name()+"_SMALL", "memory")
                fields = large.fields()
                pr = small.dataProvider()
                pr.addAttributes(fields)
                pr.addFeatures(newFeatures)
                small.updateExtents()
                #Load in the "small polygon layer" in the bottom of the layer table
                QgsMapLayerRegistry.instance().addMapLayer(small, False)
                QgsProject.instance().layerTreeRoot().addLayer(small)
                #Save MopsIDs of the small polygon layer, this is for later use if the user chooses to save changes made in the polygon layer
                aFile = open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\temp\\temp.txt",'w')
                for k, v in dict_b.iteritems():
                    aFile.write("%s\n" %v)
                aFile.close()            
            
    #For importing
    def points(self, name, input, group, errorList):
        #Set the attribute names and types
        attributes = input.readline().rstrip('\n').split(";;")
        uri = "Point?crs=epsg:3044" + self.createuri(attributes)
        vl = QgsVectorLayer(uri, name, "memory")
        vl.committedGeometriesChanges.connect(self.moveLines)
        vl.editFormConfig().setReadOnly(vl.fieldNameIndex('X_POINT'),True)
        vl.editFormConfig().setReadOnly(vl.fieldNameIndex('Y_POINT'),True)
        pr = vl.dataProvider()
        #Get all the data
        data = []
        inputline = input.readline()
        while (inputline != "ENDOFPOINTS\n"):
            data.append(inputline)
            inputline = input.readline()
        #Insert the data into the layer
        for line in data:
            try:
                fet = QgsFeature()
                lineList = line.rstrip('\n').split(";;")
                if len(lineList) != len(attributes):
                    raise
                #Read last 2 elements and use them for geometry
                y = float(lineList[-1])
                x = float(lineList[-2])
                fet.setGeometry(QgsGeometry.fromPoint(QgsPoint(x, y)))
                #Changing "NULL" to QGIS.Null
                lineList2 = []
                for item in lineList:
                    if item == "NULL":
                        item = NULL
                    lineList2.append(item)
                fet.setAttributes(lineList2)
                pr.addFeatures( [ fet ] )
                vl.updateExtents()
            except:
                errorList += line + "\n"
                #QMessageBox.about(self.dlg,"Error","The following line was not added due to an error: "+line)
        QgsMapLayerRegistry.instance().addMapLayer(vl,False)
        group.addLayer(vl)
        return errorList

    #For importing
    def lines(self, name, input, group, errorList):
        #Set the attribute names and types
        attributes = input.readline().rstrip('\n').split(";;")
        del attributes[-1:]
        uri = "LineString?crs=epsg:3044" + self.createuri(attributes)
        vl = QgsVectorLayer(uri, name, "memory")
        ############## creating ValueMaps for all kind of from- and tonodes, so only relevant points can be chosen
        nodeLayer = QgsMapLayerRegistry.instance().mapLayersByName("Node")[0]
        nodeIDs = {}
        for feature in nodeLayer.getFeatures():
            f = feature['MUID']
            nodeIDs[f] = f
        if name == 'CatchCon':
            catchmentLayer = QgsMapLayerRegistry.instance().mapLayersByName("Catchment")[0]
            catchmentIDs = {}
            for feature in catchmentLayer.getFeatures():
                f = feature['CatchMUID']
                catchmentIDs[f] = f
            vl.editFormConfig().setWidgetType(vl.fieldNameIndex('CatchID'),'ValueMap')
            vl.editFormConfig().setWidgetType(vl.fieldNameIndex('NodeID'),'ValueMap')
            vl.editFormConfig().setWidgetConfig(vl.fieldNameIndex('CatchID'),catchmentIDs)
            vl.editFormConfig().setWidgetConfig(vl.fieldNameIndex('NodeID'),nodeIDs)
        elif name == 'LoadCon':
            loadLayer = QgsMapLayerRegistry.instance().mapLayersByName("Load")[0]
            loadIDs = {}
            for feature in loadLayer.getFeatures():
                f = feature['MUID']
                loadIDs[f] = f
            vl.editFormConfig().setWidgetType(vl.fieldNameIndex('MUID'),'ValueMap')
            vl.editFormConfig().setWidgetType(vl.fieldNameIndex('MOUSENodeID'),'ValueMap')
            vl.editFormConfig().setWidgetConfig(vl.fieldNameIndex('FROMUIDMNODE'),loadIDs)
            vl.editFormConfig().setWidgetConfig(vl.fieldNameIndex('MOUSENodeID'),nodeIDs)
        else:
            vl.editFormConfig().setWidgetType(vl.fieldNameIndex('FROMNODE'),'ValueMap')
            vl.editFormConfig().setWidgetType(vl.fieldNameIndex('TONODE'),'ValueMap')
            vl.editFormConfig().setWidgetConfig(vl.fieldNameIndex('TONODE'),nodeIDs)
            vl.editFormConfig().setWidgetConfig(vl.fieldNameIndex('FROMNODE'),nodeIDs)
        ##############
        pr = vl.dataProvider()
        data = []
        inputline = input.readline()
        while (inputline != "ENDOFLINES\n"):
            data.append(inputline)
            inputline = input.readline()
        for line in data:
            try:
                lineArray = line.rstrip('\n').split(";;")
                #Getting coordinates
                cordList = lineArray.pop().split("::")
                if len(lineArray) != len(attributes):
                    raise
                geoList = []
                for cord in cordList:
                    xy = cord.split("..")
                    geoList.append(QgsPoint(float(xy[0]),float(xy[1])))
                fet = QgsFeature()
                fet.setGeometry(QgsGeometry.fromPolyline(geoList))
                #Changing "NULL" to NULL
                lineArray2 = []
                for item in lineArray:
                    if item == "NULL":
                        item = NULL
                    lineArray2.append(item)
                fet.setAttributes(lineArray2)
                pr.addFeatures( [ fet ] )
                vl.updateExtents()
            except:
                errorList += line + "\n"
                #QMessageBox.about(self.dlg,"Error","The following line was not added due to an error: "+line)  
        vl.committedAttributeValuesChanges.connect(self.moveLinesToNewNodes)
        QgsMapLayerRegistry.instance().addMapLayer(vl,False)
        group.addLayer(vl)
        return errorList

    def exportdlg(self):
        #Getting recentpaths
        recentPaths = self.getRecentPaths(self.dlg2,9,12)
        # show the dialog
        self.dlg2.show()
        # Run the dialog event loop
        result = self.dlg2.exec_()
        # See if OK was pressed
        if result:
            #Update combobox of recent paths by adding the new one
            filepath = self.dlg2.textEdit.currentText()
            self.updateRecentPaths(filepath,9,12,recentPaths)
            #Do the work
            try:
                output_file = codecs.open(filepath, 'w',encoding='utf-8')
                layers = self.iface.legendInterface().layers()
                for layer in layers:
                    if type(layer) is QgsVectorLayer:
                        if layer.wkbType()==1:
                            self.writePoint(layer,output_file)
                        if layer.wkbType()==2:
                            self.writeLine(layer,output_file)
                output_file.write("ENDOFFILE")
                output_file.close()
            except (WindowsError):
                QMessageBox.about(self.dlg,"Error","The filepath could not be found")
            except:
                QMessageBox.about(self.dlg,"Error","Unexpected error: " + str(traceback.format_exc()))

    def writePoint(self,layer,output_file):
        #print type and name
        output_file.write("POINTS\n")
        output_file.write(layer.name() + '\n')
        #print heading of features
        fields = layer.pendingFields()
        fieldnames = [field.name() for field in fields]
        line = ""
        for field in fields:
            line += field.name() + ".." + field.typeName()
            if field.typeName() == "string":
                line += "::" + str(field.length())
            line += ";;"
        line = line[:-2] + "\n"
        output_file.write(line)
        #print features
        for f in layer.getFeatures():
            line = ';;'.join(unicode(f[x]) for x in fieldnames) + '\n'
            output_file.write(line)
        output_file.write("ENDOFPOINTS\n")
        
    def writeLine(self,layer,output_file):
        #print type and name
        output_file.write("LINES\n")
        output_file.write(layer.name() + '\n')
        #print heading of features
        fields = layer.pendingFields()
        fieldnames = [field.name() for field in fields]
        line = ""
        for field in fields:
            line += field.name() + ".." + field.typeName()
            if field.typeName() == "string":
                line += "::" + str(field.length())
            line += ";;"
        #add coordinates heading
        line += "Points\n"
        output_file.write(line)
        #print features
        for f in layer.getFeatures():
            line = ';;'.join(unicode(f[x]) for x in fieldnames) + ";;"
            geom = f.geometry()
            for point in geom.asPolyline():
                line += str(point.x()) + ".." + str(point.y()) + "::"
            line = line[:-2] + "\n"
            output_file.write(line)
        output_file.write("ENDOFLINES\n")

    
    def select_input_folder(self, dialog):
        foldername = QFileDialog.getExistingDirectory(dialog, "Select input folder ", dialog.textEdit.currentText(), QFileDialog.DontUseNativeDialog)
        dialog.textEdit.lineEdit().setText(foldername)
    
    def select_output_file(self, dialog, fileType, text):
        filename = QFileDialog.getSaveFileName(dialog, text, dialog.textEdit.currentText(), fileType)
        dialog.textEdit.lineEdit().setText(filename)

    def select_output_folder(self, dialog):
        foldername = QFileDialog.getExistingDirectory(dialog, "Select output folder ", dialog.textEdit.currentText(), QFileDialog.DontUseNativeDialog)
        dialog.textEdit.lineEdit().setText(foldername)

    def select_output_dlg5(self):
        filename = QFileDialog.getOpenFileName(self.dlg5, "Select larger layer ", self.dlg5.textEdit.currentText(), '*.shp')
        self.dlg5.textEdit.lineEdit().setText(filename)

    def select_input_file(self, dialog, fileType, text):
        filename = QFileDialog.getOpenFileName(dialog, text, dialog.textEdit.currentText(), fileType)
        dialog.textEdit.lineEdit().setText(filename)

    def importCatchment(self):
        filename = QFileDialog.getOpenFileName(self.dlg, "Select the catchment shapefile", self.dlg.textEdit.currentText(), '*.shp')
        self.dlg.textEdit_2.lineEdit().setText(filename)

    def createuri(self, attributes):
        uri = "";
        for attribute in attributes:
            attributeSplit = attribute.split("..")
            if "string" in attributeSplit[1]:
                as2 = attributeSplit[1].split("::")
                uri = uri + "&field=" + attributeSplit[0] + ":string(" + as2[1] + ")"
            elif "integer" in attributeSplit[1]:
                uri = uri + "&field=" + attributeSplit[0] + ":integer"
            elif "double" in attributeSplit[1]:
                uri = uri + "&field=" + attributeSplit[0] + ":double"
        return uri

    def getRecentPaths(self,dialog,lowNum,highNum):
        recentFile = codecs.open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\" + "RecentPaths.txt", 'r', encoding='utf-8')
        content = recentFile.readlines()
        recentFile.close()
        content = [x.strip() for x in content]
        dialog.textEdit.clear()
        dialog.textEdit.addItems(content[lowNum:highNum])
        return content

    def updateRecentPaths(self,folderpath,lowNum,highNum,content):
        #If it's not in recentPaths or at the bottom, add it to the top of the list 
        if folderpath not in content[lowNum:highNum] or folderpath == content[lowNum+2]:
            content[lowNum+2] = content[lowNum+1]
            content[lowNum+1] = content[lowNum]
            content[lowNum] = folderpath
            output_file = codecs.open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\" + "RecentPaths.txt", 'w', encoding='utf-8')
            for line in content:
                output_file.write(line+"\n")
            output_file.close()
        #If it's in the middle
        elif content.index(folderpath)-lowNum == 1:
            content[lowNum+1] = content[lowNum]
            content[lowNum] = folderpath
            output_file = codecs.open(expanduser("~") + "\\.qgis2\\python\\plugins\\mops\\" + "RecentPaths.txt", 'w', encoding='utf-8')
            for line in content:
                output_file.write(line+"\n")
            output_file.close()

    def importCheckBox(self,state):
        if state == 2:
            self.dlg.textEdit_2.setShown(True)
            self.dlg.pushButton_2.setShown(True)
        else:
            self.dlg.textEdit_2.setShown(False)
            self.dlg.pushButton_2.setShown(False)
            
            
    def groupChanged(self):
        try:
            groupName = self.dlg10.comboBox.currentText()
            self.dlg10.listWidget.clear()
            root = QgsProject.instance().layerTreeRoot()
            mygroup = root.findGroup(groupName)
            for layer in mygroup.children():
                if isinstance(layer,QgsLayerTreeLayer):
                    self.dlg10.listWidget.addItem(layer.name())
        except:
            pass
        