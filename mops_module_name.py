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
        email                : kontakt@lnhwater.dk
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
#from qgis.core import QgsVectorLayer, QgsFeature, QgsGeometry, QgsPoint, QgsMapLayerRegistry, QgsVectorFileWriter
from qgis.core import *
from PyQt4.QtGui import QAction, QIcon, QFileDialog
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from mops_module_name_dialog import importDialog
from mops_module_save import saveDialog
from mops_module_export_shapefiles import exportShapefilesDialog
from os.path import isfile, join, expanduser
import os.path
from os import listdir


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

        # Create the dialog (after translation) and keep reference
        self.dlg = importDialog()
        #self.dlg.textEdit.clear()
        self.dlg.textEdit.setText("E:\Desktop\TestModel_MUQGIS")
        self.dlg.pushButton.clicked.connect(self.select_input_folder)
        self.dlg2 = saveDialog()
        self.dlg2.textEdit.clear()
        self.dlg2.pushButton.clicked.connect(self.select_output_file)
        self.dlg3 = exportShapefilesDialog()
        self.dlg3.textEdit.clear()
        self.dlg3.pushButton.clicked.connect(self.select_output_folder)
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
            text=self.tr(u'Export'),
            callback=self.exportdlg,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path,
            text=self.tr(u'Save all layers as Shapefiles'),
            callback=self.exportShapefiles,
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

    def exportShapefiles(self):
        # show the dialog
        self.dlg3.show()
        # Run the dialog event loop
        result = self.dlg3.exec_()
        # See if OK was pressed
        if result:
            layers = self.iface.legendInterface().layers()
            foldername = self.dlg3.textEdit.toPlainText()
            for layer in layers:
                QgsVectorFileWriter.writeAsVectorFormat(layer,
                    foldername + "\\" + layer.name() + ".shp","utf-8", layer.crs() ,"ESRI Shapefile")


    def moveLines(self, layerId, geoMap):
        pointLayer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        for featureId, geo in geoMap.items():
            for feature in pointLayer.getFeatures(QgsFeatureRequest(featureId)):
                layers = self.iface.legendInterface().layers()
                for lineLayer in layers:
                    if lineLayer.wkbType()==2:
                        lineLayer.startEditing()
                        if pointLayer.name() == "Catchment":
                            if lineLayer.name() == "CatchCon":
                                catchmuid = feature['CatchMUID']
                                expr = QgsExpression( "\"CatchID\"='{}'".format(catchmuid))
                                for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                                    points = lineFeature.geometry().asPolyline()
                                    points = points[1:]
                                    points.insert(0,feature.geometry().asPoint())
                                    lineLayer.changeGeometry(lineFeature.id(),QgsGeometry.fromPolyline(points))
                        elif pointLayer.name() == "Load":
                            if lineLayer.name() == "LoadCon":
                                muid = feature['MUID']
                                expr = QgsExpression( "\"MUID\"='{}'".format(muid))
                                for lineFeature in lineLayer.getFeatures( QgsFeatureRequest(expr)):
                                    points = lineFeature.geometry().asPolyline()
                                    points = points[1:]
                                    points.insert(0,feature.geometry().asPoint())
                                    lineLayer.changeGeometry(lineFeature.id(),QgsGeometry.fromPolyline(points))
                        else:
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

    def importdlg(self):
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            folderpath = self.dlg.textEdit.toPlainText()
            #Go through all files in the folder
            for file in [f for f in listdir(folderpath) if isfile(join(folderpath, f))]:
                if file[-4:] == ".txt":
                    input = open(folderpath + "\\" + file, 'r')
                    inputline = input.readline()
                    while (inputline != "ENDOFFILE"):
                        if inputline == "POINT\n":
                            self.points(input)
                        elif inputline == "LINES\n":
                            self.lines(input)
                        inputline = input.readline()
                if file[-4:] == ".shp":
                    layer = self.iface.addVectorLayer(folderpath + "\\" + file, file[:-4], "ogr")

    #For importing
    def points(self,input):
        name = input.readline().rstrip('\n')
        #Set the attribute names and types
        attributes = input.readline().rstrip('\n').split(";;")
        del attributes[-2:]
        uri = "Point?crs=epsg:4326" + self.createuri(attributes)
        vl = QgsVectorLayer(uri, name, "memory")
        vl.committedGeometriesChanges.connect(self.moveLines)
        pr = vl.dataProvider()
        #Get all the data
        data = []
        inputline = input.readline()
        while (inputline != "ENDOFPOINTS\n"):
            data.append(inputline)
            inputline = input.readline()
        #Insert the data into the layer
        for line in data:
            fet = QgsFeature()
            lineList = line.rstrip('\n').split(";;")
            #Remove last 2 elements and use them for geometry
            y = float(lineList.pop())
            x = float(lineList.pop())
            fet.setGeometry(QgsGeometry.fromPoint(QgsPoint(x, y)))
            fet.setAttributes(lineList)
            pr.addFeatures( [ fet ] )
            vl.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(vl)

    #For importing
    def lines(self,input):
        name = input.readline().rstrip('\n')
        #Set the attribute names and types
        attributes = input.readline().rstrip('\n').split(";;")
        del attributes[-1:]
        uri = "LineString?crs=epsg:4326" + self.createuri(attributes)
        vl = QgsVectorLayer(uri, name, "memory")
        pr = vl.dataProvider()
        data = []
        inputline = input.readline()
        while (inputline != "ENDOFLINES\n"):
            data.append(inputline)
            inputline = input.readline()
        for line in data:
            lineArray = line.rstrip('\n').split(";;")
            #Getting coordinates
            cordList = lineArray.pop().split("::")
            geoList = []
            for cord in cordList:
                xy = cord.split("..")
                geoList.append(QgsPoint(float(xy[0]),float(xy[1])))
            fet = QgsFeature()
            fet.setGeometry(QgsGeometry.fromPolyline(geoList))
            fet.setAttributes(lineArray)
            pr.addFeatures( [ fet ] )
            vl.updateExtents()
        QgsMapLayerRegistry.instance().addMapLayer(vl)

    def exportdlg(self):
        # show the dialog
        self.dlg2.show()
        # Run the dialog event loop
        result = self.dlg2.exec_()
        # See if OK was pressed
        if result:
            filename = self.dlg2.textEdit.toPlainText()
            output_file = open(filename, 'w')
            layers = self.iface.legendInterface().layers()
            for layer in layers:
                if layer.wkbType()==1:
                    self.writePoint(layer,output_file)
                if layer.wkbType()==2:
                    self.writeLine(layer,output_file)
            output_file.write("ENDOFFILE")
            output_file.close()

    def writePoint(self,layer,output_file):
        #print type and name
        output_file.write("POINT\n")
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
        line += "X_POINT;;Y_POINT\n"
        output_file.write(line)
        #print features
        for f in layer.getFeatures():
            line = ';;'.join(unicode(f[x]) for x in fieldnames)
            geom = f.geometry()
            line += ";;" + str(geom.asPoint().x()) + ";;" + str(geom.asPoint().y()) + "\n"
            unicode_line = line.encode('utf-8')
            output_file.write(unicode_line)
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
            unicode_line = line.encode('utf-8')
            output_file.write(unicode_line)
        output_file.write("ENDOFLINES\n")

    def select_output_file(self):
        filename = QFileDialog.getSaveFileName(self.dlg2, "Select output file ","", '*.txt')
        self.dlg2.textEdit.setText(filename)

    """def select_input_file(self):
        filename = QFileDialog.getOpenFileName(self.dlg, "Select input file ","", '*.txt')
        self.dlg.textEdit.setText(filename)"""
    
    def select_input_folder(self):
         foldername = QFileDialog.getExistingDirectory(self.dlg, "Select input folder ", expanduser("~"), QFileDialog.ShowDirsOnly)
         self.dlg.textEdit.setText(foldername)
    
    def select_output_folder(self):
        foldername = QFileDialog.getExistingDirectory(self.dlg3, "Select output folder ", expanduser("~"), QFileDialog.ShowDirsOnly)
        self.dlg3.textEdit.setText(foldername)

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

