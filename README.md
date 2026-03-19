# Plugin QGIS Itinéraires Décalés
Projet d'Analyse Spatiale des ingénieurs en 3ème année de Géodata Paris et M2 de l'UGE en IGAST. Implémentation d’un plugin QGIS permettant de représenter des itinéraires multiples « à la manière de plans de bus ».

## Installer le plugin sur QGIS 
Le dossier contenant le plugin est le dossier itineraire_decales. 
Afin de faire fonctionner le plugin, il est nécessaire d'exporter le repository en zip, d'extraire le dossier itineraires_decales et de le compresser en ZIP. 

Ce dossier .ZIP peut ensuite êre ajouté dans QGIS. Pour cela, il faut le charger depuis "Extensions / Installer/gérer les extensions / installer depuis un ZIP".
Une fois le plugin chargé, installer l'extension Plugin Reloader et sélectionner le plugin itineraires_decales dans les paramètres de l'extension.
Une nouvelle icône apparaît, qui permet de lancer le plugin.

## Algorithmes de gestion des croisements
Les algorithmes de gestion des croisements n'ont pas été encore intégrés au plugin. Ils sont disponibles dans le dossier _croisements_.
Afin de fonctionner correctement, les codes doivent être compilés depuis la console python de QGIS directement.

Le premier fichier, _croisement.py_ contient le code permettant de créer les nouvelles extrémités décalées des strokes d'itinéraires à proximité des intersections (layer _points_offset_).
Pour que l'algorithme n'échoue pas, il est nécessaire d'avoir dans le gestionnaire de couche les couches suivantes :
- _strokes_iti_ : la couche des strokes d'itinéraires issue de l'algorithme implémenté dans le plugin _itineraires_decales_
- _noeuds_graph_ : layer contenant les croisements. Pour obtenir cette couche, il est indipensable de décommenter la ligne **QgsProject.instance().addMapLayer(layer_noeuds_graph)** du fichier _itineraires_decales/core/traitement.py_

Le fichier _relier.py_ contient le code permettant, à partir des points décalés (couche _points_offset_), de calculer les points à relier entre eux en créant une nouvelle couche vectorielle (_raccords_) contenant les droites reliant ces points.

## Configuration des données utilisateur
Pour le bon fonctionnement du plugin, il faut fournir les données suivantes : 
1. **Couche réseau de route :**
   Un fichier shapefile du réseau contenant des géométries de type linéaire, sur lequel s’appuient les itinéraires. Les entités du fichier doivent à minima s’arrêter au niveau des croisements. Par exemple, un réseau issu de la BDTOPO convient parfaitement.
2. **Couche itinéraires :**
   Un fichier shapefile des itinéraires contenant des géométries de type linéaire. Chaque itinéraire doit avoir au moins un identifiant de type string compris dans un champ nommé "id". Chaque itinéraire doit être composé d’une seule entité de
type polyligne, orientée de son point de départ à son point d’arrivée. Les itinéraires doivent s’appuyer exactement sur la géométrie du réseau, cela veut dire que deux itinéraires passant par une même section de chemin doivent partager les mêmes points de passages que ceux de la géométrie du chemin emprunté.

Ces deux fichiers doivent dépendre du même système de projection.
