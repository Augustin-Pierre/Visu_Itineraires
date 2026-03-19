from qgis.core import *
from qgis.PyQt.QtCore import QVariant
import processing
import math

# Paramètre à adapter en fonction de la valeur choisie de l'offset
largeur = 2

# Chargement des layers
layer_crois = QgsProject.instance().mapLayersByName("noeuds_graph")[0]
layer_iti = QgsProject.instance().mapLayersByName("strokes_iti")[0]

list_points = []


# Fonction déterminant si un point correspond au début ou à la fin d'une ligne
def extr(ligne_geom, point_geom):
    """
    1 = point plus proche du début de la ligne
    0 = point plus proche de la fin de la ligne
    """
    if ligne_geom.isMultipart():  # correction pour  MultiLineString
        lines = ligne_geom.asMultiPolyline()
        if not lines:
            return None
        # On prend la ligne la plus longue ?
        line = max(lines, key=lambda l: QgsGeometry.fromPolylineXY(l).length())
        # print("ici")
    else:  # LineString simple
        line = ligne_geom.asPolyline()
        if not line:
            return None

    pt = point_geom.asPoint() if isinstance(point_geom, QgsGeometry) else point_geom

    start_pt = QgsPointXY(line[0]) # point de départ de la géométrie
    end_pt = QgsPointXY(line[-1]) # point final de la géométrie

    return 0 if pt.distance(end_pt) <= pt.distance(start_pt) else 1 # On regarde quelle est la distance minimale



# =============================================================================
# Algorithme de gestion des croisements
# =============================================================================

# ETAPE 1 : Création d'un buffer autour des croisements
proc_tampon = processing.run("native:buffer", 
               {'INPUT':layer_crois,
                'DISTANCE':10,
                'SEGMENTS':10,
                'END_CAP_STYLE':0,
                'JOIN_STYLE':0,
                'MITER_LIMIT':2,
                'DISSOLVE':False,
                'SEPARATE_DISJOINT':False,
                'OUTPUT':'TEMPORARY_OUTPUT'})

tampon = proc_tampon["OUTPUT"]
# QgsProject.instance().addMapLayer(tampon)

# Récupération de la frontière du buffer
frontiere = processing.run("native:boundary", 
{'INPUT':tampon,
'OUTPUT':'memory:front'})
layer_front = frontiere["OUTPUT"]
# QgsProject.instance().addMapLayer(layer_front)



# ETAPE 2 : Récupérer les points d'intersection entre la frontière et les strokes d'itinéraires

intersection = processing.run("native:lineintersections", {'INPUT':layer_front,
                                                           'INTERSECT':layer_iti,
                                                           'INPUT_FIELDS':['id'],
                                                           'INTERSECT_FIELDS':['id_iti','id_stroke','titre','num','numero','offset','rang'],
                                                           'INTERSECT_FIELDS_PREFIX':'',
                                                           'OUTPUT':'TEMPORARY_OUTPUT'})
layer_intersect = intersection["OUTPUT"]
# QgsProject.instance().addMapLayer(layer_intersect)


# ETAPE 3 : Extraire les tronçons d'itinéraires à l'extérieur des tampons
decoupe = processing.run("native:difference", {
    'INPUT': layer_iti,
    'OVERLAY': tampon,
    'OUTPUT': 'memory:layer_iti_visu'
})

layer_diff = decoupe["OUTPUT"]
# QgsProject.instance().addMapLayer(layer_diff)



# initialisation de la liste des points décalés
list_points = []


# Création de l'index spatial sur layer_iti 
index_iti = QgsSpatialIndex(layer_iti.getFeatures())

