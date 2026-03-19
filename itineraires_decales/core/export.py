"""
/***************************************************************************
Gestion des fonctions liées à l'onglet Export du Plugin
***************************************************************************/
"""

import os
from qgis.core import (
    QgsVectorFileWriter,
    QgsCoordinateTransformContext,
    QgsProject,
    QgsMapSettings,
    QgsMapRendererCustomPainterJob
)
from qgis.PyQt.QtGui import QImage, QPainter
from qgis.PyQt.QtCore import QSize, Qt


def exporter_couches(couches, dossier, fmt, canvas=None, log_widget=None):
    """
    Gère l'export des données (SHP, GPKG) ou de l'image (PNG, PDF).
    """
    os.makedirs(dossier, exist_ok=True)

    # ---- Image : PDF ou PNG ----
    if fmt in ["PNG", "PDF"]:
        if canvas is None:
            if log_widget: log_widget.append("ERR : Le canvas est requis pour l'export image.")
            return False
        return _exporter_carte(dossier, fmt, canvas, log_widget)

    # ---- Données : SHP ou GPKG ----
    driver_map = {
        "ESRI Shapefile": { "ext": ".shp", "driver": "ESRI Shapefile" },
        "GeoPackage": { "ext": ".gpkg", "driver": "GPKG" }
    }

    ext = driver_map[fmt]["ext"]
    driver = driver_map[fmt]["driver"]
    context = QgsProject.instance().transformContext()

    for nom, layer in couches:
        if layer is None or not layer.isValid():
            continue

        chemin = os.path.join(dossier, f"{nom}{ext}")
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = driver
        options.fileEncoding = "UTF-8"

        res = QgsVectorFileWriter.writeAsVectorFormatV3(layer, chemin, context, options)
        
        if res[0] == QgsVectorFileWriter.NoError:
            if log_widget: log_widget.append(f"OK Données exportées : {nom}{ext}")
        else:
            if log_widget: log_widget.append(f"ERR Export {nom} : {res[1]}")


def _exporter_carte(dossier, fmt, canvas, log_widget):
    nom_fichier = "carte_itineraires" + (".png" if fmt == "PNG" else ".pdf") # à rendre plus dynamique mais plus tard...
    chemin = os.path.join(dossier, nom_fichier)

    # Configuration du rendu (on prend ce qui est visible sur le canvas)
    settings = canvas.mapSettings()
    settings.setBackgroundColor(Qt.white) # Fond blanc pour l'export
    
    if fmt == "PNG":
        image = QImage(settings.outputSize(), QImage.Format_ARGB32_Premultiplied)
        image.setDotsPerMeterX(96 / 0.0254) # 96 DPI
        image.setDotsPerMeterY(96 / 0.0254)
        
        painter = QPainter(image)
        job = QgsMapRendererCustomPainterJob(settings, painter)
        job.start()
        job.waitForFinished()
        painter.end()
        
        success = image.save(chemin, "PNG")
    
    elif fmt == "PDF":
        from qgis.PyQt.QtPrintSupport import QPrinter
        printer = QPrinter(QPrinter.HighResolution)
        printer.setOutputFormat(QPrinter.PdfFormat)
        printer.setOutputFileName(chemin)
        printer.setPageSize(QPrinter.A4)
        
        painter = QPainter(printer)
        # On ajuste la vue au format de la page
        settings.setOutputSize(QSize(painter.viewport().width(), painter.viewport().height()))
        job = QgsMapRendererCustomPainterJob(settings, painter)
        job.start()
        job.waitForFinished()
        painter.end()
        success = True

    if success and log_widget:
        log_widget.append(f"OK Carte exportée : {nom_fichier}")
    return success