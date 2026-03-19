"""
/***************************************************************************
Gestion des fonctions liées aux strokes
***************************************************************************/
"""

from collections import defaultdict

from qgis.core import (
    QgsProject,
    QgsVectorLayer,
    QgsSpatialIndex,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsFeatureRequest,
    QgsLineSymbol,
    QgsSimpleLineSymbolLayer,
    QgsUnitTypes,
    QgsField,
    QgsProperty,
    QgsRendererCategory,
    QgsCategorizedSymbolRenderer
)
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtCore import QVariant

import processing
import colorsys
from collections import Counter
from itertools import combinations


# =============================================================================
# Fonction pour extraire les noeuds du réseau
# =============================================================================

def detect_noeud_iti(layer, nom_champ_id_iti ,nom_layer_res) : #layer en linestring
    crs=layer.crs().authid()
    layer_trav = QgsVectorLayer(f"Point?crs={crs}", f"{nom_layer_res}", "memory")
    pr = layer_trav.dataProvider()
    
    # on récupère tous les points du graph dans un set
    points = set()

    for feat in layer.getFeatures():
        geom = feat.geometry()
        point = geom.asPolyline()
        points.add(point[0])
        points.add(point[-1])
        
    # on créer un dictionnaire qui associe à chaque point ses voisins par le graphe
    pt_voisins = {pt: set() for pt in points}
    
    # on créer un dictionnaire qui associe à chaque point les id_iti des intinéraires passant par là
    id_iti_pt = {pt: set() for pt in points}
    
    # création du set des noeuds à garder
    garder=set()
    
    # remplissage des dictionnaires
    for f in layer.getFeatures():
        line = f.geometry().asPolyline()
        start = QgsPointXY(line[0])
        end = QgsPointXY(line[-1])
        
        pt_voisins[start].add(end)
        pt_voisins[end].add(start)
        
        id_iti_pt[start].add(f[nom_champ_id_iti])
        id_iti_pt[end].add(f[nom_champ_id_iti])
    
    # degré du noeud > 2
    for pt in id_iti_pt.keys() :
        if len(pt_voisins[pt]) > 2 :
            garder.add(pt)
    
        # si l'itinéraire fait un demi tour
        else :
            itis = []
            for voisin in pt_voisins[pt] :
                itis.extend(id_iti_pt[voisin])
            decompte_iti = Counter(itis)
            unique = [iti for iti,freq in decompte_iti.items() if freq==1]
            if len(unique)>0 and bool(set(unique) & set(id_iti_pt[pt])):
                garder.add(pt)
    
    features_to_add = []

    for p in garder:
        feat = QgsFeature()
        feat.setGeometry(QgsGeometry.fromPointXY(p))
        features_to_add.append(feat)
    
    pr.addFeatures(features_to_add)
    layer_trav.updateExtents()
    
    return layer_trav

# =============================================================================
# Fonction utilitaire pour vérifier si un point est proche d'un nœud
# =============================================================================

def is_near_node(pt, index_nodes, layer_noeuds_graph, tolerance=1e-6):
    nearest_ids = index_nodes.nearestNeighbor(pt, 1)
    if not nearest_ids:
        return False
    nearest_node = next(layer_noeuds_graph.getFeatures(QgsFeatureRequest(nearest_ids[0])))
    dist = pt.distance(nearest_node.geometry().asPoint())
    return dist < tolerance

# =============================================================================
# Fonction pour attribuer une couleur par itinéraire
# =============================================================================

def generate_distinct_colors(n, saturation=0.75, value=0.9):
    colors = []
    for i in range(n):
        hue = i / float(n)
        r, g, b = colorsys.hsv_to_rgb(hue, saturation, value)
        color = QColor(int(r*255), int(g*255), int(b*255))
        colors.append(color)
    return colors

# =============================================================================
# Fonction principale
# =============================================================================

