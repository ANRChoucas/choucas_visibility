# -*- coding: utf-8 -*-

"""
/***************************************************************************
 Choucas_visibility
                                 A QGIS plugin
 Calcul de visibilité et des incertitudes
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2019-07-08
        copyright            : (C) 2019 by Choucas
        email                : Mohssine.Kaouadji@ign.fr
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

__author__ = 'Choucas'
__date__ = '2019-07-08'
__copyright__ = '(C) 2019 by Choucas'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

from qgis.core import QgsProcessingProvider


from processing.core.ProcessingConfig import Setting, ProcessingConfig


from PyQt5.QtGui import QIcon
from os import path

# Algos visibilite partielle stage 
from .algorithms.visibilite_passive_stage.viewshed_points import ViewshedPoints
from .algorithms.visibilite_passive_stage.viewshed_raster import ViewshedRaster
#from .algorithms.visibilite_passive_stage.viewshed_intervisibility import Intervisibility
from .algorithms.visibilite_passive_stage.viewshed_horizon_depth import HorizonDepth
from .algorithms.visibilite_passive_stage.passive_viewshed_dbh import Choucas_visibilityAlgorithm
from .algorithms.visibilite_passive_stage.passive_viewshed_dbh_mns import Choucas_visibilityAlgorithm_mns
from .algorithms.visibilite_passive_stage.Passive_viewshed_pt_dem import PassiveViewshed_Pt_DEM
from .algorithms.visibilite_passive_stage.Passive_viewshed_pt_dem_mns import PassiveViewshed_Pt_MNS
# Algos visibilite surface partielle
from .algorithms.visibilite_surface_partielle_pir.algo1 import Algo1
from .algorithms.visibilite_surface_partielle_pir.algo2 import Algo2
# Algos visibilite partielle reprise
from .algorithms.visibilite_passive_reprise.algo_reprise import AlgoReprise
#Algos VisionParCas
from .algorithms.visionparcas.observedPoint import ObservedPoint
from .algorithms.visionparcas.visibilitePassive import VisibilitePassive
from .algorithms.visionparcas.constructPtsAleatoires import ConstructPointsAleatoires
from .algorithms.visionparcas.varMultiParametres import VarMultiParametres
from .algorithms.visionparcas.ecritureParaSursol import CreateCsvSursol

class Choucas_visibilityProvider(QgsProcessingProvider):

    def __init__(self):
        """
        Default constructor.
        """
        QgsProcessingProvider.__init__(self)

    def unload(self):
        """
        Unloads the provider. Any tear-down steps required by the provider
        should be implemented here.
        """
        pass

    def loadAlgorithms(self):
        """
        Loads all algorithms belonging to this provider.
        """
        # Algos du groupe visibilite_passive_stage
        self.addAlgorithm(Choucas_visibilityAlgorithm())
        self.addAlgorithm(ViewshedPoints())
        self.addAlgorithm(ViewshedRaster())
        self.addAlgorithm(PassiveViewshed_Pt_DEM())
        self.addAlgorithm(HorizonDepth())
        self.addAlgorithm(Choucas_visibilityAlgorithm_mns())
        self.addAlgorithm(PassiveViewshed_Pt_MNS())
        # Algos du groupe visibilite_surface_partielle
        self.addAlgorithm(Algo1())
        self.addAlgorithm(Algo2())
        # Algos du groupe visibilite_passive_reprise_pir
        self.addAlgorithm(AlgoReprise())
        # Algos du groupe visionparcas
        self.addAlgorithm(ObservedPoint())
        self.addAlgorithm(VisibilitePassive())
        self.addAlgorithm(ConstructPointsAleatoires())
        self.addAlgorithm(VarMultiParametres())
        self.addAlgorithm(CreateCsvSursol())
        # add additional algorithms here

        # self.addAlgorithm(MyOtherAlgorithm())

    def id(self):
        """
        Returns the unique provider id, used for identifying the provider. This
        string should be a unique, short, character only string, eg "qgis" or
        "gdal". This string should not be localised.
        """
        return 'Choucas'

    def name(self):
        """
        Returns the provider name, which is used to describe the provider
        within the GUI.

        This string should be short (e.g. "Lastools") and localised.
        """
        return self.tr('Visibilité - Choucas')

    def icon(self):
        """
        Should return a QIcon which is used for your provider inside
        the Processing toolbox.
        """
        #return QgsProcessingProvider.icon(self)
        return QIcon(path.dirname(__file__) + '/icon.png')

    def longName(self):
        """
        Returns the a longer version of the provider name, which can include
        extra details such as version numbers. E.g. "Lastools LIDAR tools
        (version 2.2.1)". This string should be localised. The default
        implementation returns the same string as name().
        """
        return self.name()
