import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import Point, mapping
from pyproj import Transformer
from pathlib import Path
import csv

# 🔹 GLOBAL BUFFER RADIUS (meters)
#BUFFER_RADIUS = 5_000.0
RADII_KM = [5, 10, 20, 30, 40]
COUNTRY = "it"

def pop_within_buffer(
    tif_paths,   
    lat: float,
    lon: float,
    buffer_m: float,
) -> float:
    total_pop = 0.0
    any_overlap = False

    for tif_path in tif_paths:
        with rasterio.open(tif_path) as src:
            raster_crs = src.crs
            if raster_crs is None:
                raise ValueError(f"Raster has no CRS defined: {tif_path}")

            transformer = Transformer.from_crs("EPSG:4326", raster_crs, always_xy=True)
            x, y = transformer.transform(lon, lat)
            geom = Point(x, y).buffer(buffer_m)

            # quick bbox skip
            minx, miny, maxx, maxy = geom.bounds
            left, bottom, right, top = src.bounds
            if (maxx < left) or (minx > right) or (maxy < bottom) or (miny > top):
                continue

            try:
                out_img, _ = mask(
                    src,
                    [mapping(geom)],
                    crop=True,
                    all_touched=True,
                    filled=True
                )
            except ValueError:
                # "Input shapes do not overlap raster."
                continue

            any_overlap = True
            data = out_img[0]

            nodata = src.nodata if src.nodata is not None else -200.0
            valid = (data != nodata) & np.isfinite(data) & (data >= 0)
            total_pop += float(data[valid].sum())

    if not any_overlap:
        raise ValueError("Buffer does not overlap any provided raster tiles.")

    return total_pop


