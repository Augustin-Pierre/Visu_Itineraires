from qgis.core import *
from qgis.PyQt.QtCore import QVariant

# chargement des layers
layer = QgsProject.instance().mapLayersByName("points_offset")[0] 

# récupération des noms des attributs, car ils ont un peu changé, donc je les définis avant ça évite de tout changer
RANG = "rang"
FIELD_DX = "dx"
FIELD_DY = "dy"
ITIN_ID = "id_iti"
ID_CROIS = "id_croisement"

# Formater la nouvelle couche
crs = layer.crs()
out_layer = QgsVectorLayer("LineString?crs=" + crs.authid(), "raccords", "memory")
pr = out_layer.dataProvider()

pr.addAttributes([
    QgsField("itin_id", QVariant.Int),
    QgsField("rang_a", QVariant.Int),
    QgsField("rang_b", QVariant.Int)
])
out_layer.updateFields()

# organiser par itinéraire et rang
itins = {}

# On parcourt tous les points décalés (points_offset) et on attribut à chaque point son itineraire et rang
for f in layer.getFeatures():
    
    itin = f[ITIN_ID]
    r = f[RANG]
    if itin not in itins:
        itins[itin] = {}
    if r not in itins[itin]:
        itins[itin][r] = []
    itins[itin][r].append(f)


features_out = []



for itin_id, pts_by_rang in itins.items():
    rangs = sorted(pts_by_rang.keys())
    
    for rang_a in rangs:

        rang_b = rang_a + 1 # le rang indiquant l'ordre des strokes dans l'itinéraire, il s'incrémente de 1 à chaque fois

        if rang_b not in pts_by_rang:
            continue

        pts_a = pts_by_rang[rang_a] # On récupère les points de rang a
        pts_b = pts_by_rang[rang_b] # on récupère les points de rang b

        # index des points du rang B par id_croisement
        pts_b_by_cross = {}
        for pb in pts_b:
            cross_id = pb[ID_CROIS]
            pts_b_by_cross.setdefault(cross_id, []).append(pb)

        for pa in pts_a:
            if pa["extremite"] != 0:  # ne garder que les points au "début" des strokes
                continue
            cross_id = pa[ID_CROIS]
            if cross_id not in pts_b_by_cross:
                continue
        
            for pb in pts_b_by_cross[cross_id]:
                if pb["extremite"] != 1:  # ne garder que les points à la "fin" des strokes
                    continue
        
                # coordonnées des points
                P0 = pa.geometry().asPoint()
                P1 = pb.geometry().asPoint()
        
                geom = QgsGeometry.fromPolylineXY([P0, P1]) # Création d'une droite entre les points
        
                fnew = QgsFeature(out_layer.fields())
                fnew.setGeometry(geom)
                fnew.setAttributes([itin_id, rang_a, rang_b])
        
                features_out.append(fnew)

pr.addFeatures(features_out)
out_layer.updateExtents()

QgsProject.instance().addMapLayer(out_layer)