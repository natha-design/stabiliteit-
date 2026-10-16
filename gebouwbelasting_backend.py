"""
Backend voor de gebouwbelasting-app.

"""
import io
import math

import pandas as pd

G = 9.81  # m/s²

# ----------------------------------------------------------------------------
# Standaardgegevens
# ----------------------------------------------------------------------------
DEFAULT_MATERIALS = [
    ("Tegels", 2300.0),
    ("Cementchape", 2000.0),
    ("Uitvullaag (zand-cement)", 1900.0),
    ("Uitvullaag (EPS-beton)", 600.0),
    ("Isolatie (PIR/PUR)", 35.0),
    ("Isolatie (steenwol)", 100.0),
    ("Gewapend beton", 2500.0),
    ("Gipskarton", 850.0),
    ("Staal", 7850.0),
    ("Hout (C24)", 420.0),
    ("Gelamineerd hout (GL24h)", 420.0),
    ("Baksteenmetselwerk", 1800.0),
    ("Dakgrind (ballast)", 1800.0),
    ("Bitumen dakbedekking", 1100.0),
]

BEAM_BASE = [
    "Balk-ID", "Verdieping", "Materiaal", "Breedte b (mm)", "Hoogte h (mm)",
    "Oppervlakte override (cm²)", "Overspanning L (m)", "Invloedsbreedte (m)",
]

COL_BASE = [
    "Kolom-ID", "Materiaal", "Breedte b (mm)", "Diepte h (mm)", "Oppervlakte override (cm²)",
    "Invloedsoppervlak (m²)", "Onderste gedragen niveau", "Bovenste gedragen niveau", "Extra puntlast bovenaan (kN)",
]


def default_materials_df():
    return pd.DataFrame(DEFAULT_MATERIALS, columns=["Materiaal", "Dichtheid (kg/m³)"])


def floor_layers_default():
    return pd.DataFrame([
        {"Laag": "Vloerafwerking", "Materiaal": "Tegels", "Dikte (cm)": 1.5, "Dichtheid override (kg/m³)": 0.0},
        {"Laag": "Chape", "Materiaal": "Cementchape", "Dikte (cm)": 6.0, "Dichtheid override (kg/m³)": 0.0},
        {"Laag": "Uitvullaag", "Materiaal": "Uitvullaag (zand-cement)", "Dikte (cm)": 4.0, "Dichtheid override (kg/m³)": 0.0},
        {"Laag": "Isolatie", "Materiaal": "Isolatie (PIR/PUR)", "Dikte (cm)": 8.0, "Dichtheid override (kg/m³)": 0.0},
        {"Laag": "Draagvloer", "Materiaal": "Gewapend beton", "Dikte (cm)": 20.0, "Dichtheid override (kg/m³)": 0.0},
        {"Laag": "Plafondafwerking", "Materiaal": "Gipskarton", "Dikte (cm)": 1.25, "Dichtheid override (kg/m³)": 0.0},
    ])


def roof_layers_default():
    return pd.DataFrame([
        {"Laag": "Ballast", "Materiaal": "Dakgrind (ballast)", "Dikte (cm)": 5.0, "Dichtheid override (kg/m³)": 0.0},
        {"Laag": "Dakbedekking", "Materiaal": "Bitumen dakbedekking", "Dikte (cm)": 1.0, "Dichtheid override (kg/m³)": 0.0},
        {"Laag": "Isolatie", "Materiaal": "Isolatie (PIR/PUR)", "Dikte (cm)": 12.0, "Dichtheid override (kg/m³)": 0.0},
        {"Laag": "Draagvloer", "Materiaal": "Gewapend beton", "Dikte (cm)": 20.0, "Dichtheid override (kg/m³)": 0.0},
        {"Laag": "Plafondafwerking", "Materiaal": "Gipskarton", "Dikte (cm)": 1.25, "Dichtheid override (kg/m³)": 0.0},
    ])


