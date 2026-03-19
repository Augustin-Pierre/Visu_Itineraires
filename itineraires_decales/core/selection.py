"""
/***************************************************************************
Gestion des clicks sur la carte : sélection d'itinéraire et échanges 
***************************************************************************/
"""

from qgis.gui import QgsMapTool
from qgis.core import QgsGeometry, QgsSpatialIndex, QgsProject, QgsPointXY
from qgis.PyQt.QtCore import Qt
from qgis.utils import iface 
import math

class SelectItineraire(QgsMapTool):

    def __init__(self, canvas, layer, largeur=6, mode="selection"):
        super().__init__(canvas)
        self.canvas = canvas
        self.layer = layer
        self.index = QgsSpatialIndex(layer.getFeatures()) 
        self.largeur = largeur
        self.tolerance = largeur/2 # tolérance de sélection 
        self.mode = mode

        self.first_feature = None
        self.first_vector = None
    

    def canvasPressEvent(self, event):
        """
        INTERCEPTION DES CLICS (GAUCHE)
        """
        if event.button() != Qt.LeftButton: 
            return

        if self.mode == "selection":
            self.selection_simple(event)
        elif self.mode == "echange":
            self.echange_strokes(event)
        
    def selection_simple(self, event):
        """
        Pour sélectionner uniquement.
        """
        # Récupération de la position du curseur
        click_point = self.toMapCoordinates(event.pos()) #convertit les coordonnées en pixels du clic (sur l'écran) en coordonnées géographiques sur la carte
        point_geom = QgsGeometry.fromPointXY(click_point) # Crée une géométrie ponctuelle à partir des coordonnées (pour calcul de distances)
        
        ids = self.index.nearestNeighbor(click_point, 10) # les 10 objets les plus proches du clic (en supposant qu'il n'y a pas plus d'itinéraires)

        # Pour chacun des 10 itinéraires candidats, le script va calculer un "score". 
        # Le but est de trouver le score le plus proche de 0.
        best_feat = None # initialisation de l'itinéraire le plus proche
        best_score = float("inf") # initialisation du score de proximité de l'itinéraire
        best_vector = None # itinialisation du vecteur correspondant au segment

        for feat in self.layer.getFeatures(ids): # on parcourt les itinéraires sélectionnés 
            print(feat["titre"])
            geom = feat.geometry()
            dist = geom.distance(point_geom) # distance au point du click souris
            
            res = geom.closestSegmentWithContext(click_point) 
            cote = res[3] #le 4ème élément du résultat, à l'index 3
        
            offset_int = feat["Offset"]  # champ attribut, décalage
            offset_map = offset_int * self.largeur # estime la distance à laquelle le ruban devrait se trouver par rapport au centre de la route.

            # Si le clic est à gauche mais que l'itinéraire est configuré pour être affiché à droite (ou inversement), le script l'ignore (continue) et passe au suivant.
            # ignorer mauvais côté
            if offset_int < 0 and cote > 0:
                continue
            if offset_int > 0 and cote < 0:
                continue

            # Différence entre la distance réelle du clic et la distance théorique du ruban. Plus le score est proche de 0, plus le clic est précis sur le ruban.
            score = abs(dist - abs(offset_map))
            # print(score)

            if score < self.tolerance and score < best_score:
                best_score = score
                best_feat = feat

        if best_feat:
            # On colore le stroke cliqué en jaune
            self.layer.selectByIds([best_feat.id()])
            iface.mainWindow().statusBar().showMessage("Stroke sélectionné.")
        else:
            # Clic dans le vide
            self.layer.removeSelection()
            iface.mainWindow().statusBar().showMessage("Sélection annulée.")


    def echange_strokes(self, event):
        """
        Permet l'échange de deux strokes.
        """
        iface.mainWindow().statusBar().showMessage("Commencer l'échange.")
        self.layer.removeSelection()

        if event.button() != Qt.LeftButton: 
            return
        
        # Récupération de la position du curseur
        click_point = self.toMapCoordinates(event.pos()) #convertit les coordonnées en pixels du clic (sur l'écran) en coordonnées géographiques sur la carte
        point_geom = QgsGeometry.fromPointXY(click_point) # Crée une géométrie ponctuelle à partir des coordonnées (pour calcul de distances)
        
        ids = self.index.nearestNeighbor(click_point, 10) # les 10 objets les plus proches du clic (en supposant qu'il n'y a pas plus d'itinéraires)

        # Pour chacun des 10 itinéraires candidats, le script va calculer un "score". 
        # Le but est de trouver le score le plus proche de 0.
        best_feat = None # initialisation de l'itinéraire le plus proche
        best_score = float("inf") # initialisation du score de proximité de l'itinéraire
        best_vector = None # itinialisation du vecteur correspondant au segment

        for feat in self.layer.getFeatures(ids): # on parcourt les itinéraires sélectionnés 
            print(feat["titre"])
            geom = feat.geometry()
            dist = geom.distance(point_geom) # distance au point du click souris
            # print(dist)

            # CÔTE 
            res = geom.closestSegmentWithContext(click_point) # Returns if the point is located 
                                                                # on the left or right side of the geometry 
                                                                #( < 0 means left, > 0 means right, 0 indicates that the test was unsuccessful, 
                                                                #e.g. for a point exactly on the line)
            cote = res[3] #le 4ème élément du résultat, à l'index 3
            next_vertex_index = res[2] # Index du sommet situé juste APRES le point de clic

            offset_int = feat["Offset"]  # champ attribut, décalage
            # print(offset_int)
            # offset_inf = cote * ((self.largeur/2) + ((offset_int)* self.largeur))
            # offset_sup = cote * ((self.largeur/2) + ((offset_int + 1)* self.largeur))
            offset_map = offset_int * self.largeur # estime la distance à laquelle le ruban devrait se trouver par rapport au centre de la route.
            # print(offset_map)
            # offset_map = self.mm_to_map_units(abs(offset_mm))

            # Si le clic est à gauche mais que l'itinéraire est configuré pour être affiché à droite (ou inversement), le script l'ignore (continue) et passe au suivant.
            # ignorer mauvais côté
            if offset_int < 0 and cote > 0:
                continue
            if offset_int > 0 and cote < 0:
                continue

            # Différence entre la distance réelle du clic et la distance théorique du ruban. Plus le score est proche de 0, plus le clic est précis sur le ruban.
            score = abs(dist - abs(offset_map))
            # print(score)

            if score < self.tolerance and score < best_score:
                best_score = score
                best_feat = feat

                # Calcul du vecteur directionnel du segment 
                pt2 = geom.vertexAt(next_vertex_index)  # On récupère les coordonnées des deux points qui forment le segment cliqué
                pt1 = geom.vertexAt(next_vertex_index - 1)
                best_vector = (pt2.x() - pt1.x(), pt2.y() - pt1.y()) # (x2-x1, y2-y1)

            # --- ECHANGE ---
        
            if not best_feat:
                # Clic dans le vide
                self.layer.removeSelection()
                self.first_feature = None
                self.first_vector = None
                iface.mainWindow().statusBar().showMessage("Sélection annulée. Cliquez sur un stroke.", 5000)
                return

            if self.first_feature is None:
                # Sélection du premier stroke
                self.first_feature = best_feat
                self.first_vector = best_vector # On sauvegarde le vecteur du premier clic
                self.layer.selectByIds([best_feat.id()])
                iface.mainWindow().statusBar().showMessage("Stroke 1 sélectionné. Cliquez sur le stroke 2 pour échanger (ou dans le vide pour annuler).")
                
            else:
                # Clic sur le second stroke
                if self.first_feature.id() == best_feat.id():
                    # Clic sur le même stroke = on annule la sélection 
                    self.layer.removeSelection()
                    self.first_feature = None
                    self.first_vector = None
                    iface.mainWindow().statusBar().showMessage("Sélection annulée. Cliquez sur un stroke.", 5000)
                else:
                    # Clic sur un stroke différent = on peut procéder à l'échange 
                    idx = self.layer.fields().indexOf("Offset")
                    
                    offset1 = self.first_feature["Offset"]
                    offset2 = best_feat["Offset"]

                    # Détermination des signes (+1 ou -1) de l'offset
                    signe1 = 1 if offset1 >= 0 else -1
                    signe2 = 1 if offset2 >= 0 else -1
                    meme_signe_offset = (signe1 == signe2)
                    
                    # On récupère les deux vecteurs
                    x1, y1 = self.first_vector
                    x2, y2 = best_vector
                    
                    # Calcul du produit scalaire mathématique
                    produit_scalaire = (x1 * x2) + (y1 * y2)
                    
                    # REGLES DE DECISION DES ECHANGES 
                    if produit_scalaire > 0:
                        # LES DEUX STROKES VONT DANS LE MÊME SENS : On échange simplement les valeurs.
                        nouveau_offset1 = offset2
                        nouveau_offset2 = offset1
                    else:
                        # LES DEUX STROKES VONT EN SENS INVERSE : deux cas
                        if not meme_signe_offset:
                            # SIGNE D'OFFSET DIFFERENTS : on échange les valeurs absolues, on garde le signe
                            nouveau_offset1 = signe1 * abs(offset2)
                            nouveau_offset2 = signe2 * abs(offset1)
                        else:
                            # MÊME SIGNE D'OFFSET : on inverse les signes (multiplication par -1)
                            nouveau_offset1 = -offset2
                            nouveau_offset2 = -offset1
                    
                    # APPLICATIONS DES MODIFICATIONS DANS LA TABLE ATTRIBUTAIRE 
                    self.layer.startEditing()
                    self.layer.changeAttributeValue(self.first_feature.id(), idx, nouveau_offset1)
                    self.layer.changeAttributeValue(best_feat.id(), idx, nouveau_offset2)
                    self.layer.commitChanges() 
                    
                    self.layer.removeSelection()   
                    self.layer.triggerRepaint()             
                    
                    self.first_feature = None
                    self.first_vector = None
                    iface.mainWindow().statusBar().showMessage("Échange réussi ! Vous pouvez cliquer sur un nouveau stroke.", 5000)
