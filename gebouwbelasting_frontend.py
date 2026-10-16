"""
Frontend (Streamlit) voor de gebouwbelasting-app.

Starten met:  streamlit run gebouwbelasting_frontend.py
Alle berekeningen zitten in gebouwbelasting_backend.py.
"""
import pandas as pd
import streamlit as st

import gebouwbelasting_backend as be

st.set_page_config(page_title="Gebouwbelasting", page_icon="🏗️", layout="wide")

st.markdown(
    """
    <style>
    .block-container {padding-top: 2rem; max-width: 1400px;}
    div[data-testid="stMetric"] {
        background: rgba(128,128,128,0.08);
        border: 1px solid rgba(128,128,128,0.25);
        padding: 12px 16px;
        border-radius: 12px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ----------------------------------------------------------------------------
# UI-hulpfuncties
# ----------------------------------------------------------------------------
def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value


def column_manager(state_key, ver_key, current_df, base_cols):
    """Laat de gebruiker eigen kolommen (tekst of getal) toevoegen/verwijderen."""
    with st.expander("➕ Eigen kolom toevoegen of verwijderen"):
        c1, c2, c3 = st.columns([3, 2, 1])
        new_name = c1.text_input("Naam nieuwe kolom", key=f"{state_key}_newname")
        kind = c2.selectbox("Type", ["Tekst", "Getal"], key=f"{state_key}_kind")
        c3.write("")
        c3.write("")
        if c3.button("Toevoegen", key=f"{state_key}_add"):
            try:
                st.session_state[state_key] = be.add_custom_column(current_df, new_name, kind)
            except ValueError as e:
                st.warning(str(e))
            else:
                st.session_state[ver_key] += 1
                st.rerun()
        extras = [c for c in current_df.columns if c not in base_cols]
        if extras:
            d1, d2 = st.columns([5, 1])
            to_del = d1.selectbox("Eigen kolom verwijderen", extras, key=f"{state_key}_del")
            d2.write("")
            d2.write("")
            if d2.button("Verwijder", key=f"{state_key}_delbtn"):
                st.session_state[state_key] = be.remove_custom_column(current_df, to_del)
                st.session_state[ver_key] += 1
                st.rerun()


# ----------------------------------------------------------------------------
# Titel + zijbalk
# ----------------------------------------------------------------------------
st.title("🏗️ Gebouwbelasting")
st.caption("Voorlopige belastingsraming van vloeren, balken en kolommen.")

with st.sidebar:
    st.header("⚙️ Instellingen")
    include_self = st.checkbox("Eigengewicht van balken meerekenen", value=True)
    st.markdown("Indicatieve factoren ")
    gamma_g = st.number_input("GK permanente lasten", min_value=1.0, value=1.35, step=0.05)
    gamma_q = st.number_input("QK veranderlijke lasten", min_value=1.0, value=1.50, step=0.05)

    st.markdown("---")
    st.caption("Niveau 1 = laagste niveau. Volgorde van onder naar boven.")

tab_mat, tab_floor, tab_beam, tab_col, tab_sum = st.tabs(
    ["1️⃣ Materialen", "2️⃣ Vloeren & daken", "3️⃣ Balken", "4️⃣ Kolommen", "5️⃣ Overzicht & export"]
)

# ----------------------------------------------------------------------------
# TAB 1: Materialen
# ----------------------------------------------------------------------------
with tab_mat:
    st.subheader("Materiaalbibliotheek")
    st.write(
        "Voeg hier materialen en hun volumieke massa toe. Ze zijn daarna te kiezen bij de vloerlagen, balken en kolommen. "
        "Hernoem je een materiaal, kies het dan opnieuw in de andere tabs."
    )
    init_state("materials", be.default_materials_df())
    mat_edit = st.data_editor(
        st.session_state["materials"],
        num_rows="dynamic",
        key="mat_editor",
        column_config={
            "Materiaal": st.column_config.TextColumn("Materiaal", required=True),
            "Dichtheid (kg/m³)": st.column_config.NumberColumn(
                "Dichtheid (kg/m³)", min_value=0.0, step=10.0, format="%.1f", required=True
            ),
        },
    )

materials = be.materials_from_df(mat_edit)
mat_names = list(materials.keys())

# ----------------------------------------------------------------------------
# TAB 2: Vloeren & daken
# ----------------------------------------------------------------------------
floors = []
with tab_floor:
    st.subheader("Vloer- en dakopbouw per niveau")
    st.write(
        "Elk niveau heeft een eigen opbouw. Voeg lagen toe via de lege rij onderaan de tabel "
        "(bv. uitvullaag, chape, akoestische laag, dampscherm…). Kies het materiaal uit de bibliotheek; "
        "de dichtheid wordt automatisch ingevuld. Wil je een afwijkende dichtheid, vul die dan in bij *override*."
    )
    init_state("layer_ver", 0)
    n_levels = int(st.number_input("Aantal niveaus (vloeren/daken)", min_value=1, max_value=20, value=3, step=1))

    for i in range(n_levels):
        is_roof = n_levels > 1 and i == n_levels - 1
        with st.expander(f"Niveau {i + 1}", expanded=(i == 0)):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Naam niveau", value=be.default_floor_name(i, n_levels), key=f"fname_{i}")
            qk = c1.number_input(
                "Opgelegde belasting qk (kN/m²)", min_value=0.0, value=0.75 if is_roof else 2.0,
                step=0.1, key=f"qk_{i}",
            )
            extra = c2.number_input(
                "Extra permanente belasting (kN/m²)", min_value=0.0, value=0.2, step=0.1, key=f"extra_{i}",
                help="Bv. technieken, scheidingswanden , plafondinstallaties.",
            )
            height = c2.number_input(
                "Kolomhoogte onder dit niveau (m)", min_value=0.1, value=3.0, step=0.1, key=f"height_{i}",
                help="Hoogte van de kolom dat dit niveau draagt (van het niveau eronder tot dit niveau).",
            )
            area = c3.number_input(
                "Oppervlakte van dit niveau (m², optioneel)", min_value=0.0, value=0.0, step=1.0, key=f"area_{i}",
                help="Laat op 0 als je geen totale belasting in kN nodig hebt.",
            )

            init_state(f"layers_{i}", be.roof_layers_default() if is_roof else be.floor_layers_default())
            edited = st.data_editor(
                st.session_state[f"layers_{i}"],
                num_rows="dynamic",
                key=f"editor_{i}_{st.session_state['layer_ver']}",
                column_config={
                    "Laag": st.column_config.TextColumn("Laag", required=True),
                    "Materiaal": st.column_config.SelectboxColumn("Materiaal", options=mat_names),
                    "Dikte (cm)": st.column_config.NumberColumn("Dikte (cm)", min_value=0.0, step=0.5, format="%.2f"),
                    "Dichtheid override (kg/m³)": st.column_config.NumberColumn(
                        "Dichtheid override (kg/m³)", min_value=0.0, step=50.0, format="%.1f",
                        help="0 = dichtheid uit de materiaalbibliotheek gebruiken",
                    ),
                },
            )

            floor, weighted, missing_names = be.build_floor(
                name, height, qk, extra, area, edited, materials, gamma_g, gamma_q
            )
            if missing_names:
                st.warning("Sommige lagen hebben dichtheid 0 (materiaal niet gekozen of niet gevonden): "
                           + ", ".join(missing_names))

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Eigengewicht lagen", f"{floor['Lagen (kN/m²)']:.2f} kN/m²")
            m2.metric("Permanent Gk (incl. extra)", f"{floor['Gk (kN/m²)']:.2f} kN/m²")
            m3.metric("Veranderlijk Qk", f"{qk:.2f} kN/m²")
            m4.metric("Totaal Gk + Qk", f"{floor['Gk + Qk (kN/m²)']:.2f} kN/m²")

            st.dataframe(weighted.round(3), hide_index=True)
            if st.button("Kopieer deze opbouw naar alle niveaus", key=f"copy_{i}"):
                for k in range(n_levels):
                    st.session_state[f"layers_{k}"] = edited.copy().reset_index(drop=True)
                st.session_state["layer_ver"] += 1
                st.rerun()

            floors.append(floor)

floor_names, floor_by_name, floor_index, has_dup = be.index_floors(floors)
if has_dup:
    st.error("Twee niveaus hebben dezelfde naam. Geef elk niveau een unieke naam.")

# ----------------------------------------------------------------------------
# TAB 3: Balken
# ----------------------------------------------------------------------------
with tab_beam:
    st.subheader("Balken")
    st.write(
        "Geef per balk enkel materiaal, afmetingen en overspanning in. Het eigengewicht volgt uit **doorsnede × dichtheid**. "
        "Voor een profiel (bv. IPE, HEA) vul je de doorsnede in bij *Oppervlakte override (cm²)*; "
        "laat je dat op 0, dan wordt b × h gebruikt. Berekening voor een eenvoudig opgelegde balk: M = qL²/8 en V = qL/2."
    )
    init_state("beams", be.default_beams(floor_names))
    init_state("beam_ver", 0)
    beams_edit = st.data_editor(
        st.session_state["beams"],
        num_rows="dynamic",
        key=f"beam_editor_{st.session_state['beam_ver']}",
        column_config={
            "Balk-ID": st.column_config.TextColumn("Balk-ID", required=True),
            "Verdieping": st.column_config.SelectboxColumn("Verdieping", options=floor_names, required=True),
            "Materiaal": st.column_config.SelectboxColumn("Materiaal", options=mat_names, required=True),
            "Breedte b (mm)": st.column_config.NumberColumn("Breedte b (mm)", min_value=0.0, step=10.0, format="%.0f"),
            "Hoogte h (mm)": st.column_config.NumberColumn("Hoogte h (mm)", min_value=0.0, step=10.0, format="%.0f"),
            "Oppervlakte override (cm²)": st.column_config.NumberColumn(
                "Oppervlakte override (cm²)", min_value=0.0, step=1.0, format="%.2f",
                help="Doorsnede van een profiel. 0 = b × h gebruiken.",
            ),
            "Overspanning L (m)": st.column_config.NumberColumn("Overspanning L (m)", min_value=0.0, step=0.1, format="%.2f"),
            "Invloedsbreedte (m)": st.column_config.NumberColumn("Invloedsbreedte (m)", min_value=0.0, step=0.1, format="%.2f"),
        },
    )
    column_manager("beams", "beam_ver", beams_edit, be.BEAM_BASE)

    beam_results, skipped_b = be.compute_beams(
        beams_edit, floor_by_name, materials, include_self, gamma_g, gamma_q
    )
    if skipped_b:
        st.warning("Deze balken hebben een verdieping die niet (meer) bestaat – kies de verdieping opnieuw: "
                   + ", ".join(skipped_b))
    beams_df = pd.DataFrame(beam_results)
    st.markdown("#### Resultaten")
    if beams_df.empty:
        st.info("Nog geen balken met een overspanning > 0.")
    else:
        k1, k2 = st.columns(2)
        k1.metric("Aantal balken", len(beams_df))
        k2.metric("Grootste dwarskracht ", f"{beams_df['V ULS indic. (kN)'].max():.1f} kN")
        st.dataframe(beams_df.round(2), hide_index=True)

# ----------------------------------------------------------------------------
# TAB 4: Kolommen
# ----------------------------------------------------------------------------
with tab_col:
    st.subheader("Kolommen")
    st.write(
        "Een kolom draagt de vloeren van het **onderste** tot het **bovenste** gedragen niveau. "
        "De krachten worden naar beneden toe opgeteld."
    )
    init_state("columns", be.default_columns(floor_names))
    init_state("col_ver", 0)
    cols_edit = st.data_editor(
        st.session_state["columns"],
        num_rows="dynamic",
        key=f"col_editor_{st.session_state['col_ver']}",
        column_config={
            "Kolom-ID": st.column_config.TextColumn("Kolom-ID", required=True),
            "Materiaal": st.column_config.SelectboxColumn("Materiaal", options=mat_names, required=True),
            "Breedte b (mm)": st.column_config.NumberColumn("Breedte b (mm)", min_value=0.0, step=10.0, format="%.0f"),
            "Diepte h (mm)": st.column_config.NumberColumn("Diepte h (mm)", min_value=0.0, step=10.0, format="%.0f"),
            "Oppervlakte override (cm²)": st.column_config.NumberColumn(
                "Oppervlakte override (cm²)", min_value=0.0, step=1.0, format="%.2f",
                help="Voor profielen of buizen. 0 = b × h gebruiken.",
            ),
            "Invloedsoppervlak (m²)": st.column_config.NumberColumn(
                "Invloedsoppervlak (m²)", min_value=0.0, step=0.5, format="%.2f",
                help="Vloeroppervlak dat per niveau op deze kolom afsteunt.",
            ),
            "Onderste gedragen niveau": st.column_config.SelectboxColumn("Onderste gedragen niveau", options=floor_names, required=True),
            "Bovenste gedragen niveau": st.column_config.SelectboxColumn("Bovenste gedragen niveau", options=floor_names, required=True),
            "Extra puntlast bovenaan (kN)": st.column_config.NumberColumn(
                "Extra puntlast bovenaan (kN)", min_value=0.0, step=1.0, format="%.1f",
                help="Extra permanente puntlast op de bovenste verdieping (bv. technieken op het dak).",
            ),
        },
    )
    column_manager("columns", "col_ver", cols_edit, be.COL_BASE)

    col_results, col_detail, skipped_c = be.compute_columns(
        cols_edit, floors, floor_index, materials, gamma_g, gamma_q
    )
    if skipped_c:
        st.warning("Deze kolommen hebben een niveau dat niet (meer) bestaat – kies opnieuw: " + ", ".join(skipped_c))
    cols_df = pd.DataFrame(col_results)
    cols_detail_df = pd.DataFrame(col_detail)
    st.markdown("#### Resultaten")
    if cols_df.empty:
        st.info("Nog geen kolommen ingevoerd.")
    else:
        k1, k2 = st.columns(2)
        k1.metric("Aantal kolommen", len(cols_df))
        k2.metric("Grootste voetlast ", f"{cols_df['N voet ULS indic. (kN)'].max():.1f} kN")
        st.dataframe(cols_df.round(2), hide_index=True)
        with st.expander("Normaalkracht per niveau (opbouw naar beneden)"):
            st.dataframe(cols_detail_df.round(2), hide_index=True)
        
# ----------------------------------------------------------------------------
# TAB 5: Overzicht & export
# ----------------------------------------------------------------------------
with tab_sum:
    st.subheader("Overzicht")
    floors_df = pd.DataFrame(floors)
    beams_df = pd.DataFrame(beam_results)
    cols_df = pd.DataFrame(col_results)
    cols_detail_df = pd.DataFrame(col_detail)

    t1, t2, t3, t4 = st.columns(4)
    t1.metric("Niveaus", len(floors_df))
    t2.metric("Balken", len(beams_df))
    t3.metric("Kolommen", len(cols_df))
    total_gk, total_qk = be.totals(floors_df)
    t4.metric("Totale Gk + Qk ", f"{total_gk + total_qk:.0f} kN")

    st.markdown("#### Vlaklast per niveau (kN/m²)")
    if not floors_df.empty:
        chart_df = floors_df.set_index("Niveau")[["Gk (kN/m²)", "Qk (kN/m²)"]]
        st.bar_chart(chart_df)
        st.dataframe(floors_df.round(2), hide_index=True)

    st.markdown("#### Balken")
    if beams_df.empty:
        st.caption("Geen balken.")
    else:
        st.dataframe(beams_df.round(2), hide_index=True)

    st.markdown("#### Kolommen")
    if cols_df.empty:
        st.caption("Geen kolommen.")
    else:
        st.dataframe(cols_df.round(2), hide_index=True)

    st.markdown("#### Export")
    e1, e2, e3, e4 = st.columns(4)
    e1.download_button("⬇️ Niveaus (CSV)", be.to_csv(floors_df), "niveaus.csv", "text/csv")
    e2.download_button("⬇️ Balken (CSV)", be.to_csv(beams_df), "balken.csv", "text/csv")
    e3.download_button("⬇️ Kolommen (CSV)", be.to_csv(cols_df), "kolommen.csv", "text/csv")
    sheets = {"Niveaus": floors_df, "Balken": beams_df, "Kolommen": cols_df,
              "Kolom per niveau": cols_detail_df, "Materialen": be.materials_table(materials)}
    xlsx = be.to_excel(sheets)
    if xlsx:
        e4.download_button(
            "⬇️ Alles in Excel", xlsx, "gebouwbelasting.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    else:
        e4.caption("Installeer `openpyxl` voor Excel-export.")

    st.caption(
        "Eenheden: vlaklast kN/m², lijnlast kN/m, moment kNm, kracht kN. "
       
    )