def default_floor_name(i, n):
    if n == 1:
        return "Gelijkvloers"
    if i == 0:
        return "Gelijkvloers"
    if i == n - 1:
        return "Dak"
    return f"Verdieping {i}"


def default_beams(floor_names):
    first = floor_names[1] if len(floor_names) > 1 else floor_names[0]
    return pd.DataFrame([
        {"Balk-ID": "B1", "Verdieping": first, "Materiaal": "Staal", "Breedte b (mm)": 100.0,
         "Hoogte h (mm)": 200.0, "Oppervlakte override (cm²)": 28.5, "Overspanning L (m)": 5.0,
         "Invloedsbreedte (m)": 3.0},
        {"Balk-ID": "B2", "Verdieping": first, "Materiaal": "Gewapend beton", "Breedte b (mm)": 300.0,
         "Hoogte h (mm)": 500.0, "Oppervlakte override (cm²)": 0.0, "Overspanning L (m)": 6.0,
         "Invloedsbreedte (m)": 4.0},
    ])


def default_columns(floor_names):
    low = floor_names[1] if len(floor_names) > 1 else floor_names[0]
    return pd.DataFrame([
        {"Kolom-ID": "K1", "Materiaal": "Gewapend beton", "Breedte b (mm)": 300.0, "Diepte h (mm)": 300.0,
         "Oppervlakte override (cm²)": 0.0, "Invloedsoppervlak (m²)": 20.0,
         "Onderste gedragen niveau": low, "Bovenste gedragen niveau": floor_names[-1],
         "Extra puntlast bovenaan (kN)": 0.0},
    ])


# ----------------------------------------------------------------------------
# Hulpfuncties
# ----------------------------------------------------------------------------
def num(v, default=0.0):
    """Veilig omzetten naar float (lege cellen / tekst -> default)."""
    try:
        f = float(v)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def txt(v):
    return "" if v is None or (isinstance(v, float) and math.isnan(v)) else str(v).strip()


def section_area_m2(b_mm, h_mm, override_cm2):
    """Doorsnede in m²: eigen oppervlakte (bv. IPE-profiel) of b × h."""
    if override_cm2 and override_cm2 > 0:
        return override_cm2 / 1e4
    return b_mm * h_mm / 1e6


def materials_from_df(df):
    """Materiaaltabel -> dict {naam: dichtheid}."""
    materials = {}
    for _, r in df.iterrows():
        name = txt(r.get("Materiaal"))
        if name and pd.notna(r.get("Dichtheid (kg/m³)")):
            materials[name] = float(r["Dichtheid (kg/m³)"])
    return materials


def add_custom_column(df, name, kind):
    """Voeg een eigen kolom toe. Gooit ValueError met een boodschap voor de gebruiker."""
    name = name.strip()
    if not name:
        raise ValueError("Geef een naam op.")
    if name in df.columns:
        raise ValueError("Die kolom bestaat al.")
    out = df.copy().reset_index(drop=True)
    out[name] = "" if kind == "Tekst" else 0.0
    return out


def remove_custom_column(df, name):
    return df.drop(columns=[name]).reset_index(drop=True)


# ----------------------------------------------------------------------------
# Vloeren & daken
# ----------------------------------------------------------------------------
def compute_layers(df, materials):
    d = df.copy().reset_index(drop=True)
    dens, weights = [], []
    for _, r in d.iterrows():
        ov = num(r.get("Dichtheid override (kg/m³)"))
        rho = ov if ov > 0 else materials.get(txt(r.get("Materiaal")), 0.0)
        thick = max(num(r.get("Dikte (cm)")), 0.0)
        dens.append(rho)
        weights.append(thick / 100.0 * rho * G / 1000.0)
    d["Dichtheid gebruikt (kg/m³)"] = dens
    d["Eigengewicht (kN/m²)"] = weights
    return d


