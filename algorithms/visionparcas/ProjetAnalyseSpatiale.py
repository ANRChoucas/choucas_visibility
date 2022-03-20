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


#from .viewshed_points import ViewshedPoints
#from .viewshed_raster import ViewshedRaster
#from .viewshed_intervisibility import Intervisibility
#from .viewshed_horizon_depth import HorizonDepth

#from .modules import visibility as ws
#from .modules import Points as pts
#from .modules import Raster as rst

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
                        QgsFeature,
                        QgsField,
                        QgsProcessingParameterBoolean,
                        QgsProcessingParameterField,
                        QgsProcessingParameterEnum ,
                        QgsProcessingParameterFile,
                        QgsMessageLog,
                        QgsRasterLayer,
                        QgsProcessingUtils,
                        QgsVectorLayer
                        )
from processing.core.ProcessingConfig import ProcessingConfig
import processing
import numpy as np
from .modules.fonctionsPlugin import FonctionsPlugin as fp
import os
import time
from qgis.PyQt.QtCore import QVariant
import gdal
from osgeo import osr
import chardet
import webbrowser
import inspect

class ProjetAnalyseSpatiale(QgsProcessingAlgorithm):
    """
    Créé x rasters de visibilité passive en fonction du nombre de variations
    pour chaque paramètre.
    
    INPUTS:
        - OBSERVED_LAYER: QgsVectorLayer (Point ou Polygone):
            Point ou polygone observé
        
        - NBPT_MIN : integer:
            Nombre de point formant le contour si OBSERVED_LAYER est un
            polygone (nombre minimum si variation).
            
        - NBPT_MAX : integer (optional):
            Nombre de points maximum formant le contour si OBSERVED_LAYER est
            un polygone.
            
        - NBPT_PASVAR : integer (optional):
            Pas de variation entre le nombre de point min et le nombre point max
            formant le contour si OBSERVED_LAYER est un polygone.
            
        - MNT : RasterLayer:
            Raster Modèle Numérique de Terrain (Projeté en Lambert93 et NoDataValue = -99999)
            
        - INPUT_DOSSIER_SHP : string (optional):
            Chemin vers le dossier contenant les fichiers SHP de sursol
            
        - INPUT_CSV : string (optional):
            Chemin vers le fichier CSV de paramétrage du sursol
            
        - VARSURSOL_DIF : boolean :
            Si True: variation du sursol en fonction des variations paramétrées
            dans le fichier CSV.
            Si False: pas de prise en compte des paramétrages de variation indiqués
            dans le fichier CSV.
            
        - VARSURSOL_INDIF : boolean :
            Si True: variation du sursol dans son ensemble en fonction de SURSOL_MIN,
            SURSOL_MAX et SURSOL_PASVAR
            Si False: pas de variation du sursol dans son ensemble.
            
        - SURSOL_MIN : float (optional):
            Variation relative minimum du MNE et du MNS si VARSURSOL_INDIF = True
            
        - SURSOL_MAX : float (optional):
            Variation relative maximum du MNE et du MNS si VARSURSOL_INDIF = True
            
        - SURSOL_PASVAR : float (optional):
            Pas de variation de la hauteur du sursol si VARSURSOL_INDIF = True
            
        - HOBS_MIN : float :
            Hauteur de l'observateur (hauteur minimum si variation)
            
        - HOBS_MAX : float (optional):
            Hauteur maximum de l'observateur
            
        - HOBS_PASVAR : float (optional):
            Pas de variation de la hauteur de l'observateur
            
        - HCIBLE_MIN : float :
            Hauteur de la cible (hauteur minimum si variation)
            
        - HCIBLE_MAX : float (optional):
            Hauteur maximum de la cible
            
        - HCIBLE_PASVAR : float (optional):
            Pas de variation de la hauteur de la cible
            
        - OUTPUT_DOSSIER : string :
            Chemin vers le dossier où seront stockés les rasters de visibilité
            passive calculés.
            
        - OUTPUT : string :
            Variable interne pour assurer un return au plugin.
            
        - OUTPUT_WEB : boolean :
            Si True : ouverture d'une page web de visualisation des résultats à
            la fin des calculs.
            
        - USE_CURVATURE : boolean :
            Si True : Prise en compte de la courbure de la Terre dans le calcul
            de visibilité passive.
            
        - RADIUS : integer :
            Paramètre pour le calcul de visibilité passive : rayon de calcul de
            visibilité passive autour du point.
        
        - OPERATOR : integer :
            Variable interne nécessaire au calcul de visibilité passive 
        
        OUTPUT :
            X fichiers.tif de raster de visibilité passive.
    
    """

    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.
    
    OBSERVED_LAYER = 'OBSERVED_LAYER'   
    
    NBPT_MIN='NBPT_MIN'
    NBPT_MAX='NBPT_MAX'
    NBPT_PASVAR = 'NBPT_PASVAR'
    
    MNT = 'MNT'
    INPUT_DOSSIER_SHP = 'INPUT_DOSSIER_SHP'    
    INPUT_CSV = 'INPUT_CSV'
    
    VARSURSOL_DIF = 'VARSURSOL_DIF'    
    VARSURSOL_INDIF = 'VARSURSOL_INDIF'
    SURSOL_MIN = 'SURSOL_MIN'
    SURSOL_MAX = 'SURSOL_MAX'
    SURSOL_PASVAR = 'SURSOL_PASVAR'
    
    HOBS_MIN = 'HOBS_MIN'
    HOBS_MAX = 'HOBS_MAX'
    HOBS_PASVAR = 'HOBS_PASVAR'
    
    HCIBLE_MIN = 'HCIBLE_MIN'
    HCIBLE_MAX = 'HCIBLE_MAX'
    HCIBLE_PASVAR = 'HCIBLE_PASVAR'
    
    OUTPUT_DOSSIER='OUTPUT_DOSSIER'
    OUTPUT = 'OUTPUT'
    OUTPUT_WEB = 'OUTPUT_WEB'
    
    USE_CURVATURE = 'USE_CURVATURE'
    REFRACTION = 'REFRACTION'
    RADIUS = 'RADIUS'
    OPERATOR = 'OPERATOR'
    
    def initAlgorithm(self, config=None):
        """
        Here we define the inputs and output of the algorithm, along
        with some other properties.
        
        Créé l'interface du plugin.
        
        Permet d'ajouter des paramètres qui seront les inputs à entrer par
        l'utilisateur.
        
        Permet d'indiquer des informations à l'utilisateur sur les inputs à entrer.
        
        Chaque paramètre est associé à une variable globale de la classe.
        
        """

        #Point ou polygone observé
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.OBSERVED_LAYER,
            self.tr("\n POINT OU POLYGONE OBSERVE"),
            [QgsProcessing.TypeVectorPoint, QgsProcessing.TypeVectorPolygon]
        ))
                
        self.addParameter(QgsProcessingParameterNumber(
            self.NBPT_MIN,
            "Si polygone, nombre de points formant son contour (points/km de périmètre)",
            QgsProcessingParameterNumber.Integer,
            3,
            optional = True))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.NBPT_MAX,
            "Nombre de points maximum formant le contour du polygone",
            QgsProcessingParameterNumber.Integer,
            optional = True))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.NBPT_PASVAR,
            "Pas de variation du nombre de points",
            QgsProcessingParameterNumber.Integer,
            optional = True))
        
        #MNT
        self.addParameter(
            QgsProcessingParameterRasterLayer(
                self.MNT,
                self.tr('\n \n MNT ET FICHIERS DE SURSOL \n \n Modele Numerique de Terrain MNT')
                )
            )      
        
        #Dossier des fichiers shp
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_DOSSIER_SHP,
                "Dossier contenant les éléments de sursol au format SHP",
                behavior = 1,
                optional = True
                )
            )
        
        #Fichier CSV
        self.addParameter(
            QgsProcessingParameterFile(
                self.INPUT_CSV,
                "Fichier CSV de paramétrage du sursol",
                behavior = 0,
                extension = 'csv',
                optional = True))

        #Variation différenciée des éléments de sursol:
        self.addParameter(QgsProcessingParameterBoolean(
            self.VARSURSOL_DIF,
            self.tr('Faire varier le sursol selon les paramètres de variation du fichier CSV par type de nature de sol [optionnel]'),
            False
        ))
        
        #Variation indifférenciée des éléments de sursol:
        self.addParameter(QgsProcessingParameterBoolean(
            self.VARSURSOL_INDIF,
            self.tr('Faire varier indistinctement le sursol selon les paramètres ci-dessous [optionnel]'),
            False
        ))

        #Variation relative minimum:
        self.addParameter(QgsProcessingParameterNumber(
            self.SURSOL_MIN,
            self.tr('Variation relative minimum des éléments de sursol dans leur ensemble, meters (Ex : -5.0)'),
            QgsProcessingParameterNumber.Double,
            optional = True))
        
        #Variation relative maximum:
        self.addParameter(QgsProcessingParameterNumber(
            self.SURSOL_MAX,
            self.tr('Variation relative maximum des éléments de sursol dans leur ensemble, meters (Ex : 10.0)'),
            QgsProcessingParameterNumber.Double,
            optional = True))
    
        #Pas de variation:
        self.addParameter(QgsProcessingParameterNumber(
            self.SURSOL_PASVAR,
            self.tr('Pas de variation des éléments de sursol, meters'),
            QgsProcessingParameterNumber.Double,
            optional = True))

        #Variation de la hauteur d'observateur :
         
        self.addParameter(QgsProcessingParameterNumber(
            self.HOBS_MIN,
            self.tr("\n \n HAUTEUR DE L'OBSERVATEUR \n \n Hauteur de l'observateur (hauteur minimale si variation), meters"),
            QgsProcessingParameterNumber.Double,defaultValue= 1.6))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.HOBS_MAX,
            self.tr("Hauteur maximale de l'observateur', meters"),
            QgsProcessingParameterNumber.Double,
            optional = True))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.HOBS_PASVAR,
            self.tr('Pas de variation hauteur observateur, meters'),
            QgsProcessingParameterNumber.Double,
            optional = True))
        
        #Variation de la hauteur de la cible :
        
        self.addParameter(QgsProcessingParameterNumber(
            self.HCIBLE_MIN,
            self.tr("\n \n HAUTEUR DE LA CIBLE \n \n Hauteur de la cible (hauteur minimale si variation), meters"),
            QgsProcessingParameterNumber.Double,defaultValue= 0.0))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.HCIBLE_MAX,
            self.tr("Hauteur maximale de la cible, meters"),
            QgsProcessingParameterNumber.Double,
            optional = True))
        
        self.addParameter(QgsProcessingParameterNumber(
            self.HCIBLE_PASVAR,
            self.tr('Pas de variation hauteur cible, meters'),
            QgsProcessingParameterNumber.Double,
            optional = True))

        #Dossier dans lequel vont s'enregistrer les rasters en sortie:
        self.addParameter(QgsProcessingParameterFile(
            self.OUTPUT_DOSSIER,
            "\n \n PARAMETRES DE SORTIE \n \n Dossier des rasters en sortie",
            behavior = 1
            ))

        #Sortir les fichiers pour une visualisation web:
        self.addParameter(QgsProcessingParameterBoolean(
            self.OUTPUT_WEB,
            self.tr('Ouvrir une visualisation web'),
            False
        ))

        #Rayon de calcul:
        self.addParameter(QgsProcessingParameterNumber(
            self.RADIUS,
            self.tr("\n \n PARAMETRES DE CALCUL \n \n Radius of analysis, meters"),
            QgsProcessingParameterNumber.Integer,
            defaultValue= 5000))

        #Courbure de la Terre:
        self.addParameter(QgsProcessingParameterBoolean(
            self.USE_CURVATURE,
            self.tr('Courbure de la terre'),
            True
        ))

        #Refraction atmospherique:
        self.addParameter(QgsProcessingParameterNumber(
            self.REFRACTION,
            self.tr('Réfraction atmosphérique'),
            1, 0.13, False, 0.0, 1.0
        ))

    def processAlgorithm(self, parameters, context, feedback):
        """
        Fonction où s'exécute l'algorithme.
        
        Créer une liste de variations pour chaque paramètre.
        
        Execute un calcul de visibilité passive pour chaque combinaison de
        paramètres.
        
        """
        #Objet observé QgsVectorLayer
        observedLayer = self.parameterAsVectorLayer(parameters,self.OBSERVED_LAYER,context)
                
        feedback.pushInfo(str(observedLayer.geometryType()))
        
        #Si vaut 0 est un point, si vaut 2 est un polygone
        typeGeom = observedLayer.geometryType()
        
        feedback.pushInfo(str(observedLayer.source()))
        
        #Nombre de point pour le contour si polygone et paramètres de variation
        #si indiqué
        nbPtMin = self.parameterAsInt(parameters, self.NBPT_MIN, context)
        nbPtMax = self.parameterAsInt(parameters, self.NBPT_MAX, context)
        #Vaut None si pas de variation
        nbPtPas = self.parameterAsInt(parameters, self.NBPT_PASVAR, context)
        #Vaut None si pas de variation
        
        mnt = self.parameterAsRasterLayer(parameters,self.MNT, context)    
        
        #Paramètrage du sursol
        dossier = self.parameterAsFile(parameters,self.INPUT_DOSSIER_SHP, context)
        cheminCsv = self.parameterAsFile(parameters,self.INPUT_CSV, context)
        
        feedback.pushInfo(str(dossier))
        feedback.pushInfo(str(cheminCsv))   
        
        #Vaut True si variation par type de nature de sol
        varDif = self.parameterAsBool(parameters,self.VARSURSOL_DIF,context)
        feedback.pushInfo(str(varDif))
        
        #Vaut True si variation du sursol dans son ensemble
        varIndif = self.parameterAsBool(parameters,self.VARSURSOL_INDIF,context)
        feedback.pushInfo(str(varIndif))
        
        #Paramètres de variation du sursol si variation dans son ensemble
        pasSursol = self.parameterAsDouble(parameters,self.SURSOL_PASVAR, context)
        minSursol = self.parameterAsDouble(parameters,self.SURSOL_MIN, context)
        maxSursol = self.parameterAsDouble(parameters,self.SURSOL_MAX, context)
        
        #Hauteur de l'observateur et paramètres de variation si indiqué
        minHObs = self.parameterAsDouble(parameters,self.HOBS_MIN, context)
        maxHObs = self.parameterAsDouble(parameters,self.HOBS_MAX, context)
        #Vaut None si pas de variation
        pasObs = self.parameterAsDouble(parameters,self.HOBS_PASVAR, context)
        #Vaut None si pas de variation
        
        #Hauteur de la cible et paramètres de variation si indiqué
        minHCible = self.parameterAsDouble(parameters,self.HCIBLE_MIN, context)
        maxHCible = self.parameterAsDouble(parameters,self.HCIBLE_MAX, context)
        #Vaut None si pas de variation
        pasCible = self.parameterAsDouble(parameters,self.HCIBLE_PASVAR, context)
        #Vaut None si pas de variation
        
        #Chemin du dossier des rasters en sortie
        dossierSortie = self.parameterAsFile(parameters,self.OUTPUT_DOSSIER, context)
        
        outputWeb = self.parameterAsBool(parameters,self.OUTPUT_WEB,context)
        #Vaut True si une sortie web est demandé
        
        #Rayon d'analyse
        radius = self.parameterAsDouble(parameters, self.RADIUS, context)
        
        #Prendre en compte la courbure de la Terre dans le calcul de visibilité
        #passive
        useEarthCurvature = self.parameterAsBool(parameters,self.USE_CURVATURE,context)
        
        #Réfraction atmosphérique
        refraction = self.parameterAsDouble(parameters,self.REFRACTION,context)
        
        #Valeur pour le calcul de visibilité passive
        operator = self.parameterAsInt(parameters,self.OPERATOR,context) + 1
        
        feedback.pushInfo("Récupération des paramètres")
        
        #Création d'un répertoire temporaire pour les couches temp:
        folderTemp = QgsProcessingUtils.tempFolder()
        
        #Créer un dossier temporaire spécifique qui sera nommé selon la date:
        t = time.localtime()
        date = time.strftime('%D', t)
        date2 = date.replace('/','_')
        heure = time.strftime("_%H_%M_%S", t)
        date3 = '/'+'vp'+date2+heure
        
        folderTempLayers = folderTemp + date3
        
        if not os.path.exists(folderTempLayers):
            os.makedirs(folderTempLayers)
            
        """
        Création des dossiers de résultats, s'il y a un polygone en entrée 
        on créé aussi un dossier point:
            
        """
        
        if typeGeom == 2:
            dossierPoints = dossierSortie + "/pointsContourPolygone"
            if not os.path.exists(dossierPoints):
                os.makedirs(dossierPoints)
            
        dossierRaster = dossierSortie + "/RastersVisibPass"
        if not os.path.exists(dossierRaster):
            os.makedirs(dossierRaster)
        
        """
        Création de listes d'accès au chemin des points en cas de sortie web
        
        """
        if outputWeb:
            if typeGeom == 0:
                path_point = observedLayer.source()
            else:
                paths_points_web = []
                listePointsShp = []
        
        
        """
        Réduire la taille du MNT en fonction du radius pour
        optimiser les temps de calculs
        
        """
        feedback.setProgressText("Optimisation de la taille du MNT...")
        
        opti = fp.optimisationCalcul(observedLayer, radius, folderTempLayers, mnt)
        
        #Chemin vers mnt découpé
        mnt_cut = opti[0]
        
        raster_mnt_cut = QgsRasterLayer(mnt_cut)
        
        #Récupérer l'étendue du MNT:
        ext_resultat = raster_mnt_cut.extent()
        
        #Récupérer les 4 points formants l'étendue du MNT:
        xmin = ext_resultat.xMinimum()
        xmax = ext_resultat.xMaximum()
        ymin = ext_resultat.yMinimum()
        ymax = ext_resultat.yMaximum()
        
        #Résolution MNT:
        resWidth = raster_mnt_cut.rasterUnitsPerPixelX()
        resHeight = raster_mnt_cut.rasterUnitsPerPixelY()
        
        #Etendu du MNT en vue de la création du MNE et MOS:
        etendu = str(xmin)+','+str(xmax)+','+str(ymin)+','+str(ymax)+' [EPSG:2154]'
        
        feedback.setProgress(5.0)
        
        """
        Construction du sursol au format shp :
        """
        
        if dossier != "" and cheminCsv != "":
            feedback.setProgressText("Traitement des fichiers de sursol...")
            
            fusionSursol = fp.constructionSursol(cheminCsv, dossier, raster_mnt_cut, folderTempLayers)
            
        feedback.setProgress(15.0)
        
        """
        Création des listes de variations
        
        """
        feedback.setProgressText("Création des listes de variations...")
        
        """
        Création de la liste de nb de points à faire varier
        
        """
        
        liste_nbpoints = []
        if typeGeom == 2:
            
            if nbPtMin != nbPtMax and nbPtMin < nbPtMax and nbPtPas > 0 :
                
                while nbPtMin <= nbPtMax :
                    
                    #Création de la liste des hauteurs avec le pas de variation
                    #entre la borne inférieure et la borne supérieure 
                    liste_nbpoints.append(nbPtMin)               
                    nbPtMin += nbPtPas
                            
            else:
                #Si minHauteur == maxHauteur ou supérieur à maxHauteur:
                liste_nbpoints.append(nbPtMin)
            feedback.pushInfo("Calcul des différents nombre de points formant le contour du polygone")
        
        else:
            liste_nbpoints.append(1)
            
        feedback.pushInfo("Nombre de points")       
        feedback.pushInfo(str(liste_nbpoints))
        
        """
        Création de la liste de hauteur de l'observateur à faire varier
        
        """
        
        liste_hauteurObs = []
        #Si le paramètre hauteur d'observateur est à faire varier :
        if maxHObs != None and pasObs != None:
            
            #Eviter l'incrémentation sur des floats:
            minHObsI = int(minHObs * 100)
            maxHObsI = int(maxHObs * 100)
            pasIObs = int(pasObs * 100)
            
            if minHObs != maxHObs and minHObs < maxHObs and pasObs > 0 :
                
                while minHObsI <= maxHObsI:
                    
                    #Création de la liste des hauteurs avec le pas de variation entre la borne inférieure et la borne supérieure 
                    liste_hauteurObs.append(minHObsI / 100)               
                    minHObsI += pasIObs
                    
            else:
                #Si minHauteur == maxHauteur ou supérieur à maxHauteur:
                liste_hauteurObs.append(minHObs)
                
        else:
            #Si le paramètre hauteur d'observateur n'est pas à faire varier
            liste_hauteurObs.append(minHObs)
        
        feedback.pushInfo("Calcul des différentes hauteurs d'observateur")
        feedback.pushInfo(str(liste_hauteurObs))
        
        """
        Création de la liste de hauteur de la cible à faire varier
        
        """
        
        liste_hauteurCible = []
        if maxHCible != None and pasCible != None:
            
            minHCibleI = int(minHCible * 100)
            maxHCibleI = int(maxHCible * 100)
            pasICible = int(pasCible * 100)
        
            if minHCible != maxHCible and minHCible < maxHCible and pasCible > 0 :
                
                while minHCibleI <= maxHCibleI:
                    
                    #Création de la liste des hauteurs avec le pas de variation
                    #entre la borne inférieure et la borne supérieure 
                    liste_hauteurCible.append(minHCibleI / 100)               
                    minHCibleI += pasICible
                            
            else:
                
                #Si minHauteur == maxHauteu ou supérieur à maxHauteur:
                liste_hauteurCible.append(minHCible)
                
        else:
            
            liste_hauteurCible.append(minHCible)

        feedback.pushInfo("Calcul des différentes hauteurs de cible")
        feedback.pushInfo(str(liste_hauteurCible))       
        
        """
        Construction de la liste des combinaisons de variations du sursol :
        Permet d'obtenir une liste des codes correspondant au type de nature de sol
        (mis à 0 si on fait varier indistinctement tout le sursol)
        Permet d'obtenir une liste des combinaisons de variations:
            
        Exemple: 
            
            - bati varie entre -5 et 5 par pas de 10
            - vegetation varie entre 20 et 30 par pas de 5
            - Liste des combinaisons de variation : [[-5, 20], [-5, 25], [-5, 30], [5, 20], [5, 25], [5, 30]]
        
        """
        
        if dossier != "" and cheminCsv != "":
            #Si le sursol est à prendre en compte dans le calcul de visibilité passive:
            if varIndif:
                #Si le sursol est à faire varier dans son ensemble
                
                liste_codes = [0]
                listesVarsSursol = []
                
                if maxSursol != None and pasSursol != None:
                    
                    minSursolI = int(minSursol * 100)
                    maxSursolI = int(maxSursol * 100)
                    pasSursolI = int(pasSursol * 100)
                
                    if minSursol != maxSursol and minSursol < maxSursol and pasSursol > 0 :
                        
                        while minSursolI <= maxSursolI:
                            
                            #Création de la liste des hauteurs avec le pas de variation entre la borne inférieure et la borne supérieure 
                            listesVarsSursol.append([minSursolI / 100])               
                            minSursolI += pasSursolI
                                    
                    else:
                        
                        #Si minHauteur == maxHauteur ou supérieur à maxHauteur:
                        listesVarsSursol.append([minSursol])
                        
                else:
                    
                    listesVarsSursol.append([minSursol])
                    
            elif varDif :
                #Si le sursol est à faire varier selon le type de nature de sol
                
                codeVar = fp.constructionListeVarSursol(cheminCsv)
                liste_codes = codeVar[0]
                listesVarsSursol = codeVar[1]
            
            else:
                #Si le sursol est à prendre en compte mais à ne pas faire varier:
                listesVarsSursol = [[0]]
                liste_codes = [0]
        
        else:
            #Si le sursol n'est pas à prendre en compte:
            listesVarsSursol = [[0]]
            liste_codes = [0]
        
        feedback.pushInfo("Création de la liste de variation de hauteur du sursol")
        feedback.pushInfo(str(listesVarsSursol))
        feedback.pushInfo(str(liste_codes))
        
        
        """
        Calcul du nombre de raster de visibilité passive à calculer
        
        """
        
        nbHobsvp = len(liste_hauteurObs)
        nbHciblevp = len(liste_hauteurCible)
        nbPointCalcvp = len(liste_nbpoints)
        nbVarSursol = len(listesVarsSursol)
        
        nbPointCalcTempvp = 0
        
        for nb in liste_nbpoints:
            
            nbPointCalcTempvp += ((nbHciblevp * nbHobsvp * nb * nbVarSursol) + 1)
            
        
        nbrastervp = nbHobsvp * nbHciblevp * nbPointCalcvp * nbVarSursol
        
        feedback.pushInfo("\n \n \n NOMBRE DE RASTER DE VISIBILITE DEMANDE EN SORTIE : \n \n" + str(nbrastervp) + '\n \n')
        
        if typeGeom == 2:
            feedback.pushInfo("\n \n \n NOMBRE DE RASTER DE VISIBILITE CALCULES EN PRENANT EN COMPTE LE CALCUL DES RASTERS DE VISIBILITE PASSIVE TEMPORAIRES \n (1 par point pour chaque nombre de points formant le contour du polygone) : \n \n" + str(nbPointCalcTempvp) + '\n \n')
        
        if cheminCsv != "" and dossier != "":
            feedback.pushInfo("\n \n \n NOMBRE DE MNS ET DE MNE calculés : \n \n" + str(nbVarSursol) + '\n \n')
        
        """
        Création des listes de MNE et de MNS si prise en compte du sursol:
            
        """
        
        if dossier != "" and cheminCsv != "":
        
            """
            Calcul du MOS et du MNE :
            
            """
            feedback.setProgressText("Calcul du MNE et du MOS...")
            
            path_mos = folderTempLayers + '/mos.tif'
            
            #Calcul du MOS d'après le champ code du fichier de fusion de sursol
            
            constructMos = processing.run("gdal:rasterize",
            {'INPUT':fusionSursol,
            'FIELD':'code',
            'BURN':0,
            'UNITS':1,
            'WIDTH':resWidth,
            'HEIGHT':resHeight,
            'EXTENT':etendu,
            'NODATA':-99999,
            'OPTIONS':'',
            'DATA_TYPE':2,
            'INVERT':False,
            'OUTPUT': path_mos},
            context=context, feedback=feedback, is_child_algorithm=True)
            
            mos = constructMos['OUTPUT']
            
            #Calcul du MNE (sans prendre en compte aucune variation)
            
            path_mne = folderTempLayers+'/mne.tif'
            
            constructMne = processing.run("gdal:rasterize",
            {'INPUT':fusionSursol,
            'FIELD':'hauteur',
            'BURN':0,
            'UNITS':1,
            'WIDTH':resWidth,
            'HEIGHT':resHeight,
            'EXTENT':etendu,
            'NODATA':-99999,
            'OPTIONS':'',
            'DATA_TYPE':5,
            'INVERT':False,
            'OUTPUT': path_mne},
            context=context, feedback=feedback, is_child_algorithm=True)
            #Les endroits sans sursol seront considérés comme du NODATA pour éviter
            #que ces endroits soient pris en compte si variation du MNE
            
            path_mne = constructMne['OUTPUT']
            
            feedback.pushInfo(str(path_mne))
            feedback.pushInfo(str(path_mos))
            
            """
            Récupération des listes de valeurs pour le mne, le mos et le mnt :
                
            """
            #Création de listes (indépendantes du fichier) contenant toutes les valeurs
            #du MNT, MNE, MOS au format suivant :[[ligne0col0, ligne0col1], [ligne1, col0...]]
            
            #http s ://gis.stackexchange.com/questions/107996/how-to-do-loops-on-raster-cells-with-python-console-in-qgis
            
            #Ouverture du MNT par GDAL grâce au chemin du MNT :
            mntGDAL = gdal.Open(mnt_cut)
            
            #Obtention de la liste des valeurs du MNT
            mntArray = mntGDAL.ReadAsArray()
            
            #Fermer le fichier ouvert par GDAL
            mntGDAL = None
            
            #Récupérer la taille de la matrice de pixels du MNT
            widthMnt, heightMnt = mntArray.shape
            
            #Ouvrir les fichiers MNE et MOS:
            mneGDAL = gdal.Open(path_mne)
            mneArray = mneGDAL.ReadAsArray()
            mneGDAL = None
            
            mosGDAL = gdal.Open(path_mos)
            mosArray = mosGDAL.ReadAsArray()
            mosGDAL = None
            
            #feedback.pushInfo(str(mneArray))
            #feedback.pushInfo(str(mosArray))
            
            #Calculer la résolution du MNT
            xres = (xmax-xmin)/float(heightMnt)
            yres = (ymax-ymin)/float(widthMnt)
            
            #les 0 signifient que le raster est orienté vers le nord
            #Création des paramètres pour la création dun fichier Géotiff
            geotransform = (xmin, xres, 0, ymax, 0, -yres)
            
            #Géoréférencement
            srs = osr.SpatialReference()
            
            #L'EPSG est défini en dur en 2154 (pose sûrement des problèmes
            #si le mnt est dans une autre projection)
            srs.ImportFromEPSG(2154)
            
            """
            Calcul des différents MNS et MNE
            
            """
            
            liste_path_mne = []
            liste_path_mns = []
            
            feedback.setProgressText("Calcul du(des) MNE et du(des) MNS...")
            
            #Pour chaque variation du sursol:
            for i in range(0, len(listesVarsSursol)):
                                
                if feedback.isCanceled():  break
                
                mneListe = []
                mnsListe = []
                
                for row in range(0, widthMnt):
                #Initialisation d'une ligne pour chaque futur MNS et MNE
                    mnsLigne = []
                    mneLigne = []
                    
                    #Parcours de chaque case pour chaque ligne:
                    for col in range(0, heightMnt):
                        
                        #Calcul pour le MNS:
                        
                        if mntArray[row][col] < -90000 :
                            
                            #Si NoData, alors on ajoute à la ligne une case contenant la valeur -99999
                            mnsLigne.append(-99999)
                            
                        elif mneArray[row][col] < -90000:
                            
                            #Si il n'y a pas d'éléments de sursol à cet endroit
                            #Le MNS prend la valeur du MNT
                            
                            valMns = mntArray[row][col]
                            
                            mnsLigne.append(valMns)
                            
                        else :
                            
                            #On cherche si le code du pixel est à faire varier:
                            
                            valMns = None
                            
                            for k in range(0, len(liste_codes)):
                                
                                if mosArray[row][col] == liste_codes[k]:
                                    
                                    valMns = mntArray[row][col] + mneArray[row][col] + listesVarsSursol[i][k]
                                    
                                    #Si la valeur du pixel du MNS est devenue négative, doit être mise à 0
                                    #(cas où la variation relative est négative)
                                    
                                    if valMns >= 0:
                                        mnsLigne.append(valMns)
                                        
                                    else:
                                        mnsLigne.append(0)
                                        
                            if valMns == None:
                                #Signifie que la valeur en question n'est pas à faire varier
                                valMns = mntArray[row][col] + mneArray[row][col]
                                mnsLigne.append(valMns)
                                
                        #Calcul pour le MNE:
                                
                        if mneArray[row][col] < -90000:
                            #S'il n'y a pas d'éléments de sursol, le pixel vaut 0
                            mneLigne.append(0)
    
                        else:
                            #On cherche si le code du pixel est à faire varier
                            valMne = None
                            for k in range(0, len(liste_codes)):
                                
                                if mosArray[row][col] == liste_codes[k]:
                                    
                                    valMne = mneArray[row][col] + listesVarsSursol[i][k]
                                    
                                    #Si la valeur est devenue négative, est mise à 0
                                    if valMne >= 0:
                                        mneLigne.append(valMne)
                                    else:
                                        mneLigne.append(0)
                            
                            if valMne == None:
                                #Signifie que la valeur en question n'est pas à faire varier
                                valMne = mneArray[row][col]
                                mneLigne.append(valMne)                     
                                
                    #Lorsque toute une ligne a été calculé, ajout aux listes du MNS et MNE
                    mnsLigneFin = mnsLigne.copy()
                    mneLigneFin = mneLigne.copy()
                    
                    #Ajout de la copie de la ligne à la liste du MNS:
                    mnsListe.append(mnsLigneFin)
                    mneListe.append(mneLigneFin)
                
                mnsListeFinale = mnsListe.copy()
                mneListeFinale = mneListe.copy()
                
                #feedback.pushInfo(str(mneListeFinale))
            
                """
                Transformer une liste de valeurs de pixel en fichier Géotiff :
                    
                """
                
                path_mns_temp = folderTempLayers+'/mns'
                path_mne_temp = folderTempLayers+'/mne'
                
                for j in range(0, len(listesVarsSursol[i])):
                    path_mns_temp += '_code' + str(liste_codes[j]) + 'var' + str(int(listesVarsSursol[i][j]*100))
                    path_mne_temp += '_code' + str(liste_codes[j]) + 'var' + str(int(listesVarsSursol[i][j]*100))
                
                path_mns_temp += '.tif'
                path_mne_temp += '.tif'
                
                #Transformer liste en numpy_array :
                #http s ://gis.stackexchange.com/questions/37238/writing-numpy-array-to-raster-file
                mnsArraytemp = np.array(mnsListeFinale)
                mneArraytemp = np.array(mneListeFinale)
                
                #Créer le fichier .tif                
                mnsSortie = gdal.GetDriverByName('GTiff').Create(path_mns_temp, heightMnt, widthMnt, 1, gdal.GDT_Float32)
                mnsSortie.SetGeoTransform(geotransform)
                mnsSortie.SetProjection(srs.ExportToWkt())
                
                mneSortie = gdal.GetDriverByName('GTiff').Create(path_mne_temp, heightMnt, widthMnt, 1, gdal.GDT_Float32)
                mneSortie.SetGeoTransform(geotransform)
                mneSortie.SetProjection(srs.ExportToWkt())
                
                #Ajout de la liste créé en tant que valeur pour chaque pixel
                mnsSortie.GetRasterBand(1).WriteArray(mnsArraytemp)
                mnsSortie.FlushCache()
    
                mneSortie.GetRasterBand(1).WriteArray(mneArraytemp)
                mneSortie.FlushCache()
                
                #Gestion des noData :
                #http s ://gis.stackexchange.com/questions/319249/inserting-nodata-value-using-gdal
                
                sortieGDALMns = gdal.Open(path_mns_temp,1)
                #1 signifie que l'on ouvre le fichier en mode édition
                
                mnsBand = sortieGDALMns.GetRasterBand(1)
                #Sélection de la bande 1
                mnsBand.SetNoDataValue(-99999)
                
                mnsBand= None 
                sortieGDALMns = None
                
                #Ajout du chemin du mne et du mns aux listes correspondantes
                liste_path_mne.append(path_mne_temp)
                liste_path_mns.append(path_mns_temp)
                
        
        else:
            #Si le sursol n'est pas pris en compte dans le calcul
            liste_path_mne = [None]
            liste_path_mns = [None]
        
        feedback.setProgress(40.0)
        
        """
        Calcul de visibilité passive pour chaque variation:
            
        """
        
        liste_paths_rasters_vp = []
        
        #Pour chaque nombre de points:
        for count in liste_nbpoints:
            feedback.setProgressText("Calcul des raster(s) de visibilité(s) passive(s)...")
            
            if feedback.isCanceled():  break
            
            #Créer un dossier temporaire spécifique pour chaque nb de point:
            
            folderTempLayers2 = folderTempLayers + '/nbpt' + str(count)
            
            if not os.path.exists(folderTempLayers2):
                os.makedirs(folderTempLayers2)
                
            if typeGeom == 2:
        
                """
                Création de n points aléatoires sur le contour du polygone:
                """
                
                path_points = dossierPoints + '/pointsPolygon_'+str(count)+'.shp'
                
                if outputWeb:
                    #Enregistrer les chemins des points constituant le contour
                    path_point_web_prep = '/pointsPolygon_'+str(count)+'.geojson'
                    paths_points_web.append(path_point_web_prep)
                    
                    listePointsShp.append(path_points)
                
                #Appel au processing plugin creation de points aléatoires
                creationPoints = processing.run('Choucas:createptsaleatoireskm',
                {'INPUT': observedLayer,
                 'INPUT_COUNT' : count,
                 'OUTPUT': path_points},
                context=context, feedback=feedback, is_child_algorithm=True)
                
                feedback.pushInfo(str(creationPoints['OUTPUT']))
                
                path_points = creationPoints['OUTPUT']
                
                points = QgsVectorLayer(path_points)
                
                """
                Création d'un shp point spécifique pour chaque point:
                """
                
                feats = [feat for feat in points.getFeatures()]
                
                listePoints = []
                i=0
                for feat in feats:
                    geom = feat.geometry()
                    id = feat.attribute('ID')
                    
                    newFeat = QgsFeature()
                    newFeat.setGeometry(geom)
                
                    newFeat.setAttributes([id])
                    
                    #Création des champs:
                    field = QgsField('ID', QVariant.Int, len=500)
                    fields = [field]
                
                    #Création du shp propre:
                    layerNewPoint = QgsVectorLayer("Point", "point"+str(count)+'_'+str(i), 'memory')
                
                    #Récupérer le système de référence du shp source:
                    srid = points.crs()
                    sridWkt = srid.toWkt()
                
                    #Géoréférencement du nouveau fichier shp à partir de celui du shp source:
                    crs = layerNewPoint.crs()
                    crs.createFromWkt(sridWkt)
                    layerNewPoint.setCrs(crs)
                
                    #Ajout des champs au shp:
                    layerNewPointData = layerNewPoint.dataProvider()
                    layerNewPointData.setEncoding(u'UTF-8')
                    layerNewPointData.addAttributes(fields)
                    layerNewPoint.updateFields()
                
                    #Ajout des entités / features au shp propre:
                    layerNewPointData.addFeatures([newFeat])
                    #layerTest.updateExtents()
                
                    #Ajout du shp propre à la liste des shp propres (qui sont des VectorLayer)
                    listePoints.append(layerNewPoint)
                    
                    i+=1
                
                    
            else:
                listePoints=[observedLayer]
               

                
            """
            Calcul de visibilité passive pour chaque point
            """
            
            #Liste des rasters de visbilité passives pour les points de polygone: 
                        
            #Pour chaque hauteur de cible
            for i in range(0, len(liste_hauteurCible)):
                hauteurCible = liste_hauteurCible[i]
                
                #Pour chaque hauteur d'observateur
                for j in range(0, len(liste_hauteurObs)):
                    hauteurObservateur = liste_hauteurObs[j]
                    
                    #Pour chaque mns et mne
                    for k in range (0, len(liste_path_mns)):
                                
                        path_mns = liste_path_mns[k]
                        path_mne = liste_path_mne[k]
                        
                        #Pour chaque point
                        l=0
                        liste_paths_rasters_vp_polygone = []
                        for ptObs in listePoints :
                            
                            if feedback.isCanceled():  break
                            
                            """
                            Création de point observé :
                            """
    
                            observedPoint = folderTempLayers2+"/obsdPt"+str(count)+'_'+str(i)+'_'+str(j)+ '_' + str(k) + '_' + str(l) + ".shp"
                            
                            creationObservedPoint = processing.run('Choucas:observedpoint',
                            {'OBSERVED_POINTS': ptObs,
                             'DEM' : raster_mnt_cut,
                             'OUTPUT': observedPoint,
                             'RADIUS' : radius,
                             'TARGET_HEIGHT': hauteurCible},
                            context=context, feedback=feedback, is_child_algorithm=True)
                                        
                            observedPoint = creationObservedPoint['OUTPUT']
                            
                            pointObsVector = QgsVectorLayer(observedPoint)
                    
                            feedback.pushInfo("Création du point observé ")
                            feedback.pushInfo(str(creationObservedPoint['OUTPUT']))
                
                
                            """
                            Calcul de visibilité passive:
                            """
                            
                            #Les fichiers sont nommés sous la forme : vpass_nbpt3_Hcible0_Hobs140_sursol_code1var10_code2var20.tif
                            if typeGeom == 2:
                                
                                #Pour calculer le raster de visibilité passive finale
                                #Lorsqu'il y a un polygone, il faut conserver dans le
                                #même dossier le raster de vp pour x hauteurCible, y hauteurObservateur et z hauteurSursol
                                
                                folderTempLayers3 = folderTempLayers2 + '/cib' + str(i) + 'obs' + str(j) + 'sursol' + str(k)
                                
                                feedback.pushInfo("Chemin des rasters pour ce polygone + cib obs et sursol: "+str(folderTempLayers3))
                                
                                if not os.path.exists(folderTempLayers3):
                                    os.makedirs(folderTempLayers3)
                                
                                rasterVisPassive = folderTempLayers3 + '/vpass' + str(l) + '_Hcible' + str(int(liste_hauteurCible[i]*100)) + '_Hobs' + str(int(liste_hauteurObs[j]*100)) + '_sursol' + str(k) + ".tif"
                            
                            else:
                                #Si l'objet est un point : création du nom du raster en sortie
                                rasterVisPassive = dossierRaster + '/vpass_nbpt' + str(count) + '_Hcible' + str(int(liste_hauteurCible[i]*100)) + '_Hobs' + str(int(liste_hauteurObs[j]*100))
                                
                                if not varDif and not varIndif:
                                    rasterVisPassive += "nosursol"
                                
                                else:
                                    rasterVisPassive += 'sursol'
                                    for m in range(0, len(listesVarsSursol[k])):
                                        rasterVisPassive += '_code' + str(liste_codes[m]) + 'var' + str(int(listesVarsSursol[k][m]*100))
                                
                                rasterVisPassive += '.tif'
                            
                            #Appel au plugin de calcul de visibilité passive
                            constructVisibPass = processing.run('Choucas:visibilitepassive',
                            {'OBSERVED_POINTS': pointObsVector,
                             'MNT': mnt_cut,
                             'MNE': path_mne,
                             'MNS': path_mns,
                             'INTPUT_HOBS': hauteurObservateur,
                             'INPUT_HCIBLE': hauteurCible,
                             'OUTPUT_PASSIVE':rasterVisPassive,
                             'RADIUS': radius,
                             'USE_CURVATURE':useEarthCurvature,
                             'REFRACTION':refraction,
                             'OPERATOR':operator},
                            context=context, feedback=feedback, is_child_algorithm=True)
                            
                            rasterVisPassive = constructVisibPass['OUTPUT_PASSIVE']
                            
                            if typeGeom == 0:
                                liste_paths_rasters_vp.append(rasterVisPassive)
                                
                            else:
                                #On ajoute le raster calculé au dossier des rasters pour le nombre de points et les paramètres concernés
                                liste_paths_rasters_vp_polygone.append(rasterVisPassive)
                   
                            l+=1
                        
                        """
                        Construction du raster de visibilité passive résultat pour le polygone
                        Un pixel voit le polygone s'il voit tous les points.
                        
                        """
                        
                        if typeGeom == 2:
                            feedback.setProgressText("Calcul du raster en sortie de visibilité passive pour le polygone...")
                            li_path_raster_vp = liste_paths_rasters_vp_polygone.copy()
                            
                            #Récupérer les listes 
                            li_val_raster_vp = []
                            for rasterVp in li_path_raster_vp:
                                
                                rasterVpGDAL = gdal.Open(rasterVp)
                                rasterVpArray = rasterVpGDAL.ReadAsArray()
                                rasterVpGDAL = None
                                li_val_raster_vp.append(rasterVpArray)
                                feedback.pushInfo(str(len(rasterVpArray)))
                                
                            feedback.pushInfo("Rasters à concaténer : " + str(li_path_raster_vp))
                                     
                            #Paramètres du raster résultat:
                            #Chaque raster a la même emprise donc on récupère les dimensions
                            #du premier raster de la liste:
                            width, height = li_val_raster_vp[0].shape
                            
                            
                            #Calcul de la résolution du raster résultat à partir de celle du mnt
                            #utilisé pour les calculs
                            
                            xres2 = (xmax-xmin)/float(height)
                            yres2 = (ymax-ymin)/float(width)
                            
                            #Géoréférencement du raster résultat
                            #Suppose que le mnt en entrée est un 2154 !
                            
                            geotransform2 = (xmin, xres2, 0, ymax, 0, -yres2)
                            srs2 = osr.SpatialReference()
                            srs2.ImportFromEPSG(2154)
                            
                            
                            li_resultatnonbinaire = []
                            li_resultatbinaire = []
                            for row in range(0, width):
                            #Initialisation d'une ligne:
                                #Deuxième boucle: parcours de chaque case pour chaque ligne et choix de binaire ou non :
                                tabnonbinaire = []
                                    #Non binaire  
                                for col in range(0, height):
                                    tabnonbinaire.append(0)
                                for col in range(0, height):
                                    #Le pixel voit la cible
                                    for vpArray in li_val_raster_vp:
                                        if vpArray[row][col]==1:
                                        #Ajouter 1
                                            tabnonbinaire[col]=tabnonbinaire[col]+1
                                #Lorsque toutes les valeurs du raster résultat ont été calculées
                                #pour une ligne, création d'une copie de cette ligne de valeurs:
                                tabnonbinaireFin = tabnonbinaire.copy()
                                #Ajout de la copie de la ligne à la liste du raster:
                                li_resultatnonbinaire.append(tabnonbinaireFin)
                                #Binaire
                                tabbinaire = []
                                for col in range(0, height):
                                    pixelVoit = True
                                    #Le pixel voit la cible
                                    for vpArray in li_val_raster_vp:
                                        if vpArray[row][col]==0:
                                            #Si un pixel ne voit pas un point
                                            #le pixel ne voit pas le polygone
                                            pixelVoit = False
                                    if pixelVoit:
                                        tabbinaire.append(1)
                                    else:
                                        tabbinaire.append(0)
                                #Lorsque toutes les valeurs du raster résultat ont été calculées
                                #pour une ligne, création d'une copie de cette ligne de valeurs:
                                tabbinaireFin = tabbinaire.copy()
                                #Ajout de la copie de la ligne à la liste du raster:
                                li_resultatbinaire.append(tabbinaireFin)
                            
                            
                            """
                            Transformer la liste de valeurs résultat en fichier Géotiff :
                                
                            """
                            #Transformer liste en numpy_array :
                            li_resultatbinaire = li_resultatbinaire.copy()
                            resArraybinaire = np.array(li_resultatbinaire)
                            #Transformer liste en numpy_array :
                            li_resultatnonbinaire = li_resultatnonbinaire.copy()
                            resArraynonbinaire = np.array(li_resultatnonbinaire)
                            
                            R=np.zeros([len(resArraynonbinaire), len(resArraynonbinaire[0])])
                            nb_pts = len(listePoints)
                            for mo in range(0, width):
                                for no in range(0, height):
                                    if (resArraynonbinaire[mo][no]/nb_pts) < 0.1:
                                        R[mo,no]= 10* (resArraynonbinaire[mo,no]/nb_pts)
                                    if 0.1 <= resArraynonbinaire[mo][no]/nb_pts and resArraynonbinaire[mo][no]/nb_pts <= 0.9:
                                        R[mo,no]= 1
                                    if resArraynonbinaire[mo][no]/nb_pts > 0.9:
                                        R[mo,no]= -10 * (resArraynonbinaire[mo,no]/nb_pts) + 10
                            resArrayfuzzi=R 
                            
                            listedesraster=[resArraybinaire,resArraynonbinaire,resArrayfuzzi]
                            print(listedesraster)
                            compteur = 1
                            for z in listedesraster:
                                
                                res_output = dossierRaster + '/vpass_nbpt' + str(count) + '_Hcible' + str(float(liste_hauteurCible[i]*100)) + '_Hobs' + str(float(liste_hauteurObs[j]*100))
                                
                                if cheminCsv == "" and dossier == "":
                                    res_output += "nosursol"
                                
                                else:
                                    res_output += 'sursol'
                                    for m in range(0, len(listesVarsSursol[k])):
                                        res_output += '_code' + str(liste_codes[m]) + 'var' + str(int(listesVarsSursol[k][m]*100))

                                res_output += str(compteur) + '.tif'
                                resVisibPass = gdal.GetDriverByName('GTiff').Create(res_output, height, width, 1, gdal.GDT_Float64)
                                resVisibPass.SetGeoTransform(geotransform2)
                                resVisibPass.SetProjection(srs2.ExportToWkt())
                                
                                #Ajout de la liste créé en tant que valeur pour chaque pixel
                                resVisibPass.GetRasterBand(1).WriteArray(z)
                                resVisibPass.FlushCache()
                                liste_paths_rasters_vp.append(res_output)
                                
                                compteur += 1
        
        feedback.pushInfo(str(liste_paths_rasters_vp))
        feedback.setProgress(75.0)
        
        viewshed = liste_paths_rasters_vp[0]
         
        return {self.OUTPUT: viewshed}
        
        
        if outputWeb:
            #Pour la sortie web, besoin de raster projetés en 3857
            #et de points au format JSON projetés en 4326
            
            dossierWeb = dossierSortie + "/sortiesWeb"
            if not os.path.exists(dossierWeb):
                os.makedirs(dossierWeb)
            
            #Reprojection des rasters en 3857
            for pathRasterVp in liste_paths_rasters_vp:
                
                #Pose problème si le chemin contient deux fois RastersVisibPass
                raster_web_path = pathRasterVp.replace('RastersVisibPass', 'sortiesWeb')
                
                processing.run('gdal:warpreproject',
                {'INPUT': pathRasterVp,
                'TARGET_CRS': 'EPSG:3857',
                'OUTPUT': raster_web_path})
            
            #Conversion de format des points
            if typeGeom == 0:
                
                #Ajout du radius en tant qu'attribut du point
                pathPointAddField = folderTempLayers + '/pointAddFieldRadius.shp'
                
                processing.run('qgis:advancedpythonfieldcalculator',
                {'INPUT': path_point,
                 'FORMULA' : 'value =' + str(int(radius)),
                 'FIELD_LENGTH' : 10,
                 'FIELD_NAME' : 'radius',
                 'FIELD_PRECISION' : 3,
                 'FIELD_TYPE' : 0,
                 'OUTPUT': pathPointAddField})
                
                #Reprojection du point en 4326
                pathPointReproject = folderTempLayers + '/pointReprojectSortieWeb.shp'
                
                processing.run('native:reprojectlayer',
                {'INPUT': pathPointAddField,
                 'TARGET_CRS' : 'EPSG:4326 - WGS 84',
                 'OUTPUT': pathPointReproject})
                
                #Création du point au format geojson
                path_point_web = dossierWeb + '/point.geojson'
                
                processing.run('gdal:convertformat',
                {'INPUT': pathPointReproject,
                 'OUTPUT': path_point_web})
                
            else:
                
                for i in range(0, len (listePointsShp)):
                    pathPointShp = listePointsShp[i]
                    
                    vectorPointShp = QgsVectorLayer(pathPointShp)
                    nomPointShp = vectorPointShp.sourceName()
                    feedback.pushInfo(nomPointShp)
                    feedback.pushInfo(str(type(nomPointShp)))
                    
                    #Ajout du champ radius of analysis:
                    pathPointAddField = folderTempLayers + '/pointAddFieldRadius.shp'
                    processing.run('qgis:advancedpythonfieldcalculator',
                    {'INPUT': pathPointShp,
                     'FORMULA' : 'value =' + str(int(radius)),
                     'FIELD_LENGTH' : 10,
                     'FIELD_NAME' : 'radius',
                     'FIELD_PRECISION' : 3,
                     'FIELD_TYPE' : 0,
                     'OUTPUT': pathPointAddField})
                    
                    #Reprojection en 4326
                    pathPointReproject = folderTempLayers + '/pointReprojectSortieWeb.shp'
                    processing.run('native:reprojectlayer',
                    {'INPUT': pathPointAddField,
                     'TARGET_CRS': 'EPSG:4326 - WGS 84',
                     'OUTPUT': pathPointReproject})
                    
                    #Conversion en format geojson
                    path_point_web = dossierWeb + '/' + paths_points_web[i]
                    
                    processing.run('gdal:convertformat',
                    {'INPUT': pathPointReproject,
                     'OUTPUT': path_point_web})
                    
                    
            #Ouverture de l'interface web:
            pathmodule = inspect.getfile(fp)
            pathwebInterface = pathmodule.replace('fonctionsPlugin.py', 'VisionParCas/index.html')
            webbrowser.open(pathwebInterface)
        
            #Assurer un return au plugin
            viewshed = liste_paths_rasters_vp[0]
             
            return {self.OUTPUT: viewshed}
        
    def tr(self, string):
        """
        Returns a translatable string with the self.tr() function.
        """
        return QCoreApplication.translate('Processing', string)

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'ProjetAnalyseSpatiale'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr('Projet Analyse spatiale')

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
        return 'visionparcas'

    def shortHelpString(self):
        """
        Returns a localised short helper string for the algorithm. This string
        should provide a basic description about what the algorithm does and the
        parameters and outputs associated with it..
        """
        
        h = ("Calcul de rasters de visibilité passive en faisant varier des paramètres.\n \n \
             Le nombre de rasters à calculer peut rapidement être très important. \
                 Un trop grand nombre de variations (notamment pour le sursol qui entraine des calculs de MNE et MNS pour chaque variation) \
                     ou un trop grand nombre de paramètres à faire varier à la fois risque de demander un long temps de calcul. \
                         Un paramètre A qui varie 4 fois et un paramètre B qui varie 5 fois demandent le calcul de 20 rasters en sortie. \
                             Une variation pour un type de nature de sursol vaut 1 paramètre. Si un polygone est en entrée \
                                 il y a autant de rasters calculés que de nombre de points demandés + 1 raster pour le polygone. \n \n \
                                     Paramètres à entrer obligatoirement : \n - Point ou polygone observé : (format shapefile) \
                                         un fichier shp contenant 1 entité correspondant à ce qui est observé \n \
                                             - MNT : un raster projeté en Lambert 93 \n \
                                                 - un dossier de sortie (contiendra les rasters de visibilité passive calculés) : les pixels valant 1 voient l'objet observé.\n \
                                                     - une hauteur d'observateur (valeur par défaut : 1,6 m). \n - une hauteur de cible (hauteur de l'objet observé) (valeur par défaut : 0 m).\n \n \
                                                     POINT OU POLYGONE OBSERVE : \n Si un polygone est indiqué : \
                                                         fixer le nombre de points qui constituera le contour du polygone (cf: création de points aléatoires) par défaut 3 points. \
                                                             Pour faire varier le nombre de points : indiquer un nombre maximum et un pas de variation. \n \n \
                                                                 MNT ET FICHIERS DE SURSOL : \n Le MNT doit être projeté en 2154. Pour prendre en compte le sursol \
                                                                     dans le calcul de visibilité passive, il faut indiquer un emplacement pour les fichiers SHP ET un fichier CSV \
                                                                         de paramétrage du sursol correspondant à chaque fichier shp.\n Pour faire varier la hauteur du sursol selon le type de \
                                                                             nature de sol : seule la case Faire varier selon le type de nature de sol doit être cochée. \n \
                                                                                 Pour faire varier le sursol dans son ensemble, il faut cocher la case correspondante 'Faire varier indistinctement' et indiquer une \
                                                                                     valeur relative minimum, maximum et un pas. \n La hauteur de chaque entité va être incrémentée des valeurs souhaités \
                                                                                         \n \n HAUTEUR DE L'OBSERVATEUR ET HAUTEUR DE CIBLE : \n La hauteur de l'observateur et la hauteur de cible \
                                                                                             peuvent être fixés, si l'on souhaite faire varier ces hauteurs, il faut indiquer une variation maximum et un pas \
                                                                                                 \n \n PARAMETRES DE SORTIE : \n Il est conseillé de créer un nouveau dossier vide comme dossier de sortie des résultats. \
                                                                                                     \n \n PARAMETRES DE CALCUL : \n La prise en compte de la courbure de la Terre et la réfraction atmosphérique\
                                                                                                         sont des paramètres du calcul de visibilité passive. Le radius of analysis indique \
                                                                                                             la distance à partir du point observé sur laquelle le calcul de visibilité va s'effectuer. \
                                                                                                                 Permet de réduire les temps de calcul, est un paramètre issu du calcul de visibilité passive.")
                    
        return self.tr(h)


    def createInstance(self):
        return ProjetAnalyseSpatiale()