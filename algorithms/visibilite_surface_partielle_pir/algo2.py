# -*- coding: utf-8 -*-

"""
/***************************************************************************
 ClassName
                                 A QGIS plugin
 Description du plugin
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-11-20
        copyright            : (C) 2019 by Cécile Duchêne, ENSG
        email                : cecile.duchene@ensg.eu
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

__author__ = 'Charles d\'Andigne et Amina Barmani, ENSG, IGN, LaSTIG'
__date__ = '2019-11-20'
__copyright__ = '(C) 2019 by Charles d\'Andigne et Amina Barmani, ENSG, IGN, LaSTIG'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


import os
import processing
from qgis.PyQt.QtCore import (QCoreApplication,QVariant)
from qgis.core import (QgsProcessing,
                       QgsFeatureSink,
                       QgsProcessingAlgorithm,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterRasterDestination,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterNumber,
                       QgsProcessingOutputLayerDefinition,
                       QgsFeature,
                       QgsField,
                       QgsFields,
                       QgsWkbTypes,
                       QgsVectorLayer)


class Algo2(QgsProcessingAlgorithm):
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

    INPUT = 'INPUT'
    INPUT_MNT='INPUT_MNT'
    OUTPUT = 'OUTPUT'
    OUTPUT_DBH = 'OUTPUT_DBH'
    OUTPUT_PASSIVE = 'OUTPUT_PASSIVE'

    def initAlgorithm(self, config):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        """

        # We add the input vector features source.
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Couche de point'),
                [QgsProcessing.TypeVectorPoint]
            )
        )
        # MNT
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.INPUT_MNT,
                self.tr('Modèle Numérique de terrain')
            )
        )
        # We add a feature sink in which to store our processed features (this
        # usually takes the form of a newly created vector layer when the
        # algorithm is run in QGIS).
        #Couche de points de vue
        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Couche point de vue ')
            )
        )
        ## OUTPUT_DBH
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT_DBH,
                "OUTPUT_DBH", None, False))
        ##OUTPUT_PASSIVE
        self.addParameter(
            QgsProcessingParameterRasterDestination(
                self.OUTPUT_PASSIVE,
                self.tr('OUTPUT_PASSIVE')))

    def processAlgorithm(self, parameters, context, feedback):
        """
        Here is where the processing itself takes place.
        """
        # Retrieve the feature source and sink. The 'dest_id' variable is used
        # to uniquely identify the feature sink, and must be included in the
        # dictionary returned by the processAlgorithm function.
        source = self.parameterAsSource(parameters, self.INPUT, context)
        MNT = self.parameterAsRasterLayer(parameters, self.INPUT_MNT, context)

        # La couche de sortie est une couche point avec un champ ID
        output_fields = QgsFields()
        #output_fields.append(QgsField("ID", QVariant.Int))
        #output_fields.append(QgsField("observ_hgt", QVariant.Double))
        #output_fields.append(QgsField("raduis", QVariant.Double))
        (sink, dest_id) = self.parameterAsSink(parameters, self.OUTPUT,
                context, output_fields , QgsWkbTypes.Point , source.sourceCrs())

        # Compute the number of steps to display within the progress bar and
        # get features from source
        total = 100.0 / source.featureCount() if source.featureCount() else 0

        #Définir les couches
        features = source.getFeatures()

        input_path = parameters['INPUT']
        print(input_path)
        output_path = parameters['OUTPUT']
        print(output_path)

        #input_layer=QgsVectorLayer(input_path)
        #pts_vue_output = QgsVectorLayer(output_path,"output_layer","ogr")

        #The input parameters can be accessed as a dictionary object so parameters['INPUT'] will give the  path to a layer
        sink=processing.run("Choucas:Création de point de vue",
                       {'OBSERVER_POINTS': input_path,
                        'DEM': MNT,
                        'OBSERVER_ID': 'ID',
                        'RADIUS': 5000,
                        'RADIUS_FIELD': None,
                        'OBS_HEIGHT': 0,
                        'OBS_HEIGHT_FIELD': None,
                        'TARGET_HEIGHT': 0,
                        'TARGET_HEIGHT_FIELD': None,
#                        'OUTPUT': QgsProcessingOutputLayerDefinition(output_path)})['OUTPUT']
                        'OUTPUT': output_path})['OUTPUT']

        #sink.addFeature(out['OUTPUT'], QgsFeatureSink.FastInsert)
        """
        for current, feature in enumerate(features):
            # Stop the algorithm if cancel button has been clicked
            if feedback.isCanceled():
                break

            # *** Ici appeler la methode qui construit l'objet modifié (ou créé) en sortie
            # à partir de l'objet en entrée (variable feature) ***
            # Il faudra alors remplacer dans la ligne ci-dessous la variable "feature"
            # par la variable contenant l'objet en sortie
            # Pour l'instant on met juste un petit message pour dire qu'on passe par là

            print('Avant traitement')


            # Update the progress bar
            feedback.setProgress(int(current * total))
            """

        # Return the results of the algorithm. In this case our only result is
        # the feature sink which contains the processed features, but some
        # algorithms may return multiple feature sinks, calculated numeric
        # statistics, etc. These should all be included in the returned
        # dictionary, with keys matching the feature corresponding parameter
        # or output names.
        #return {self.OUTPUT: dest_id}
        return {self.OUTPUT:sink}

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'Visibilite_passive_pts_aleatoires'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr(self.name())

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
        return 'visibilite_surface_partielle_pir'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return Algo2()