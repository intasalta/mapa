import os
import math
import requests

# === CONFIGURACIÓN ===
# URL del servicio WMS que quieres pre-cachear
WMS_URL = "https://wms.ign.gob.ar/geoserver/wms"
LAYERS = "capasbase:limite_politico_administrativo_linea"

# Bounding box de tu área de interés (min_lon, min_lat, max_lon, max_lat)
# Ejemplo: Área aproximada
BBOX = [-65.60, -25.00, -65.30, -24.70] 

ZOOM_MIN = 10
ZOOM_MAX = 13  # Mantener zoom moderado para no saturar almacenamiento de Git

TILES_DIR = "tiles"

def lon2tile(lon, zoom):
    return int((lon + 180.0) / 360.0 * (1 << zoom))

def lat2tile(lat, zoom):
    lat_rad = math.radians(lat)
    return int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * (1 << zoom))

def tile2bbox(x, y, z):
    """ Convierte coordenadas de tesela XYZ a BBOX EPSG:3857 (Web Mercator) """
    def tile2mercator(tx, ty, zoom):
        initial_resolution = 20037508.342789244 * 2 / 256.0
        origin_shift = 20037508.342789244
        res = initial_resolution / (2 ** zoom)
        mx = tx * 256 * res - origin_shift
        my = origin_shift - ty * 256 * res
        return mx, my

    minx, maxy = tile2mercator(x, y, z)
    maxx, miny = tile2mercator(x + 1, y + 1, z)
    return f"{minx},{miny},{maxx},{maxy}"

def fetch_and_save_tile(z, x, y):
    bbox_3857 = tile2bbox(x, y, z)
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.1.1",
        "REQUEST": "GetMap",
        "LAYERS": LAYERS,
        "STYLES": "",
        "SRS": "EPSG:3857",
        "BBOX": bbox_3857,
        "WIDTH": "256",
        "HEIGHT": "256",
        "FORMAT": "image/png",
        "TRANSPARENT": "TRUE"
    }
    
    out_dir = os.path.join(TILES_DIR, str(z), str(x))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, f"{y}.png")

    try:
        response = requests.get(WMS_URL, params=params, timeout=10)
        content_type = response.headers.get("Content-Type", "")
        
        # Validar si es realmente una imagen PNG
        if response.status_code == 200 and "image" in content_type:
            with open(out_path, "wb") as f:
                f.write(response.content)
            print(f"OK: {z}/{x}/{y}")
        else:
            print(f"Error en {z}/{x}/{y}: Content-Type recibido es '{content_type}'")
            # Muestra los primeros 300 caracteres de la respuesta XML de GeoServer
            print(f"Detalle servidor: {response.text[:300]}")
    except Exception as e:
        print(f"Fallo al descargar {z}/{x}/{y}: {e}")


def main():
    min_lon, min_lat, max_lon, max_lat = BBOX
    for z in range(ZOOM_MIN, ZOOM_MAX + 1):
        x_min = lon2tile(min_lon, z)
        x_max = lon2tile(max_lon, z)
        y_min = lat2tile(max_lat, z)  # Nota: Y invierte latitud
        y_max = lat2tile(min_lat, z)

        for x in range(x_min, x_max + 1):
            for y in range(y_min, y_max + 1):
                fetch_and_save_tile(z, x, y)

if __name__ == "__main__":
    main()