if __name__ == "__main__":
    # ✅ put ALL 4 England tiles here
    #tifs = [
    #    r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\fu\population_rasters\GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R3_C18.tif",
    #    r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\fu\population_rasters\GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R3_C19.tif",
    #    r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\fu\population_rasters\GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R4_C18.tif",
    #    r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\fu\population_rasters\GHS_POP_E2025_GLOBE_R2023A_54009_100_V1_0_R4_C19.tif",]

    raster_folder = Path(
        r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\fu\population_rasters"
    )

    # Grab all .tif files in the folder
    tifs = list(raster_folder.glob("*.tif"))

    if not tifs:
        raise ValueError("No .tif files found in the folder.")

    print(f"Found {len(tifs)} raster tiles.")

    stadiums = {
        # --- Serie A (2025–26) ---
        "Atalanta - New Balance Arena": None,
        "Bologna - Stadio Renato Dall'Ara": None,
        "Cagliari - Unipol Domus": None,
        "Como - Stadio Giuseppe Sinigaglia": None,
        "Cremonese - Stadio Giovanni Zini": None,
        "Fiorentina - Stadio Artemio Franchi": None,
        "Genoa - Stadio Luigi Ferraris": None,
        "Inter - San Siro (Stadio Giuseppe Meazza)": None,
        "Juventus - Allianz Stadium": None,
        "Lazio - Stadio Olimpico": None,
        "Lecce - Stadio Via del Mare": None,
        "Milan - San Siro (Stadio Giuseppe Meazza)": None,
        "Napoli - Stadio Diego Armando Maradona": None,
        "Parma - Stadio Ennio Tardini": None,
        "Pisa - Arena Garibaldi - Stadio Romeo Anconetani": None,
        "Roma - Stadio Olimpico": None,
        "Sassuolo - MAPEI Stadium - Città del Tricolore": None,
        "Torino - Stadio Olimpico Grande Torino": None,
        "Udinese - Stadio Friuli (Bluenergy Stadium)": None,
        "Hellas Verona - Stadio Marcantonio Bentegodi": None,

        # --- Serie B “big / prominent” picks (2025–26) ---
        "Palermo - Stadio Renzo Barbera": None,
        "Sampdoria - Stadio Luigi Ferraris": None,
        "Bari - Stadio San Nicola": None,
        "Venezia - Stadio Pier Luigi Penzo": None,
        "Empoli - Stadio Carlo Castellani": None,
        "Monza - U-Power Stadium": None,
        "Spezia - Stadio Alberto Picco": None,
        "Cesena - Orogel Stadium - Dino Manuzzi": None,
        "Modena - Stadio Alberto Braglia": None,
        "Frosinone - Stadio Benito Stirpe": None,
    }

    for radius_km in RADII_KM:
        buffer_m = radius_km * 1000.0

        results = []
        for name, (lat, lon) in stadiums.items():
            try:
                total = pop_within_buffer(tifs, lat, lon, buffer_m=buffer_m)
                results.append((name, total))
            except Exception as e:
                results.append((name, None))
                print(f"[WARN] {name} ({radius_km}km): {e}")

        # sort: errors bottom, otherwise pop desc
        results.sort(key=lambda x: (x[1] is None, -(x[1] or 0)))

        print(f"\nEstimated population within {radius_km} km buffer (across {len(tifs)} tiles)")
        print("-" * 90)
        for name, total in results:
            if total is None:
                print(f"{name:45s}  ERROR")
            else:
                print(f"{name:45s}  {total:12,.0f}")

        output_folder = Path(
            r"V:\srm\wml\Workarea\ofedyshy\Personal\Data Analysis\fu\population_outputs"
        )
        output_folder.mkdir(parents=True, exist_ok=True)

        csv_path = output_folder / f"fu_pop_{COUNTRY}_{radius_km}km_2025.csv"

        with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Club", "Population"])
            for name, total in results:
                writer.writerow([name, total if total is not None else "ERROR"])

        print(f"CSV saved to: {csv_path}")

    """
    stadiums = {
        "Man United — Old Trafford": (53.4631, -2.2913),
        "Liverpool — Anfield": (53.4308, -2.9608),
        "Everton — Goodison Park": (53.4388, -2.9664),
        "Man City — Etihad Stadium": (53.4831, -2.2004),
        "Leeds United — Elland Road": (53.7778, -1.5721),
        "Newcastle United — St James’ Park": (54.9756, -1.6216),
        "Sunderland — Stadium of Light": (54.9144, -1.3884),
        "Aston Villa — Villa Park": (52.5092, -1.8849),
        "Wolves — Molineux Stadium": (52.5903, -2.1307),
        "Chelsea — Stamford Bridge": (51.4816, -0.1910),
        "Arsenal — Emirates Stadium": (51.5549, -0.1084),
        "Tottenham — Tottenham Hotspur Stadium": (51.6043, -0.0665),
        "West Ham — London Stadium": (51.5386, 0.0165),
        "Brighton — Amex Stadium": (50.8618, -0.0835),
        "Bournemouth — Vitality Stadium": (50.7352, -1.8383),
        "Brentford — Gtech Community Stadium": (51.4907, -0.2887),
        "Burnley — Turf Moor": (53.7890, -2.2300),
        "Crystal Palace — Selhurst Park": (51.3983, -0.0856),
        "Fulham — Craven Cottage": (51.4749, -0.2217),
        "Nottingham Forest — City Ground": (52.9399, -1.1325),
    }

    stadiums = {
        "Lech Poznan - Stadion Poznań": (52.4068, 16.9290),           # Lech Poznań, Poznań
        "Legia Warszawa - Stadion Wojska Polskiego": (52.2280, 21.0365),  # Legia Warsaw, Warsaw
        "Rakow Częstochowa - Stadion Miejski Rakow": (50.8118, 19.1120),  # Raków Częstochowa, Częstochowa
        "Gornik Zabrze - Arena Zabrze": (50.3220, 18.7890),         # Górnik Zabrze, Zabrze
        "Jagiellonia Bialystok - Chorten Arena": (53.1290, 23.1680), # Jagiellonia Białystok, Białystok
        "Pogon Szczecin - Stadion Florian Krygier": (53.4299, 14.5796), # Pogoń Szczecin, Szczecin
        "Widzew Lodz - Stadion Widzewa": (51.7700, 19.5088),        # Widzew Łódź, Łódź
        "Zaglebie Lubin - KGHM Zaglebia Arena": (51.4000, 16.2010), # Zagłębie Lubin, Lubin
        "Korona Kielce - Exbud Arena": (50.8660, 20.6280),          # Korona Kielce, Kielce
        "Motor Lublin - Arena Lublin": (51.2400, 22.5680),          # Motor Lublin, Lublin
        "Arka Gdynia - Stadion Miejski Gdynia": (54.5189, 18.5305), # Arka Gdynia, Gdynia
        "Cracovia - Stadion Cracovii": (50.0614, 19.9405),          # Cracovia, Kraków
        "GKS Katowice - Stadion Miejski Katowice": (50.2599, 19.0088), # GKS Katowice, Katowice
        "Wisla Plock - Orlen Stadion": (52.5620, 19.6850),          # Wisła Płock, Płock :contentReference[oaicite:1]{index=1}
        "Piast Gliwice - Stadion Miejski Gliwice": (50.2946, 18.6714), # Piast Gliwice, Gliwice
        "Radomiak Radom - Stadion Radomiaka": (51.3890, 21.1590),   # Radomiak Radom, Radom
        "Tarnow - Stadion Bruk-Bet": (50.1730, 20.2740),         # Bruk-Bet Termalica Nieciecza, Nieciecza
        "Pogon Szczecin - Stadion Florian Krygier": (53.4299, 14.5796), # (*duplicate listing removed if needed*)
        "Lechia Gdansk - Polsat Plus Arena Gdansk": (54.3900, 18.6403),
        "Slask Wroclaw - Tarczynski Arena Wroclaw": (51.1392, 16.9398),
        "Resovia Rzeszow - Stadion Miejski w Rzeszowie": (50.0400, 22.0080)
    }

    {
        "Bayern Munich - Allianz Arena": (48.2188, 11.6247),
        "Borussia Dortmund - Signal Iduna Park": (51.4926, 7.4519),
        "RB Leipzig - Red Bull Arena Leipzig": (51.3458, 12.3483),
        "Bayer Leverkusen - BayArena": (51.0382, 7.0023),
        "Eintracht Frankfurt - Deutsche Bank Park": (50.0686, 8.6455),
        "Borussia Monchengladbach - Borussia-Park": (51.1746, 6.3852),
        "VfB Stuttgart - MHPArena Stuttgart": (48.7923, 9.2320),
        "TSG Hoffenheim - PreZero Arena": (49.2392, 8.8867),
        "SC Freiburg - Europa-Park Stadion": (48.0213, 7.8298),
        "FC Augsburg - WWK Arena": (48.3233, 10.8853),
        "VfL Wolfsburg - Volkswagen Arena": (52.4326, 10.8034),
        "Werder Bremen - Wohninvest Weserstadion": (53.0665, 8.8371),
        "Union Berlin - Stadion An der Alten Forsterei": (52.4572, 13.5680),
        "Hertha Berlin - Olympiastadion Berlin": (52.5147, 13.2395),
        "FSV Mainz 05 - MEWA Arena": (49.9840, 8.2247),
        "1. FC Koln - RheinEnergieStadion": (50.9339, 6.8750),
        "Hamburger SV - Volksparkstadion": (53.5872, 9.8986),
        "Heidenheim - Voith-Arena": (48.6795, 10.1544),
        "Schalke 04 - Veltins-Arena": (51.5547, 7.0671),
        "St Pauli - Millerntor-Stadion": (53.5497, 9.9675),
        "Fortuna Dusseldorf - Merkur Spiel-Arena": (51.2610, 6.7338),
        "VfL Bochum - Vonovia Ruhrstadion": (51.4817, 7.2197),
        "Nurnberg - Max-Morlock-Stadion": (49.4268, 11.1257),
        "Hannover 96 - Heinz von Heiden Arena": (52.3600, 9.7319),
        "Karlsruhe - BBBank Wildpark": (49.0194, 8.4122),
        "Dynamo Dresden - Rudolf-Harbig-Stadion": (51.0406, 13.7498),
    }
"""