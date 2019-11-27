# -*- coding: utf-8 -*-

"""
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""


from .viewshed_points import ViewshedPoints
from .viewshed_raster import ViewshedRaster
from .viewshed_intervisibility import Intervisibility
from .viewshed_horizon_depth import HorizonDepth

from .modules import visibility as ws
from .modules import Points as pts
from .modules import Raster as rst

from plugins.processing.gui import MessageBarProgress
from PyQt5.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                        QgsFeatureSink,
                        QgsProcessingException,
                        QgsProcessingAlgorithm,
                        QgsProcessingParameterRasterLayer,
                        QgsProcessingParameterFeatureSource,
                        QgsProcessingParameterFeatureSink,
                        QgsProcessingParameterNumber,
                        QgsProcessingParameterRasterDestination,
                        QgsProcessingOutputRasterLayer,
                        QgsWkbTypes,
                        QgsProcessingParameterBoolean,
                        QgsProcessingParameterField,
                        QgsProcessingParameterEnum ,
                        QgsProcessingParameterFile,
                        QgsMessageLog,
                        QgsRasterLayer)

import processing
import numpy as np
import time



class PassiveViewshed_Pt_MNS(QgsProcessingAlgorithm):
    """
    This is an example algorithm that takes a vector layer and
    creates a new identical one.

    It is meant to be used as an example of how to create your own
    algorithms and explain methods and variables used to do it. An
    algorithm like this will be available in all elements, and there
    is not need for additional work.

    All Processing algorithms should extend the QgsProcessingAlgorithm
    class.
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.