# on parcourt tous les points issue de l'intersection
for point in layer_intersect.getFeatures():

    pt_geom = point.geometry() # récupération de la géométrie du point
    
    # Supprimer les points vides 
    if pt_geom is None or pt_geom.isEmpty():
        continue

    # Récupérer les attributs
    
    pt = pt_geom.asPoint()
    offset = point["Offset"]
    id_iti_val = point["id_iti"]
    id_stroke = point["id_stroke"]
    rang = point["rang"]
    id_croisement = point["id"]
    
    
    # récupérer tous les tronçons qui passent par le point
  
    ids = index_iti.intersects(pt_geom.boundingBox())
    candidate_features = [layer_iti.getFeature(fid) for fid in ids]
    
    
    # ne garder que ceux avec le même id et contenant le point
    matching_features = [] # liste des troncons qui fonctionnent
    
    for f in candidate_features:
        if f["id_stroke"] == id_stroke and f.geometry().distance(pt_geom) <= 0.0001:  # Même id_stroke
            matching_features.append(f)

    if not matching_features:
        continue
    
    feat_iti = matching_features[0] # On récupère la première feature qui match, normalement une seule mais parfois bugs
    
    feat_id_stroke = feat_iti["id_stroke"]
    
    # récupérer le tronçon découpé afin de savoir si le point correspond au début ou à la fin du tronçon
    request = QgsFeatureRequest().setFilterExpression(f'"id_stroke" = {feat_id_stroke}')
    # récupère la première feature correspondante dans layer_diff
    feat_iti_decoup = next(layer_diff.getFeatures(request), None)
    
    if feat_iti_decoup is None:
        extremite = None
    else:
        extremite = extr(feat_iti_decoup.geometry(), pt_geom) # On récupère la valeur 0 ou 1 de extrémité
    

    # On réupère la géométrie du tronçon
    geom_iti = feat_iti.geometry()

    # calcul direction et point offset
    # Localisation du point sur la ligne
    # On calcule la normale au troncon au niveau du point d'intersection et on place un point à la distance 
    # correspondant à l'offset
    
    dist = geom_iti.lineLocatePoint(pt_geom) # distance du début de la ligne du point le plus proche sur la ligne 
    dist = max(0, min(dist, geom_iti.length())) # quelques bugs parfois sinon
    delta = 0.5
    
    p1 = geom_iti.interpolate(max(0, dist - delta)).asPoint() # point 1
    p2 = geom_iti.interpolate(min(geom_iti.length(), dist + delta)).asPoint() # point 2
    
    # vecteur local
    dx = p2.x() - p1.x()
    dy = p2.y() - p1.y()
    
    length = math.sqrt(dx*dx + dy*dy)
    dx /= length
    dy /= length
    
    # vecteur normal cohérent
    nx = dy
    ny = -dx
    
    # point offset
    d = offset * largeur
    new_point = QgsPointXY(pt.x() + nx*d, pt.y() + ny*d)
    angle = math.atan2(dy, dx)

    # Préparation du Layer des points décalés
    list_points.append({
        "id_pt": point.id(),
        "id_croisement" : id_croisement,
        "id_iti": id_iti_val,
        "id_stroke": id_stroke,
        "geom": new_point,
        "dx": dx,
        "dy": dy,
        "angle": angle,
        "offset" : offset,
        "rang": rang,
        "extremite" : extremite
    })




# Création d'une couche mémoire pour les points offset
layer_points = QgsVectorLayer(
    "Point?crs=" + layer_iti.crs().authid(),
    "points_offset",
    "memory"
)

provider = layer_points.dataProvider()

# Ajout des champs attributaires
provider.addAttributes([
    QgsField("id_pt", QVariant.Int),
    QgsField("id_croisement", QVariant.Int),
    QgsField("id_iti", QVariant.Int),
    QgsField("id_stroke", QVariant.Int),
    QgsField("angle", QVariant.Double),
    QgsField("offset", QVariant.Double),
    QgsField("dx", QVariant.Double),
    QgsField("dy", QVariant.Double),
    QgsField("rang", QVariant.Int),
    QgsField("extremite", QVariant.Int)
])
layer_points.updateFields()

# Création des features
features = []
for p in list_points:
    f = QgsFeature()
    f.setGeometry(QgsGeometry.fromPointXY(p["geom"]))
    f.setAttributes([p["id_pt"],p["id_croisement"], p["id_iti"],p["id_stroke"], p["angle"],p["offset"],p["dx"],p["dy"],p["rang"],p["extremite"]])
    features.append(f)

provider.addFeatures(features)
layer_points.updateExtents()




QgsProject.instance().addMapLayer(layer_points)
QgsProject.instance().addMapLayer(layer_diff)

layer_diff.setRenderer(layer_iti.renderer().clone())
layer_diff.triggerRepaint()
    
    