def build_floor(name, height, qk, extra, area, layers_df, materials, gamma_g, gamma_q):
    """
    Berekent één niveau.
    Geeft terug: (floor_dict, weighted_df, lagen_zonder_dichtheid)
    """
    weighted = compute_layers(layers_df, materials)
    gk_layers = float(weighted["Eigengewicht (kN/m²)"].sum())
    gk_total = gk_layers + extra
    total = gk_total + qk

    missing = weighted[(weighted["Dichtheid gebruikt (kg/m³)"] == 0) & (weighted["Dikte (cm)"].fillna(0) > 0)]
    missing_names = [txt(x) for x in missing["Laag"]]

    floor = {
        "Niveau": name,
        "Kolomhoogte (m)": height,
        "Lagen (kN/m²)": gk_layers,
        "Extra permanent (kN/m²)": extra,
        "Gk (kN/m²)": gk_total,
        "Qk (kN/m²)": qk,
        "Gk + Qk (kN/m²)": total,
        "ULS indicatief (kN/m²)": gamma_g * gk_total + gamma_q * qk,
        "Oppervlakte (m²)": area,
        "Totaal Gk (kN)": gk_total * area if area > 0 else None,
        "Totaal Qk (kN)": qk * area if area > 0 else None,
    }
    return floor, weighted, missing_names


def index_floors(floors):
    """Geeft (floor_names, floor_by_name, floor_index, heeft_dubbele_namen)."""
    floor_names = [f["Niveau"] for f in floors]
    floor_by_name = {}
    for f in floors:
        floor_by_name.setdefault(f["Niveau"], f)
    floor_index = {}
    for idx, nm in enumerate(floor_names):
        floor_index.setdefault(nm, idx)
    has_duplicates = len(set(floor_names)) != len(floor_names)
    return floor_names, floor_by_name, floor_index, has_duplicates


# ----------------------------------------------------------------------------
# Balken
# ----------------------------------------------------------------------------
def compute_beams(beams_df, floor_by_name, materials, include_self, gamma_g, gamma_q):
    """Geeft (resultaten_lijst, overgeslagen_ids)."""
    extras = [c for c in beams_df.columns if c not in BEAM_BASE]
    results, skipped = [], []
    for _, row in beams_df.iterrows():
        bid = txt(row.get("Balk-ID"))
        L = num(row.get("Overspanning L (m)"))
        if L <= 0:
            continue
        fl = floor_by_name.get(txt(row.get("Verdieping")))
        if fl is None:
            skipped.append(bid or "(zonder ID)")
            continue
        mat = txt(row.get("Materiaal"))
        rho = materials.get(mat, 0.0)
        A = section_area_m2(num(row.get("Breedte b (mm)")), num(row.get("Hoogte h (mm)")),
                            num(row.get("Oppervlakte override (cm²)")))
        width = num(row.get("Invloedsbreedte (m)"))

        g_self = A * rho * G / 1000.0 if include_self else 0.0
        g_floor = fl["Gk (kN/m²)"] * width
        q_var = fl["Qk (kN/m²)"] * width
        g_line = g_self + g_floor
        q_char = g_line + q_var
        q_uls = gamma_g * g_line + gamma_q * q_var

        res = {
            "Balk-ID": bid,
            "Verdieping": fl["Niveau"],
            "Materiaal": mat,
            "Doorsnede (cm²)": A * 1e4,
            "Overspanning (m)": L,
            "Invloedsbreedte (m)": width,
            "Eigengewicht balk (kN/m)": g_self,
            "Vloer permanent (kN/m)": g_floor,
            "Veranderlijk (kN/m)": q_var,
            "Lijnlast karakt. (kN/m)": q_char,
            "M karakt. (kNm)": q_char * L ** 2 / 8,
            "V karakt. (kN)": q_char * L / 2,
            "Lijnlast ULS indic. (kN/m)": q_uls,
            "M ULS indic. (kNm)": q_uls * L ** 2 / 8,
            "V ULS indic. (kN)": q_uls * L / 2,
            "Steunpuntsreactie karakt. (kN)": q_char * L / 2,
        }
        for c in extras:
            res[c] = row.get(c)
        results.append(res)
    return results, skipped