def lancer_tout(chemin_iti, chemin_res, largeur, tolerance, progression=None):

    if progression:progression(10, "Chargement des couches...")
    layer_iti = QgsVectorLayer(chemin_iti, "itineraire", "ogr")
    layer_res = QgsVectorLayer(chemin_res, "reseau", "ogr")
    # QgsProject.instance().addMapLayer(layer_iti)
    # QgsProject.instance().addMapLayer(layer_res)

    #------------------------------------
    # Création des strokes routiers
    #------------------------------------
    if progression: progression(15, "Création des strokes routiers...")

    paraminput0 = {
            'INPUT':layer_res,
            'METHOD':1,
            'OUTPUT':'memory:iti_eclate_fixgeom'
            }

    paramoutput0 = processing.run("native:fixgeometries", paraminput0)
    layer_res_fixegeom = paramoutput0["OUTPUT"]

    paraminput1 = {
            'INPUT':layer_res_fixegeom,
            'FIELD':[],
            'SEPARATE_DISJOINT':True,
            'OUTPUT':'memory:strokes_routiers'
    }

    paramoutput1 = processing.run("native:dissolve",paraminput1)
    layer_strokesroute = paramoutput1["OUTPUT"]
    QgsProject.instance().addMapLayer(layer_strokesroute)


    #------------------------------------
    # Création des strokes d'itinéraires
    #------------------------------------

    if progression: progression(30, "Création des strokes d'itinéraires...")

    # Subdivision des itineraires en segments

    # créer la couche
    crs = layer_iti.crs().authid()
    layer_iti_eclate = QgsVectorLayer(f"LineString?crs={crs}", "iti_eclate", "memory")
    pr1 = layer_iti_eclate.dataProvider()

    # ajouter les mêmes champs
    pr1.addAttributes(layer_iti.fields())
    pr1.addAttributes([QgsField("rang", QVariant.Int)])
    layer_iti_eclate.updateFields()

    # ajout d'un attribut rang pour l'indexation des segments dans l'ordre
    layer_iti_eclate.startEditing()

    for f in layer_iti.getFeatures():
        geom = f.geometry()
        
        # Récupérer tous les LineStrings (même si c'est multipart)
        lines = geom.asMultiPolyline() if geom.isMultipart() else [geom.asPolyline()]
        
        k_rang=0
        
        for line in lines:
            # Créer un segment pour chaque paire de points consécutifs
            for i in range(len(line)-1):
                if line[i].distance(line[i+1])<tolerance :
                    continue
                segment = QgsGeometry.fromPolylineXY([line[i], line[i+1]])
                new_feat = QgsFeature()
                new_feat.setGeometry(segment)
                new_feat.setAttributes(f.attributes())
                pr1.addFeature(new_feat)
                layer_iti_eclate.changeAttributeValue(new_feat.id(), layer_iti_eclate.fields().indexOf("rang"), k_rang)
                k_rang+=1

    layer_iti_eclate.commitChanges()
    layer_iti_eclate.updateExtents()
    #QgsProject.instance().addMapLayer(layer_iti_eclate)

    if progression: progression(60, "Détection des noeuds du graphe...")
    layer_noeuds_graph = detect_noeud_iti(layer_iti_eclate,'id', 'noeuds_graph')

    prN = layer_noeuds_graph.dataProvider()
    prN.addAttributes([QgsField("id", QVariant.Int)])
    layer_noeuds_graph.updateFields()
    layer_noeuds_graph.startEditing()
    k_id_N = 0
    for feat in layer_noeuds_graph.getFeatures():
        layer_noeuds_graph.changeAttributeValue(feat.id(), layer_noeuds_graph.fields().indexOf("id"), k_id_N)
        k_id_N+=1
    layer_noeuds_graph.commitChanges()

    # QgsProject.instance().addMapLayer(layer_noeuds_graph)

    # fusion des segments de même id_iti noeuds en noeuds pour obtenir les strokes
    if progression: progression(75, "Fusion des segments d'itinéraire de même id noeuds en noeuds pour obtenir les strokes...")
    # --- Créer un index spatial pour les nœuds ---

    index_nodes = QgsSpatialIndex(layer_noeuds_graph.getFeatures())

    # --- Créer la couche de résultat ---

    crs = layer_iti_eclate.crs().authid()
    layer_strokes_iti = QgsVectorLayer(f"LineString?crs={crs}", "strokes_iti", "memory")
    pr = layer_strokes_iti.dataProvider()
    pr.addAttributes(layer_iti_eclate.fields())
    pr.addAttributes([QgsField("id_stroke", QVariant.Int)])
    layer_strokes_iti.updateFields()

    # création d'un dictionnaire des segments par itinéraire
    groups = defaultdict(list)
    for f in layer_iti_eclate.getFeatures():
        groups[f["id"]].append(f)

    # --- Fusion par id et respect du sens ---
        
    layer_strokes_iti.startEditing() 

    k_id = 1

    for id_val, feats in groups.items():
        unused = set(f.id() for f in feats) # on récupère les id de chaque tronçon dans un set
        feat_dict = {f.id(): f for f in feats} # création dictionnaire des features segment avec en clé sont id
        k_rang = 0

        while unused: # tant qu'il y a des tronçons dispos
            current_id = unused.pop()
            current_feat = feat_dict[current_id]
            merged_line = current_feat.geometry().asPolyline().copy()

            growing = True
            while growing:
                growing = False
                end_point = merged_line[-1]

                # stop si on arrive sur un nœud  
                for other_id in list(unused):
                    other_feat = feat_dict[other_id]
                    other_geom = other_feat.geometry().asPolyline()
                    
                    # stop si on arrive sur un nœud
                    if is_near_node(QgsPointXY(end_point), index_nodes, layer_noeuds_graph, tolerance):
                        growing = False
                        break
                    # Respect strict du sens : on ne reverse jamais
                    if other_geom[0] == end_point :
                        merged_line.extend(other_geom[1:])
                        unused.remove(other_id)
                        growing = True
                        break

            # Ajouter le segment fusionné
            new_feat = QgsFeature()
            new_feat.setGeometry(QgsGeometry.fromPolylineXY(merged_line))
            new_feat.setAttributes(current_feat.attributes())
            pr.addFeature(new_feat)
            
            # Complétion champ rang et et id_stroke
            layer_strokes_iti.changeAttributeValue(new_feat.id(), layer_strokes_iti.fields().indexOf("rang"), k_rang)
            layer_strokes_iti.changeAttributeValue(new_feat.id(), layer_strokes_iti.fields().indexOf("id_stroke"), k_id)
            k_rang+=1
            k_id+=1

    # On renomme le champ 'id' en champ 'id_iti'
    idx = layer_strokes_iti.fields().indexOf("id")
    layer_strokes_iti.renameAttribute(idx, "id_iti")
    layer_strokes_iti.commitChanges()

    # --- Ajouter la couche au projet ---
    QgsProject.instance().addMapLayer(layer_strokes_iti)

    # --------------------
    # Style strokes routes
    # --------------------
    if progression: progression(90, "Calcul des décalages et attribution du style...")

    symbol_strokesroute = QgsLineSymbol.createSimple({})
    line_layer = QgsSimpleLineSymbolLayer()
    line_layer.setColor(QColor("black"))
    line_layer.setWidth(largeur)
    line_layer.setWidthUnit(QgsUnitTypes.RenderMetersInMapUnits)
    symbol_strokesroute.changeSymbolLayer(0, line_layer)
    layer_strokesroute.renderer().setSymbol(symbol_strokesroute)
    layer_strokesroute.triggerRepaint()

    # -----------------------------------
    # Attribution offset strokes iti
    # -----------------------------------

    # Ajout champ offset
    layer_strokes_iti.startEditing()
    layer_strokes_iti.dataProvider().addAttributes([QgsField("Offset", QVariant.Int)])
    layer_strokes_iti.updateFields()

    # complétion du champ de manière aléatoire
    index = QgsSpatialIndex(layer_strokes_iti.getFeatures())
    idx = layer_strokes_iti.fields().indexOf("Offset")

    # initialiser toutes les valeurs de offset à 0 pour éviter les bugs quand on cherche le max plus tard
    for feature in layer_strokes_iti.getFeatures():
            feature[idx] = 0
            layer_strokes_iti.updateFeature(feature)

    # Création d'un dictionnaire pour chaque strokes iti des offset+sens des strokes superposés 
    for feature in layer_strokes_iti.getFeatures():
        Dict_sens_offset = {'identique':[],'inverse':[]}
        geom=feature.geometry()
        candidats=index.intersects(geom.boundingBox())
        
        for fid in candidats : 
            autre = layer_strokes_iti.getFeature(fid)
            
            if autre.id() != feature.id() :
                if autre.geometry().isGeosEqual(geom):
                    if feature.geometry().asPolyline()==autre.geometry().asPolyline() :
                        Dict_sens_offset['identique'].append(autre["Offset"])
                    else : 
                        Dict_sens_offset['inverse'].append(autre["Offset"])
                
        maxs = [max(Dict_sens_offset['identique'],key=abs,default=0),max(Dict_sens_offset['inverse'],key=abs,default=0)]
        
        if abs(maxs[0])==abs(maxs[1]) or -max(maxs,key=abs) in Dict_sens_offset['identique'] or -max(maxs,key=abs) in Dict_sens_offset['inverse']:
            feature[idx]=abs(max(maxs,key=abs))+1
        else :
            if max(maxs,key=abs)==maxs[0]:
                feature[idx]=-maxs[0]
            else : 
                feature[idx]=maxs[1]
        
        layer_strokes_iti.updateFeature(feature)
        
    layer_strokes_iti.commitChanges()

    # --------------------
    # apparence strokes iti
    # --------------------

    expr = '"id_iti"' # On catégorise sur l'id de l'itinéraire

    # Attribtion d'une couleur par itinéraire 

    colors = generate_distinct_colors(layer_iti.featureCount())
    unique_id = list(set(f['id_iti'] for f in layer_strokes_iti.getFeatures()))
    id_color_dict = {uid: colors[i % len(colors)] for i, uid in enumerate(unique_id)}

    categories = []

    for uid in unique_id:
        symbol = QgsLineSymbol.createSimple({'color': id_color_dict[uid]})
        symbol_layer = symbol.symbolLayer(0)
        
        symbol_layer.setWidth(largeur)
        symbol_layer.setWidthUnit(QgsUnitTypes.RenderMetersInMapUnits)
        symbol_layer.setOffsetUnit(QgsUnitTypes.RenderMetersInMapUnits)
        
        # ASTUCE : On lit le décalage directement depuis la table attributaire en temps réel
        symbol_layer.setDataDefinedProperty(
            QgsSimpleLineSymbolLayer.PropertyOffset,
            QgsProperty.fromExpression(f'"Offset" * {largeur}')
        )
        
        # La catégorie ne dépend plus que de l'ID
        category = QgsRendererCategory(uid, symbol, str(uid))
        categories.append(category)
        
    renderer = QgsCategorizedSymbolRenderer(expr, categories)
    layer_strokes_iti.setRenderer(renderer)
    layer_strokes_iti.triggerRepaint()


    return {
        "layer_iti": layer_iti,
        "layer_res": layer_res,
        "layer_strokesroute": layer_strokesroute,
        "layer_strokes_iti": layer_strokes_iti,
    }
