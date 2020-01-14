from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingMultiStepFeedback,
    QgsProcessingParameterVectorLayer,
    QgsProcessingParameterRasterLayer,
    QgsProcessingParameterMultipleLayers,
    QgsProcessingParameterNumber,
    QgsProcessingParameterVectorDestination,
    QgsProcessingOutputFolder
)
from qgis.core import (
    QgsGeometry,
    QgsVectorLayer,
    QgsFeature,
    QgsVectorFileWriter,
    QgsFields,
    QgsWkbTypes,
    QgsCoordinateReferenceSystem,
    QgsFields,
    QgsField,
)
from qgis.PyQt.QtCore import QVariant
import processing


class CreateViewshedFromSeveralPoints(QgsProcessingAlgorithm):
    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterVectorLayer(
                "points", "Points", types=[QgsProcessing.TypeVectorPoint]
            )
        )

        self.addParameter(QgsProcessingParameterRasterLayer("mnt", "MNT"))

        self.addParameter(
            QgsProcessingParameterVectorDestination("OUTPUT_VIEWPOINTS", "Points de vue créés")
        )
    '''
        self.addParameter(
            QgsProcessingOutputFolder("OUTPUT_FOLDER", "La somme des visions passives")
        )
    '''
    def processAlgorithm(self, parameters, context, model_feedback):
        # entrées
        points = self.parameterAsVectorLayer(parameters, "points", context)
        mnt = self.parameterAsRasterLayer(parameters, "mnt", context)

        # sorties
        output_viewpoints = self.parameterAsOutputLayer(parameters, "OUTPUT_VIEWPOINTS", context)
        output_folder = "D:/Documents/data/visibilite/donnees"
        # output_folder = self...(parameters, "OUTPUT_FOLDER", context)

        # variables propres à Processing
        feedback = QgsProcessingMultiStepFeedback(
            points.featureCount() * 2, model_feedback
        )
        results = {}

        # Verification d'u attribut ID
        if points.fields().indexOf("ID") < 0:
            feedback.reportError(
                "Les points doivent avoir un attribut numérique ID unique", True,
            )
            return {}

        # Calcul de la sortie des points de vue
        processing.run(
            "Choucas:Création de point de vue",
            {
                "OBSERVER_POINTS": points,
                "DEM": mnt,
                "OBSERVER_ID": "id",
                "RADIUS": 5000,
                "RADIUS_FIELD": None,
                "OBS_HEIGHT": 0,
                "OBS_HEIGHT_FIELD": None,
                "TARGET_HEIGHT": 0,
                "TARGET_HEIGHT_FIELD": None,
                "OUTPUT": output_viewpoints,
            },
        )

        results["OUTPUT"] = output_viewpoints
        # print(output_viewpoints)
        # Les print() dans l'interface Python de QGIS semblent faire planter QGIS

        # Calcul de la sortie des DBH par point de vue
        
        id_pt = 7
        for i in range(0, 2):
            partie1 = output_folder + '|layerid=0|subset="ID" = \''
            point_obs_id = partie1 + str(i) + "'"
            dbh_output_temp = output_folder + "/temp_dbh.tif"
            output_passive = (
                output_folder
                + "/V0_qgis_rgealti5_iter_"
                + str(i)
                + "_mne0_c1_13_obs160_"
                + "variation_xy_pt_"
                + str(id_pt)
                + ".tif"
            )
            '''
            print(point_obs_id)
            print(dbh_output_temp)
            print(output_passive)

            processing.run(
                "Choucas:Calcul de la vision active, passive et le raster depth below horizon à partir du point d observation et du MNT ",
                {
                    "OBSERVER_POINTS": point_obs_id,
                    "Hobs": 1.6,
                    "DEM": mnt,
                    "USE_CURVATURE": True,
                    "REFRACTION": 0.13,
                    "OUTPUT_DBH": dbh_output_temp,
                    "OUTPUT_PASSIVE": output_passive,
                },
            )
            '''
        return results

    def name(self):
        return "createviewshedfromseveralpoints"

    def displayName(self):
        return "Créer un viewshed à partir de plusieurs points"

    def group(self):
        return "Visibilite"

    def groupId(self):
        return "Visibilite"

    def createInstance(self):
        return CreateViewshedFromSeveralPoints()
