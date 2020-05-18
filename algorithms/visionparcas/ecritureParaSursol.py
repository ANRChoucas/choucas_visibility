# -*- coding: utf-8 -*-

"""
/***************************************************************************
 QGIS Viewshed Analysis
                                 A QGIS plugin

                              -------------------
        begin                : 2020-05-1
        copyright            : (C) 2020 Coucas
        email                : 
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

__author__ = 'ensg'
__date__ = '2020-05-01'
__copyright__ = '(C) 2020 ensg'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


from PyQt5.QtCore import QCoreApplication
from qgis.core import (QgsProcessing,
                       QgsProcessingException,
                       QgsProcessingAlgorithm,
                       QgsFeatureSink,
                       QgsProcessingParameterFileDestination,
                       QgsProcessingParameterFeatureSource,
                       QgsProcessingParameterFeatureSink,
                       QgsProcessingParameterRasterLayer,
                       QgsProcessingParameterNumber,
                       QgsProcessingParameterField,
                       QgsProcessingParameterFile )

import csv
import unicodedata
import os

class CreateCsvSursol(QgsProcessingAlgorithm):
    """
    Permet de créer un fichier de paramétrage du sursol au format CSV en vue
    d'un calcul de visibilité passive multi paramètres.
    
    INPUT:
        - Fichier SHP (QgsVectorlayer)
        - Champ Nature de sol (Facultatif) (string)
        - Champ Hauteur (Facultatif) (string)
        - Emplacement du fichier CSV (string)
        
    OUTPUT:
        - Fichier CSV de paramétrage du sursol
    
    Remplie automatiquement les champs nom_shp.shp, nom champ nature de sol,
    type de nature de sol et nom champ hauteur si indiqués en entrée, à partir
    des informations issues du fichier SHP.
    
    Ce processing est à exécuter par lot afin de pouvoir compléter le fichier
    CSV en une fois pour tous les fichiers SHP composant le sursol.
    """
    
    # Constants used to refer to parameters and outputs. They will be
    # used when calling the algorithm from another algorithm, or when
    # calling from the QGIS console.

    INPUT_SHP = 'INPUT_SHP'
    FIELD_NATURE = 'FIELD_NATURE'
    FIELD_HAUTEUR = 'FIELD_HAUTEUR'
    
    OUTPUT_CSV = 'OUTPUT_CSV'
    
    def initAlgorithm(self, config):
        """Here we define the inputs and output of the algorithm, along
        with some other properties.
        """
        
        self.addParameter(QgsProcessingParameterFeatureSource(
            self.INPUT_SHP,
            self.tr("Fichier de sursol"),
            [QgsProcessing.TypeVectorPolygon]
            ))
        
        self.addParameter(QgsProcessingParameterField(
            self.FIELD_NATURE,
            self.tr('Champ nature de sol'),
            parentLayerParameterName = self.INPUT_SHP,
            optional = True
            ))
        
        self.addParameter(QgsProcessingParameterField(
            self.FIELD_HAUTEUR,
            self.tr('Champ hauteur'),
            parentLayerParameterName = self.INPUT_SHP,
            optional = True
            ))
        
        self.addParameter(
            QgsProcessingParameterFileDestination(
                self.OUTPUT_CSV,
                "Fichier CSV de paramétrage du sursol"
                ))
        
    def processAlgorithm(self, parameters, context, feedback):
        
        #Récupération des paramètres
        vectorShp = self.parameterAsVectorLayer(parameters,self.INPUT_SHP,context)
        
        #Récupération du nom du fichier shp seulement (sans le chemin):
        nomShp = vectorShp.sourceName()
        
        if nomShp != "":
        
            nomShp += '.shp'
            
        else:
            #Si le sourceName() a renvoyé un str vide, le nomShp sera l'ensemble du chemin:
            nomShp = vectorShp.source()
        
        #Récupération des noms des champs        
        champNature = self.parameterAsString(parameters, self.FIELD_NATURE, context)
        champHauteur = self.parameterAsString(parameters, self.FIELD_HAUTEUR, context)
        
        #Chemin vers le fichier CSV de sortie
        cheminCsv = self.parameterAsFileOutput(parameters, self.OUTPUT_CSV, context)
        
        #Informations pour la console d'exécution
        feedback.pushInfo(str(vectorShp))
        feedback.pushInfo(str(nomShp))
        feedback.pushInfo(str(champNature))
        feedback.pushInfo(str(champHauteur))
        feedback.pushInfo(str(cheminCsv))
        
        #Pour éviter les problèmes d'encodings, définition des valeurs erreurs
        #pour l'utf8
        erreurEncodingUtf8 = '?'
        erreur2EncodingUtf8 = '\ufffd'
        
        #Initialisation des lignes à entrer dans le fichier CSV:
        lignesCsv = []
        
        #Initialisation d'une liste pour conserver les types de natures qui
        #constituent déjà une ligne du fichier CSV.
        listeNatureType = []
        
        #Si le fichier CSV n'existe pas encore, ajout en première ligne du
        #fichier de la ligne "Titre"
        if not os.path.isfile(cheminCsv):
            ligneTitre = ['NomFichierShp.shp', 'Nom champ nature de sol (Facultatif)', 'Type de nature de sol (Facultatif)', 'Nom champ hauteur (Facultatif)', 'Hauteur simulee (Facultatif)', 'Code pour le type de nature de sol (Facultatif) 0 est interdit', 'Variation relative minimale (metres)', 'Variation relative maximale (metres)', 'Pas de variation']
            lignesCsv.append(ligneTitre)
        
        """
        Récupération des informations du shape:
        """
        #Si un champ nature est spécifiée :
        if champNature != "":
            #Définition de l'encoding du fichier SHP en utf8
            #Les valeurs non lues par l'utf8 deviennent soient des '?' soient
            # des '\ufffd'
            vectorShp.setProviderEncoding('utf8')
            
            #Récupération des entités/features du fichier shape :
            feats = [feat for feat in vectorShp.getFeatures()]
            
            #Retour utilisateur pour la progression de la barre d'exécution:
            progressall = 100 / len(feats)
            feedback.setProgressText("Lecture du fichier...")
                    
            for feat in feats:
                i=1
                feedback.setProgress(progressall * i)
                
                #Initialisation de la ligne à ajouter au fichier CSV:
                ligne = []
            
                #Ajout du nom du shp:
                ligne.append(str(nomShp))
                
                #Ajout du nom champ nature:
                ligne.append(str(champNature))
            
                #Ajout du type de nature:
                nature = (feat.attribute(champNature))
                
                #Gestion des encodings pour les fichiers qui ne sont pas en UTF8:
                natureEncode = nature.encode()
                natureUnicode = unicode(natureEncode, 'utf8')
                #la valeur de type de nature de sol est encodée en binaire puis
                #décodée utf8
                
                #On remplace arbitrairement les caractères erreurs utf8 par la
                # lettre 'e'
                #Lors du calcul de visibilité passive, le même processus est appliqué
                #Cela permet d'éviter les problèmes d'encodings entre un type
                #de nature de sol encodé différemment dans le fichier CSV et dans 
                #le fichier shape
                natureErreurReplace = natureUnicode.replace(erreurEncodingUtf8, 'e')
                natureErreur2Replace = natureErreurReplace.replace(erreur2EncodingUtf8, 'e')
                
                #Pour éviter les problèmes d'encodings, les accents sont enlevés
                natureSansAccent = unicodedata.normalize('NFKD', natureErreur2Replace).encode('ascii', 'ignore')
                natureUtf = natureSansAccent.decode('utf8')
                    
                if natureUtf not in listeNatureType:
                    #Ajout du type de nature en utf8 sans accent
                    ligne.append(str(natureUtf))
                    
                    #Ajout du champ hauteur si existant:
                    if champHauteur != "":
                        ligne.append(champHauteur)
                        
                    else:
                        ligne.append("")
                
                    #Ajout des autres paramètres vides :
                    for i in range (0, 6):
                        ligne.append("")
                
                    ligne2 = ligne.copy()
                    lignesCsv.append(ligne2)
                    
                    listeNatureType.append(natureUtf)
                    
                i+=1
            
            feedback.pushInfo(str(listeNatureType))
        
        else:
            #Si le champ nature est vide:
            ligne = []
            ligne.append(str(nomShp))
            
            #Les colonnes champ nature de sol et type restent vident
            ligne.append("")
            ligne.append("")
            
            #Ajout du champ hauteur si existant:
            if champHauteur != "":
                ligne.append(champHauteur)
                
            else:
                ligne.append("")
        
            #Ajout des autres paramètres vides :
            for i in range (0, 6):
                ligne.append("")
        
            ligne2 = ligne.copy()
            lignesCsv.append(ligne2)
            
        
        """
        Ecriture dans le fichier csv de chaque ligne:
        """
        
        with open(cheminCsv, 'a', encoding='utf-8', newline='') as csvfile:
            rowWriter = csv.writer(csvfile, delimiter=';')
            for ligne in lignesCsv:
                rowWriter.writerow(ligne)
                
        csvfile.close()
        
        return {self.OUTPUT_CSV: cheminCsv}
         

    def name(self):
        """
        Returns the algorithm name, used for identifying the algorithm. This
        string should be fixed for the algorithm, and must not be localised.
        The name should be unique within each provider. Names should contain
        lowercase alphanumeric characters only and no spaces or other
        formatting characters.
        """
        return 'createcsvsursol'

    def displayName(self):
        """
        Returns the translated algorithm name, which should be used for any
        user-visible display of the algorithm name.
        """
        return self.tr("Création fichier CSV de paramétrage du sursol")

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
        
    def tr(self, string):
        return QCoreApplication.translate('Processing', string)
    
    def shortHelpString(self):

        helpInterface = "Ecriture du fichier CSV de paramétrage du sursol. \
            Créé automatiquement chaque ligne du fichier CSV de paramétrage \
                de sursol en vue d'un calcul de visibilité passive multi paramètres. \n \
                    Remplie les colonnes nom_shp.shp, nom champ nature de sol, type de nature de sol et \
                        nom champ hauteur s'il y a. \n \n Pour compléter le fichier CSV en une fois pour chaque fichier \
                            shp de sursol, ce processing doit être exécuté par processus de lot avec le même nom de fihcier csv \
                                en sortie pour chaque fichier shp.\n \
                                    L'extension du fichier en sortie doit être .csv\
                                        \n \n Attention : si un fichier shape provoque des erreurs de lecture \
                                         en utf8, le caractère concerné (exemple 'â') est remplacé par un 'e'. \
                                             Les changements de ce type dans le fichier CSV permettent d'éviter les erreurs \
                                                 dues à un encoding différent entre le fichier shp et le fichier CSV. Le même processus est appliqué pour chaque entité lors de l'exécution \
                                                     du plugin de visibilité passive multi paramètres (remplacement des caractères non lus en utf8 par un 'e'), ce qui permet d'affecter à chaque entité le paramétrage demandé dans le fichier CSV. \
                                                         De la même manière, pour éviter de potentielles erreurs liées à l'encoding, les accents sont également supprimés"

        return helpInterface

    def createInstance(self):
        return CreateCsvSursol()
