# -*- coding: utf-8 -*-
"""
Created on Fri May  1 12:39:38 2020

@author: projetdev
"""
import processing
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
                        QgsRasterLayer,
                        QgsProcessingUtils,
                        QgsVectorLayer,
                        QgsFeature,
                        QgsField
                        )
from processing.core.ProcessingConfig import ProcessingConfig
import chardet
import os
from qgis.PyQt.QtCore import QVariant
import unicodedata

class FonctionsPlugin:
    
    
    #Optimisation des calculs :
    def optimisationCalcul(point, radius, folderTemp, mnt, mne = None, mns = None):
        """
        Réduit la taille du MNT / MNE / MNS en fonction du radius pour
        optimiser les temps de calculs
        
        INPUT : 
            - point: QgsVectorLayer (point (ou polygone))
            - radius: integer
            - folderTemp : string
            - mnt : string
            - mne : string or NoneType
            - mns : string or NoneType
            
        OUTPUT :
            - mnt_cut: string
            - mne_cut: string or None
            - mns_cut: string or None
            
        Cette fonction permet d'optimiser les temps de calcul en réduisant
        la taille du mnt, mne, mns en fonction du rayon d'analyse sur lequel
        va s'effectuer le calcul de visibilité passive.
        Créé un buffer à partir du point ou polygone observé de la longueur du radius + 100 m
        L'étendue de ce buffer constitue le masque pour réduire la taille du mnt, 
        mne, mns.
        
        Retourne le chemin vers le mnt, mne, mns découpés (None pour le mne et mns si None en entrée).
            
        """
        #Reprojeter le point en entrée dans un système métrique (2154) afin de s'assurer
        #que le buffer créé est correct.
        
        observedPointMetric = folderTemp + '/reproject.shp'
        processing.run('native:reprojectlayer',
        {'INPUT': point,
         'TARGET_CRS':'EPSG:2154',
         'OUTPUT': observedPointMetric})

        #Création d'un buffer
        buffer = folderTemp + '/tampon.shp'
        processing.run('native:buffer',
        {'INPUT': observedPointMetric,
         'DISTANCE': radius+100,
         'DISSOLVE': True,
         'OUTPUT': buffer})
        #On ajoute une marge de 100 m pour éviter de potentielles erreurs si
        #jamais l'emprise du rayon d'analyse est légèrement différente de celle
        #du buffer.

        #Découpe du raster selon l'emprise du buffer:              
        bufferVector = QgsVectorLayer(buffer)
        ext = bufferVector.extent()
        
        #Découpage du MNT, MNE, MNS :
        mnt_cut = folderTemp + '/mntCut.tif'
        mne_cut = folderTemp + '/mneCut.tif'
        mns_cut = folderTemp + '/mnsCut.tif'
        
        processing.run('gdal:cliprasterbyextent',
        {'INPUT': mnt,
        'PROJWIN': ext,
        'NODATA': -99999,
        'OUTPUT': mnt_cut})
        
        #Découpage du mne et mns seulement si entré en paramètre
        if mne != None and mns != None:
            processing.run('gdal:cliprasterbyextent',
            {'INPUT': mne,
            'PROJWIN': ext,
            'NODATA': -99999,
            'OUTPUT': mne_cut})
        
            processing.run('gdal:cliprasterbyextent',
            {'INPUT': mns,
            'PROJWIN': ext,
            'NODATA': -99999,
            'OUTPUT': mns_cut})
        
        else:
            mne_cut = None
            mns_cut = None
        
        return (mnt_cut, mne_cut, mns_cut)

    def constructionSursol(cheminCsv, dossier, mntRasterLayer, folderTemp):
        """
        Retourne l'emplacement du fichier shape de sursol fusionné.
        
        Fusionne plusieurs fichiers SHP en vue d'un calcul de visibilité passive.
        Le fichier shape créé prend en compte les paramétrages indiqués dans
        le fichier CSV. 
        
        Pour chaque entité :
            - Attribution d'un code selon le type de nature de sol
            - Attribution d'une hauteur simulée si champ hauteur inexistant
            dans le fichier shape, et ce selon le type de nature de sol
            - Attribution d'une hauteur simulée de manière prioritaire si il
            existe un champ hauteur mais que l'on souhaite simuler une hauteur
            pour un type de nature de sol.
        
        INPUT:
            - cheminCsv : string
            - dossier : string
            - mntRasterLayer : QgsRasterLayer
            - folderTemp : string
            
        OUTPUT:
            - fusionSursol : string
        
        Pour le fichier CSV de paramétrage du sursol:
            Récupération de chaque ligne du fichier CSV.
        
        Pour le chemin vers le dossier contenant les fichiers SHP:
            Pour chaque fichier contenu dans le dossier, on ne conserve que les 
            extensions shp.
        
        Pour chaque fichier shp:
            Chaque fichier est reprojeté dans le CRS du MNT afin de pouvoir ensuite
            découper chaque fichier selon l'emprise du MNT afin de raccourcir
            les temps de calcul.
            
        Les entités sont extraites de chaque fichier shape afin de recréer des shapes
        copies propres, en fonction des paramètres définis dans le fichier CSV de paramétrage.
        
        Modèle de table attributaire pour chaque shape : champ nature, champ code, champ hauteur
        
        Une union est réalisée sur chaque fichier shape pour ensuite ne conserver que
        la valeur de hauteur la plus grande (avec la nature de sol et le code associée).
        
        """
        
        #Création d'un fichier temporaire pour les couches intermédiaires
        folderTemp2 = folderTemp + '/filesProjCut'
        
        if not os.path.exists(folderTemp2):
            os.makedirs(folderTemp2)
        
        erreurEncodingUtf8 = '\ufffd'
        erreur2EncodingUtf8 = '?'
        
        #Lecture du fichier CSV
        readEncoding = open(cheminCsv, 'rb')
        encode = chardet.detect(readEncoding.read())['encoding']
        readEncoding.close()
        
        paramCsv=[]
        with open(cheminCsv, 'r', encoding = encode) as fichierCsv:
            while 1:
                row=fichierCsv.readline()
                if row=="":
                    break
                #row = row.replace(";\n", "")
                row = row.replace("\n", "")
                val=row.split(";")
                paramCsv.append(val)
        fichierCsv.close()
        
        #Suppression de la première ligne qui contient les titres
        del(paramCsv[0])
        
        #Récupération d'une liste des fichiers contenus dans le dossier:
        listeFichier = os.listdir(dossier)
        
        #Conserver seulement les extensions .shp:
        listeFichierShpUncutUnproj = []
        for i in range (0, len(listeFichier)):
            if '.shp' in listeFichier[i]:
                listeFichierShpUncutUnproj.append(dossier+"/"+listeFichier[i])
        
        """
        Reprojeter les couches selon le CRS du MNT:
        """
        ext = mntRasterLayer.extent()
        crsRaster = mntRasterLayer.crs()
        
        listeFichierShpProj = []
        
        for i in range(0, len(listeFichierShpUncutUnproj)):
            fichierShpUnProjVector = QgsVectorLayer(listeFichierShpUncutUnproj[i])
            
            for ligneCsv in paramCsv:
                if ligneCsv[0] in listeFichierShpUncutUnproj[i]:
                    fichierShpProj = folderTemp + '/' + ligneCsv[0]
                    break
            creationShpProj = processing.run('native:reprojectlayer',
            {'INPUT': fichierShpUnProjVector,
            'TARGET_CRS':crsRaster,
            'OUTPUT': fichierShpProj})
            
            listeFichierShpProj.append(fichierShpProj)
        
        
        """
        Réduire la taille des fichiers shp selon l'emprise du mnt
        """
        
        listeFichierShp = []
        
        for i in range(0, len(listeFichierShpProj)):
            fichierShpVector = QgsVectorLayer(listeFichierShpProj[i])
            
            for ligneCsv in paramCsv:
                if ligneCsv[0] in listeFichierShpProj[i]:
                    fichierShpCut = folderTemp2 + '/' + ligneCsv[0]
                    break
            
            creationShpCut = processing.run('gdal:clipvectorbyextent',
            {'INPUT': fichierShpVector,
            'EXTENT': ext,
            'OUTPUT': fichierShpCut})
            
            listeFichierShp.append(fichierShpCut)
            
        
        """
        Créer des shp copie avec seulement le champ nature, code et hauteur:
        """
        
        #Avec la liste des fichiers shp : création d'une couche temporaire
        #par fichier qui conserve seulement le champ nature, à laquelle est attribuée
        #un code selon le paramétrage du CSV ainsi qu'une hauteur
        listeLayerSursol = []
        
        for i in range (0, len(listeFichierShp)):
            #On récupère chaque ligne du fichier CSV propre à la couche :
            paramCsvLayer = []
            for nomShp in paramCsv:
                
                if nomShp[0] in listeFichierShp[i]:
                    paramCsvLayer.append(nomShp)
            
            #Récupération du nom du champ nature depuis le fichier CSV
            nomChampNatureCsv = paramCsvLayer[0][1]
            
            #Récupération du nom du champ hauteur depuis le fichier CSV
            nomChampHauteurCsv = paramCsvLayer[0][3]
            
            #Récupération des entités (features)            
            layer = QgsVectorLayer(listeFichierShp[i])
            
            #Définition de l'encoding en utf8
            layer.setProviderEncoding('utf8')
            
            feats = [feat for feat in layer.getFeatures()]
            
            featsFinal = []
            
            for feat in feats:
                geom = feat.geometry()
                
                if nomChampNatureCsv != "":
                    #Vérifie si le champ nature a été précisé
                    
                    nature = (feat.attribute(nomChampNatureCsv))
                    #Récupérer la valeur de l'attribut nature pour ce feature.
                    
                    if nature != None:
                        #Vérifie si l'entité en question a une nature spécifiée
                        
                        #Gestion des encodings pour les fichiers qui ne sont pas en utf8 :
                        natureEncode = nature.encode()
                        natureUnicode = unicode(natureEncode, 'utf8')
                        #La valeur de l'attribut est transformée en utf8 : on 
                        #s'assure que la valeur est décodée en utf8
                        
                        #Si une erreur utf8 est détectée, la valeur erreur est
                        #remplacé arbitrairement par un e
                        #Objectif: empêcher qu'un type de sursol d'une entité 
                        #ne soit pas reconnu comme égale à un type de nature
                        #décrit dans le fichier CSV à cause d'un encoding différent
                        natureErreurReplace = natureUnicode.replace(erreurEncodingUtf8, 'e')
                        natureErreur2Replace = natureErreurReplace.replace(erreur2EncodingUtf8, 'e')
                        
                        #On élimine les accents pour éviter des erreurs d'encoding
                        natureSansAccent = unicodedata.normalize('NFKD', natureErreur2Replace).encode('ascii', 'ignore')
                        natureUtf = natureSansAccent.decode('utf8')
                        
                        #On cherche le type de nature correspondant dans le fichier CSV :
                        for param in paramCsvLayer:
                            #Gestion des encodings pour les fichiers qui ne sont pas en Utf8:
                            #Le même processus est appliquée au type de nature 
                            paramNature = param[2]
                            paraNatEncode = paramNature.encode()
                            paraNatUnicode = unicode(paraNatEncode, 'utf8')
                            paraNatErreurReplace = paraNatUnicode.replace(erreurEncodingUtf8, 'e')
                            paraNatSansAccent = unicodedata.normalize('NFKD', paraNatErreurReplace).encode('ascii', 'ignore')
                            paraNatUtf = paraNatSansAccent.decode('utf8')
                        
                            #Récupérer la ligne correspondant à ce type de nature :
                            if natureUtf == paraNatUtf:
                                
                                # Récupération du code
                                code = param[5]
                                if code == "":
                                    code = 0
                                    #Si aucun code n'a été précisé, il est mis à 0
                                
                                hauteur = param[4]
                                #Si la hauteur est vide, on récupère la valeur de hauteur pour l'entité
                                if hauteur == "":
                                    if nomChampHauteurCsv != "":
                                        #On vérifie qu'un nom de champ a été entré
                                        hauteur = (feat.attribute(nomChampHauteurCsv))
                                    else :
                                        hauteur = None
                                        
                                if hauteur != None:
                                    #Si une hauteur a pu être affectée à l'entité
                                    #Ajout de l'entité au fichier shape créé
                                    newFeat = QgsFeature()
                                    newFeat.setGeometry(geom)
                                    
                                    newFeat.setAttributes([str(natureUtf), int(code), float(hauteur)])
                                    
                                    featsFinal.append(newFeat)
                                    
                else:
                    #Si aucun champ nature n'a été précisé:
                    #Signifie qu'il n'y a qu'une seule ligne sur le fichier CSV
                    #pour ce fichier
                    natureUtf = 'indifferencie'
                    
                    code = paramCsvLayer[0][5]
                    if code == "":
                        code = 0
                    
                    hauteur = paramCsvLayer[0][4]
                    
                    #Si la hauteur est vide, on récupère la valeur de hauteur pour l'entité
                    if hauteur == "":
                        if nomChampHauteurCsv != "":
                            #On vérifie qu'un nom de champ a été entré
                            hauteur = (feat.attribute(nomChampHauteurCsv))
                        else :
                            hauteur = None
                            
                    if hauteur != None:
                        #Si une hauteur a pu être affectée à l'entité
                        #Ajout de l'entité au fichier shape créé
                        newFeat = QgsFeature()
                        newFeat.setGeometry(geom)
                        
                        newFeat.setAttributes([str(natureUtf), int(code), float(hauteur)])
                        
                        featsFinal.append(newFeat)
                        
            
            #Création des champs:
            fieldNature = QgsField('nature', QVariant.String, 'String', len=100)
            fieldCode = QgsField('code', QVariant.Int, 'Integer', len=20)
            fieldHauteur = QgsField('hauteur', QVariant.Double, 'Double', len=20, prec=6)
            fields = [fieldNature, fieldCode, fieldHauteur]
            
            #Création du shp propre:
            layerFin = QgsVectorLayer("MultiPolygon", "sursol"+str(i), 'memory')
            
            #Récupérer le système de référence du shp source:
            srid = layer.crs()
            sridWkt = srid.toWkt()
            
            #Géoréférencement du nouveau fichier shp à partir de celui du shp source
            #càd celui du MNT
            crs = layerFin.crs()
            crs.createFromWkt(sridWkt)
            layerFin.setCrs(crs)
        
            #Ajout des champs au shp propre:
            layerFinData = layerFin.dataProvider()
            layerFinData.setEncoding(u'UTF-8')
            layerFinData.addAttributes(fields)
            layerFin.updateFields()
            
            #Ajout des entités / features au shp propre:
            layerFinData.addFeatures(featsFinal)
            
            #Ajout du shp propre à la liste des shp propres (liste de VectorLayer)
            listeLayerSursol.append(layerFin)
        
        """
        Union de toutes les couches :
        """
        
        #Première union à réaliser:
        path_union = listeLayerSursol[0]
        
        #Condition pour savoir s'il est nécessaire de réaliser une union des
        #couches
        if len(listeLayerSursol) > 1:
            #On réalise un enchainement d'union:
            #La couche résultat contient les champs de chacune des deux couches unies
            #Lorsque qu'il y a union, aux endroits où les couches se superposent
            #une nouvelle entité est créé, qui contient les attributs des
            #champs de chaque couche
            listeLayerSursol2 = listeLayerSursol[1:len(listeLayerSursol)]
            
            for i in range (0, len(listeLayerSursol2)):
                path_sortie = folderTemp + '/union'+str(i)+'.shp'
                processing.run('native:union',
                {'INPUT': path_union,
                'OVERLAY' : listeLayerSursol2[i],
                'OVERLAY_FIELDS_PREFIX' : str(i),
                'OUTPUT': path_sortie})
                #Les champs résultants de l'union sont préfixés i
                path_union = path_sortie
                
        
            #Récupération de la couche finale:
            fusionSursol = path_union
            
            #Les champs de la couche finale sont par exemple: nature, code, hauteur,
            #nature0, code0, hauteur0, nature1...
            
            #Récupération de la couche comme objet VectorLayer
            fichier_fusion_vector = QgsVectorLayer(fusionSursol)
            
            #Obtenir la liste des champs:
            liste_champs = fichier_fusion_vector.dataProvider().fields().toList()
            
            #Récupérer les index des champs à supprimer:
            index_champs_deleted = list(range(3, len(liste_champs)))
            
            """
            Assigner au champ hauteur la hauteur maximum parmi tous les champs
            hauteurs issus de l'union des couches
            """
            
            #Récupérer l'ensemble des champs hauteur :
            liste_champs_hauteur = []
            for field in fichier_fusion_vector.fields():
                if 'hauteur' in field.name():
                    liste_champs_hauteur.append(field.name())
            
            #Récupérer l'ensemble des champs nature:
            liste_champs_nature = []
            for field in fichier_fusion_vector.fields():
                if 'nature' in field.name():
                    liste_champs_nature.append(field.name())  
            
            #Récupérer l'ensemble des champs code:
            liste_champs_code = []
            for field in fichier_fusion_vector.fields():
                if 'code' in field.name():
                    liste_champs_code.append(field.name())
            
            features = [feat for feat in fichier_fusion_vector.getFeatures()]
            
            
            #Conserver la hauteur la plus grande:
            fichier_fusion_vector.startEditing()
            
            for obj in features:
                valHauteur = 0
                #valNature = ""
                #valCode = 0
                for i in range (0, len(liste_champs_hauteur)):
                    if obj.attribute(liste_champs_hauteur[i]) != None:
                        if obj.attribute(liste_champs_hauteur[i]) >= valHauteur:
                            valHauteur = obj.attribute(liste_champs_hauteur[i])
                            fichier_fusion_vector.changeAttributeValue(obj.id(), 2, valHauteur)
                            # 2 représente l'index du champ 'hauteur'
                            
                            valNature = obj.attribute(liste_champs_nature[i])
                            fichier_fusion_vector.changeAttributeValue(obj.id(), 0, valNature)
                            
                            valCode = obj.attribute(liste_champs_code[i])
                            fichier_fusion_vector.changeAttributeValue(obj.id(), 1, valCode)
                    
            fichier_fusion_vector.commitChanges()
            
            #Suppression des champs désormais inutiles
            fichier_fusion_vector.dataProvider().deleteAttributes(index_champs_deleted)
            fichier_fusion_vector.updateFields()
        
        else:
            #Si un seul fichier en entrée:
            #On reprojecte la couche, pour enregistrer le fichier dans le dossier
            #temporaire spécifique:
            fusionSursol = folderTemp + '/union0.shp'
            processing.run('native:reprojectlayer',
            {'INPUT': path_union,
            'TARGET_CRS':crsRaster,
            'OUTPUT': fusionSursol})
                    
        return fusionSursol
    
    def constructionListeVarSursol(cheminCsv):
        """
        Retourne un tuple contenant la liste des codes de nature de sol et la
        liste des combinaisons de variations de hauteur de sursol tel que
        paramétré dans le fichier CSV.
        
        INPUT:
            - cheminCsv : string
            Contient le chemin vers le fichier CSV de paramétrage du sursol
            
        OUTPUT:
            - (listeCodes, allVarMns) : tuple
            - listeCodes : list[integer]
            - allVarMns : list[list]
            - allVars[list] : float
        
        La fonction lit les colonnes du fichier CSV de paramétrage du sursol
        qui concernent les variations par type de nature de sol.
        
        Pour chaque code différent indiqué dans le fichier CSV, on récupère
        la variation relative minimum, la variation relative maximum et le pas
        de variation.
        
        Pour chaque code, on créé une liste des variations demandées.
        
        A partir de chaque liste de variations on créé une liste qui contient
        toutes les combinaisons de variations demandées.
        
        Exemple:
            Lecture du fichier CSV:
                code 1 : var min = -5, var max = 5, pas = 10
                code 2 : var min = 0, var max = 20, pas = 10
                
            liste de variation pour le code 1 : [-5, 5]
            liste de variation pour le code 2 : [0, 10, 20]
            
            listeCodes : [1, 2]
            allVarMns : [[-5, 0], [-5, 10], [-5, 20], [5, 0], [5, 10], [5, 20]]
            
            allVarMns est la liste de combinaison de variations sur laquelle l'algorithme
            de calcul de visibilité passive multi-paramètres va boucler.
            
            Pour la première combinaison de variation, tous les pixels du MNE et
            du MNS correspondants au code 1 seront incrémentés de -5 mètres,
            et tous les pixels correspondants au code 2 seront incrémentés de 0 mètre.

        """
        
        #Lecture du fichier CSV
        readEncoding = open(cheminCsv, 'rb')
        encode = chardet.detect(readEncoding.read())['encoding']
        readEncoding.close()
        
        paramCsv=[]
        with open(cheminCsv, 'r', encoding = encode) as fichierCsv:
            while 1:
                row=fichierCsv.readline()
                if row=="":
                    break
                #row = row.replace(";\n", "")
                row = row.replace("\n", "")
                val=row.split(";")
                paramCsv.append(val)
        fichierCsv.close()
        
        #Suppression de la première ligne :
        del(paramCsv[0])
        
        
        #Obtenir les codes pour lesquelles on souhaite faire varier la hauteur:
        listeSursolVariant = []
        code_utilise = []
        for i in range (0, len(paramCsv)):
            if paramCsv[i][5] != "" and paramCsv[i][6] != "" and paramCsv[i][7] != "" and paramCsv[i][8] != "":
                sursolVariant = [paramCsv[i][5], paramCsv[i][6], paramCsv[i][7], paramCsv[i][8]]
                code_util = paramCsv[i][5]
                if sursolVariant not in listeSursolVariant:
                    if code_util not in code_utilise:
                        code_utilise.append(code_util)
                        listeSursolVariant.append(sursolVariant)
        
        #Calcul des listes de variations pour chaque variation souhaitée:
        #Pour chaque liste de variation, on ajoute le code associé à la liste
        #des codes: permet d'associer listeCodes[i] à listeVariations[i]
        
        listeVariations = []
        listeCodes = []
        for elem in listeSursolVariant:
            liste_var = []
            code = int(elem[0])
            varMin = float(elem[1])
            varMax = float(elem[2])
            pas = float(elem[3])
            
            minVarI = int(varMin * 100)
            maxVarI = int(varMax * 100)
            pasI = int(pas * 100)
            
            i = 0
        
            if varMin != varMax and varMin < varMax and pas > 0 :
                while minVarI <= maxVarI:
                    #Création de la liste des hauteurs avec le pas de variation entre la borne inférieure et la borne supérieure 
                    liste_var.append(minVarI / 100)
                    minVarI += pasI
                    
                    i+=1
                    if i > 50:
                        break
            else:
                #Si minHauteur == maxHauteur ou supérieur à maxHauteur:
                liste_var.append(varMin)
                
            listeVariations.append(liste_var)
            listeCodes.append(code)
        
        """
        Obtenir une liste qui combine les différentes variations de hauteur possible:
            
        """
        #Liste de toutes les combinaisons de variations relatives possibles
        allVarMns = []
        
        #Une combinaison de variation
        elemVar = []
        
        #Compteurs pour itérer dans les boucles
        counter = []
        
        sizeMaxVar = 1
        

        for i in range (0, len(listeVariations)):
            #Calcul du nombre de combinaisons de variations:
            sizeMaxVar = sizeMaxVar * len(listeVariations[i])
            
            #Création d'un compteur à 0 pour chaque liste de variation
            counter.append(0)
        
        #Pour chaque combinaison de variation:
        for i in range (0, sizeMaxVar):
            #Pour chaque liste de variation:
            for j in range(0, len(listeVariations)):
                #Ajout de la variation relative du type de nature de sol [j] à la combinaison de variation 
                elemVar.append(listeVariations[j][counter[j]])
            
            #Pour chaque liste de variation:
            for j in range(0, len(listeVariations)):
                #Incrémentation du compteur pour parcourir toutes les variations possibles:
                counter[j] += 1
                
                #Si le compteur pour la liste de variation j n'a pas parcouru toute
                #la longueur de la liste de variation j, on sort de la boucle
                if counter[j] <= (len(listeVariations[j])-1):
                    break
                
                else:
                    #Sinon, le compteur pour cette liste de variation est mis
                    #à 0.
                    counter[j] = 0
            
            #Ajout de la combinaison de variation à la liste des combinaisons
            #de variations et réinitialisation
            elemVar2 = elemVar.copy()
            allVarMns.append(elemVar2)
            elemVar = []
    
            
        return (listeCodes, allVarMns)