# ----------------------------------------------------------------------------
# Kolommen
# ----------------------------------------------------------------------------
def compute_columns(cols_df, floors, floor_index, materials, gamma_g, gamma_q):
    """Geeft (resultaten_lijst, detail_lijst, overgeslagen_ids)."""
    extras = [c for c in cols_df.columns if c not in COL_BASE]
    results, detail, skipped = [], [], []
    for _, row in cols_df.iterrows():
        cid = txt(row.get("Kolom-ID"))
        lo_name = txt(row.get("Onderste gedragen niveau"))
        hi_name = txt(row.get("Bovenste gedragen niveau"))
        if lo_name not in floor_index or hi_name not in floor_index:
            if cid:
                skipped.append(cid)
            continue
        a, b = floor_index[lo_name], floor_index[hi_name]
        if a > b:
            a, b = b, a
        mat = txt(row.get("Materiaal"))
        rho = materials.get(mat, 0.0)
        A = section_area_m2(num(row.get("Breedte b (mm)")), num(row.get("Diepte h (mm)")),
                            num(row.get("Oppervlakte override (cm²)")))
        trib = num(row.get("Invloedsoppervlak (m²)"))
        point = num(row.get("Extra puntlast bovenaan (kN)"))

        g_cum, q_cum, self_total = point, 0.0, 0.0
        for j in range(b, a - 1, -1):
            fl = floors[j]
            g_cum += fl["Gk (kN/m²)"] * trib
            q_cum += fl["Qk (kN/m²)"] * trib
            self_w = A * rho * G / 1000.0 * fl["Kolomhoogte (m)"]
            g_cum += self_w
            self_total += self_w
            n_char = g_cum + q_cum
            detail.append({
                "Kolom-ID": cid,
                "Niveau (kolomstuk eronder)": fl["Niveau"],
                "Eigengewicht stuk (kN)": self_w,
                "G cumulatief (kN)": g_cum,
                "Q cumulatief (kN)": q_cum,
                "N karakt. (kN)": n_char,
                "N ULS indic. (kN)": gamma_g * g_cum + gamma_q * q_cum,
            })

        n_char = g_cum + q_cum
        n_uls = gamma_g * g_cum + gamma_q * q_cum
        sigma = n_char / (A * 1000.0) if A > 0 else None  # MPa
        res = {
            "Kolom-ID": cid,
            "Materiaal": mat,
            "Doorsnede (cm²)": A * 1e4,
            "Gedragen niveaus": f"{floors[a]['Niveau']} → {floors[b]['Niveau']}",
            "Invloedsoppervlak (m²)": trib,
            "Eigengewicht kolom (kN)": self_total,
            "G voet (kN)": g_cum,
            "Q voet (kN)": q_cum,
            "N voet karakt. (kN)": n_char,
            "N voet ULS indic. (kN)": n_uls,
            "Gem. drukspanning N/A (MPa)": sigma,
        }
        for c in extras:
            res[c] = row.get(c)
        results.append(res)
    return results, detail, skipped


# ----------------------------------------------------------------------------
# Overzicht & export
# ----------------------------------------------------------------------------
def totals(floors_df):
    """Totale Gk en Qk (kN) over alle niveaus waar een oppervlakte is ingevuld."""
    if floors_df.empty:
        return 0.0, 0.0
    return (floors_df["Totaal Gk (kN)"].sum(skipna=True),
            floors_df["Totaal Qk (kN)"].sum(skipna=True))


def materials_table(materials):
    return pd.DataFrame({"Materiaal": list(materials.keys()),
                         "Dichtheid (kg/m³)": list(materials.values())})


def to_csv(df):
    return df.to_csv(index=False, sep=";", decimal=",").encode("utf-8-sig")


def to_excel(sheets):
    try:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as xw:
            for name, df in sheets.items():
                df.to_excel(xw, sheet_name=name[:31], index=False)
        return buf.getvalue()
    except Exception:
        return None