##    DEM = 'DEM'
    MNS = 'MNS'
    OBSERVER_POINTS = 'OBSERVER_POINTS'
    MNE='MNE'

    INPUT_Hobs = 'Hobs'
    USE_CURVATURE = 'USE_CURVATURE'
    REFRACTION = 'REFRACTION'
    PRECISION = 'PRECISION'
    OPERATOR = 'OPERATOR'
    OUTPUT_DBH = 'OUTPUT_DBH'
    OUTPUT_PASSIVE='OUTPUT_PASSIVE'
    OUTPUT_ACTIVE='OUTPUT_ACTIVE'


    PRECISIONS = ['Coarse','Normal', 'Fine']


    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return PassiveViewshed_Pt_MNS()

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Calcul de la vision active, passive et le raster depth below horizon à partir du point d observation et du MNS '

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Vision active,passive et dbh à partir du Pt Obs et MNS')

    def group(self):
        """
        Returns the name of the group this algorithm belongs to. This string
        should be localised.
        """
        return self.tr(self.groupId())

    def groupId(self):
        """
        Returns the unique ID of the group this algorithm belongs to. This
        string should be fixed for the algorithm, and must not be localised.
        The group id should be unique within each provider. Group id should
        contain lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'visibilite_passive_stage'

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        return self.tr("Calcul de la vision active, passive et le raster depth below horizon à partir du point d observation et du MNS")

    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # les données et les paramètres en entrée

        #point d observation
        self.addParameter(
            QgsProcessingParameterFeatureSource(

            self.OBSERVER_POINTS,
            self.tr("Point d'observation"),
            [QgsProcessing.TypeVectorPoint]))
        #hauteur de l observateur
        self.addParameter(QgsProcessingParameterNumber(
            self.INPUT_Hobs,
                "Hauteur d'observation",
                QgsProcessingParameterNumber.Double,1.60))

        #MNE
        self.addParameter(QgsProcessingParameterRasterLayer
                          (self.MNE,
            self.tr("Model Numerique d'Elevation")))

        #MNS
        self.addParameter(QgsProcessingParameterRasterLayer
                          (self.MNS,
            self.tr('Modele Numerique de Surface')))

        #courbure de la terre
        self.addParameter(QgsProcessingParameterBoolean(
            self.USE_CURVATURE,
            self.tr('Courbure de la terre'),
            True))

        #refraction atmospherique
        self.addParameter(QgsProcessingParameterNumber(
            self.REFRACTION,
            self.tr('réfraction atmosphérique'),
            1, 0.13, False, 0.0, 1.0))



        ## OUTPUT_DBH
        self.addParameter(QgsProcessingParameterRasterDestination(
            self.OUTPUT_DBH,
                "OUTPUT_DBH",None, False))

        ##OUTPUT_PASSIVE
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT_PASSIVE,
                    self.tr('OUTPUT_PASSIVE')))


    def processAlgorithm(self, parameters, context, feedback):

        raster = self.parameterAsRasterLayer(parameters,self.MNS, context)
        mne=self.parameterAsRasterLayer(parameters,self.MNE, context)
        observers = self.parameterAsSource(parameters,self.OBSERVER_POINTS,context)

        useEarthCurvature = self.parameterAsBool(parameters,self.USE_CURVATURE,context)
        refraction = self.parameterAsDouble(parameters,self.REFRACTION,context)
        precision = 1

        operator = self.parameterAsInt(parameters,self.OPERATOR,context) + 1


        ########################################################################
        ####                Calcul du DBH     ##################################
        analysis_type = 1  #pour le calcul des diff angl
        output_path_dbh = self.parameterAsOutputLayer(parameters,self.OUTPUT_DBH,context)

        raster_path= raster.source()
        dem = rst.Raster(raster_path, output=output_path_dbh)

        points = pts.Points(observers)

        fields =["observ_hgt", "radius"]
        miss = points.test_fields(fields)

        if miss:
            err= " \n ****** \n ERROR! \n Missing fields: \n" + "\n".join(miss)
            feedback.reportError(err, fatalError = True)
            raise QgsProcessingException(err)

        points.take(dem.extent, dem.pix)

        if points.count == 0:
            err= "  \n ******* \n ERROR! \n No viewpoints in the chosen area!"
            feedback.reportError(err, fatalError = True)
            raise QgsProcessingException(err )

        elif points.count == 1:
            operator=0
            live_memory = False

        else:
            live_memory = ( (dem.size[0] * dem.size[1]) / 1000000 <
                           float(ProcessingConfig.getSetting(
                               'MEMORY_BUFFER_SIZE')))

        #has to be assigned before write_outpur routine because the
        #operator variable determines raster background value [opaque ...]
        dem.set_buffer(operator, live_memory = live_memory)

        # prepare the output raster
        if not live_memory:
            dem.write_output(output_path_dbh) #, fill = np.nan) [not needed]


        pt = points.pt #this is a dict of obs. points


        start = time.clock(); report=[]


        #for speed and convenience, use maximum sized window for all analyses
        #this is not clear! should set using entire size, not radius !!
        dem.set_master_window(points.max_radius,
                            size_factor = precision ,
                            background_value=np.nan,
                            pad = precision>0,
                            curvature =useEarthCurvature,
                            refraction = refraction )


        cnt = 0

        for id1 in pt :



            if feedback.isCanceled():  break


            matrix_vis = ws.viewshed_raster (analysis_type, pt[id1], dem,
                                          interpolate = precision > 0)

            # the algorithm is giving angular difference
            matrix_vis *= - dem.mx_dist
            matrix_vis[dem.radius_pix, dem.radius_pix ]=0


            # must set mask before writing the result!
            dem.set_mask( pt[id1]["radius"])

            r = dem.add_to_buffer (matrix_vis, report = True)

            report.append([pt[id1]["id"],*r])

            # dem contient le resultat

            cnt += 1

            feedback.setProgress(int((cnt/points.count) *100))

        #M: memory layers for intermediate calculation



        if live_memory: dem.write_output(output_path_dbh)

        dem = None


##        txt = ("\n Analysis time: " + str(
##                            round( (time.clock() - start
##                                    ) / 60, 2)) + " minutes."
##              " \n.      RESULTS \n Point_ID, non-visible pixels, total pixels" )
##
##        for l in report:
##            txt = txt + "\n" + ' , '.join(str(x) for x in l)
##
##
##        QgsMessageLog.logMessage( txt, "Viewshed info")
##
##        results = {}
##
##        for output in self.outputDefinitions():
##            outputName = output.name()
##
##            if outputName in parameters :
##                results[outputName] = parameters[outputName]

        ##############################################################
        raster_dbh = QgsRasterLayer(output_path_dbh, "DBH")
        raster_mne = self.parameterAsRasterLayer(parameters,self.MNE, context)

        Hobs=parameters[self.INPUT_Hobs]

        # DBH[j]+ altitude_mne[j]<=Hobs
        # (A+B)<=Hobs


        formule='(A+B)<=' + str(Hobs)
        #calculate

        #calcul du passive viewshed mns
        algresult =processing.run("gdal:rastercalculator",
        {'INPUT_A':raster_dbh,
        'BAND_A':1,
        'INPUT_B':raster_mne,
        'BAND_B':1,
        'INPUT_C':None,
        'BAND_C':-1,
        'INPUT_D':None,
        'BAND_D':-1,
        'INPUT_E':None,
        'BAND_E':-1,
        'INPUT_F':None,
        'BAND_F':-1,
        'FORMULA':formule,
        'NO_DATA':None,
        'RTYPE':2,
        'OPTIONS':'',
        'OUTPUT':parameters[self.OUTPUT_PASSIVE]},
        context=context, feedback=feedback, is_child_algorithm=True)

        viewshed = algresult['OUTPUT']

        return {self.OUTPUT_PASSIVE: viewshed}
