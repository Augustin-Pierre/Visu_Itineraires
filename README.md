# Visu_Itineraires
Projet d'Analyse spatiale pour l'implémentation d’un plugin QGIS permettant de représenter des itinéraires « à la manière de plans de bus »

## Installer le plugin sur QGIS 
Le dossier contenant le plugin est le dossier itineraire_decales. 
Afin de faire fonctionner le plugin, il est nécessaire d'exporter le repository en zip, d'extraire le dossier itineraires_decales et de le compresser en zip. 

Ce dossier .zip peut ensuite êre ajouté dans QGIS. Pour cela, il faut le charger depuis "Extensions / Installer/gérer les extensions / installer depuis un zip".
Une fois le plugin chargé, installer l'extension Plugin Reloader et sélectionner le plugin itineraires_decales dans les paramètres de l'extension.
Une nouvelle icône apparaît, qui permet de lancer le plugin.

## Algorithmes de gestion des croisements
Les algorithmes de gestion des croisements n'ont pas été encore intégrés au plugin. Ils sont disponibles dans le dossier _croisements_.
Afin de fonctionner correctement, les codes doivent être compilés depuis la console python de QGIS directement.

Le premier fichier, _croisement.py_ contient le code permettant de créer les nouvelles extrémités décalées des strokes d'itinéraires à proximité des intersections.
Pour que l'algorithme n'échoue pas, il est nécessaire d'avoir dans le gestionnaire de couche les couches suivantes :
- _strokes_iti_ : la couche des strokes d'itinéraires issue de l'algorithme implémenté dans le plugin _itineraires_decales_
- _noeuds_graph_ : layer contenant les croisements. Pour obtenir cette couche, il est indipensable de décommenter la ligne du fichier 
