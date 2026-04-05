import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import holidays
from streamlit_calendar import calendar
import json
import os
import io

# --- IMPORTATIONS POUR EXCEL ---
from openpyxl import Workbook
from openpyxl.styles import Alignment, PatternFill, Font, Border, Side

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Planning RI Pro", layout="wide", initial_sidebar_state="expanded")

# --- THÈME MODERNE & ERGONOMIQUE (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #1E293B; }
    .stApp { background-color: #F8FAFC; }
    h1 { color: #0F172A; font-weight: 800; border-bottom: 4px solid #2563EB; padding-bottom: 10px; margin-bottom: 1rem; }
    h2 { color: #334155; font-weight: 700; margin-top: 1.5rem; }
    .stButton>button { width: 100%; border-radius: 8px; border: 1px solid #CBD5E1; background-color: #FFFFFF; color: #334155; padding: 0.6rem; transition: all 0.2s; text-align: left; font-weight: 600; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .stButton>button:hover { border-color: #2563EB; color: #2563EB; background-color: #EFF6FF; transform: translateY(-1px); box-shadow: 0 4px 6px rgba(37, 99, 235, 0.1); }
    .btn-valider button { background-color: #059669 !important; color: white !important; font-weight: 800; }
    .btn-generer button { background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important; color: white !important; font-weight: 800; padding: 1rem !important; }
    .btn-supprimer button { background-color: #DC2626 !important; color: white !important; padding: 2px 10px !important; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: #E2E8F0; padding: 6px; border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { border-radius: 6px; background-color: transparent; font-weight: 600; color: #64748B;}
    .stTabs [aria-selected="true"] { background-color: white !important; color: #2563EB !important; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    [data-testid="stTable"] { background-color: white; border-radius: 8px; overflow: hidden; border: 1px solid #E2E8F0; }
    </style>
    """, unsafe_allow_html=True)

# --- TRADUCTIONS FRANÇAISES ---
JOURS_FR = {"Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi",
            "Thursday": "Jeudi", "Friday": "Vendredi", "Saturday": "Samedi", "Sunday": "Dimanche"}
MOIS_FR = {1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
           7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"}

# --- SYSTÈME DE SAUVEGARDE LOCALE ---
FICHIER_SAUVEGARDE = "equipe_ri.json"

def charger_donnees():
    if os.path.exists(FICHIER_SAUVEGARDE):
        with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Mise à jour automatique des anciens fichiers pour intégrer le score WE
            for m in data:
                if "score_we" not in data[m]:
                    data[m]["score_we"] = 0
            return data
    return None

def sauvegarder_donnees(data):
    with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# --- INITIALISATION DE LA BASE DE DONNÉES ---
if 'merms_data' not in st.session_state:
    donnees_sauvees = charger_donnees()
    if donnees_sauvees:
        st.session_state.merms_data = donnees_sauvees
    else:
        noms = ["Lechevin L.", "Abdelaoui F.", "Laurin M.", "Cotton L.", "Bacquet V.", 
                "Leroux C.", "Brasseur O.", "Dupierris P.A.", "Talbaut V.", "Michel L.", "Dhondt F.", "Geffroy C."]
        st.session_state.merms_data = {
            name: {
                "lignes": [2] if name in ["Dhondt F.", "Geffroy C."] else [1, 2],
                "score_cumule": 0, 
                "score_we": 0, # NOUVEAU COMPTEUR SPÉCIFIQUE WEEK-END
                "pref_vendredi": False, 
                "absences": []
            } for name in noms
        }
        sauvegarder_donnees(st.session_state.merms_data)

# --- FENÊTRE POP-UP : CALENDRIER INTERACTIF ---
@st.dialog("Saisie des Desiderata", width="large")
def modal_desiderata(name):
    st.write(f"### 👤 Agent : **{name}**")
    temp_key = f"temp_{name}"
    if temp_key not in st.session_state:
        st.session_state[temp_key] = st.session_state.merms_data[name]["absences"].copy()

    cal_options = {
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"},
        "selectable": True, "locale": "fr", "firstDay": 1, "height": "450px"
    }
    
    events = [{"title": "ABSENT", "start": d, "end": d, "color": "#DC2626"} for d in st.session_state[temp_key]]
    res = calendar(events=events, options=cal_options, key=f"cal_{name}")

    if "select" in res:
        start = res["select"]["start"].split("T")[0]
        end_raw = datetime.strptime(res["select"]["end"].split("T")[0], "%Y-%m-%d") - timedelta(days=1)
        new_days = pd.date_range(start, end_raw.strftime("%Y-%m-%d")).strftime("%Y-%m-%d").tolist()
        for d in new_days:
            if d not in st.session_state[temp_key]: st.session_state[temp_key].append(d)
        st.rerun()

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🗑️ Effacer toutes mes saisies", use_container_width=True):
            st.session_state[temp_key] = []
            st.rerun()
    with col_b:
        v_pref = st.toggle("Coupler le vendredi au WE", value=st.session_state.merms_data[name]["pref_vendredi"])

    st.write("---")
    st.markdown('<div class="btn-valider">', unsafe_allow_html=True)
    if st.button("✅ CONFIRMER ET ENREGISTRER MES CHOIX", use_container_width=True):
        st.session_state.merms_data[name]["absences"] = st.session_state[temp_key]
        st.session_state.merms_data[name]["pref_vendredi"] = v_pref
        del st.session_state[temp_key]
        sauvegarder_donnees(st.session_state.merms_data)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- MOTEUR ALGORITHMIQUE AVANCÉ (DOUBLE ÉQUITÉ) ---
def generer_planning(debut, fin):
    fr_holidays = holidays.France(years=[debut.year, fin.year])
    jours = pd.date_range(debut, fin)
    
    planning = {d: {"L1": "⚠️ À POURVOIR", "L2": "⚠️ À POURVOIR"} for d in jours}
    
    # Copies des scores pour simulation
    scores = {m: v['score_cumule'] for m, v in st.session_state.merms_data.items()}
    scores_we = {m: v['score_we'] for m, v in st.session_state.merms_data.items()}
    assigned_dates = {m: set() for m in st.session_state.merms_data.keys()}
    
    def est_dispo(m, dates_list):
        return not any(dt.strftime("%Y-%m-%d") in st.session_state.merms_data[m]["absences"] for dt in dates_list)

    # 1. PASSE DES WEEK-ENDS (Priorité stricte à l'équité des WE)
    for d in jours:
        if d.weekday() == 5: # Samedi
            d_sun = d + timedelta(days=1)
            d_fri = d - timedelta(days=1)
            we_days = [d]
            if d_sun <= fin: we_days.append(d_sun)
            
            for ligne in ["L1", "L2"]:
                candidats = []
                for m, v in st.session_state.merms_data.items():
                    if (ligne == "L1" and 1 not in v["lignes"]) or (ligne == "L2" and 2 not in v["lignes"]): continue
                    if ligne == "L2" and planning[d]["L1"] == m: continue
                    if not est_dispo(m, we_days): continue
                    
                    if v["pref_vendredi"] and d_fri >= debut:
                        if not est_dispo(m, [d_fri]) or planning[d_fri][ligne] != "⚠️ À POURVOIR": continue 
                    candidats.append(m)
                
                # SÉLECTION : On prend celui qui a fait le MOINS de WE. En cas d'égalité, celui qui a le moins de points totaux.
                choix = min(candidats, key=lambda x: (scores_we[x], scores[x])) if candidats else None
                
                if choix:
                    scores_we[choix] += 1 # 1 WE de plus au compteur
                    for wd in we_days:
                        planning[wd][ligne] = choix
                        assigned_dates[choix].add(wd)
                        scores[choix] += 3 
                    
                    if st.session_state.merms_data[choix]["pref_vendredi"] and d_fri >= debut:
                        planning[d_fri][ligne] = choix
                        assigned_dates[choix].add(d_fri)
                        scores[choix] += 1
                        
    # 2. PASSE DE LA SEMAINE (Règles métiers classiques)
    for d in jours:
        for ligne in ["L1", "L2"]:
            if planning[d][ligne] != "⚠️ À POURVOIR": continue
            
            candidats = []
            for m, v in st.session_state.merms_data.items():
                if (ligne == "L1" and 1 not in v["lignes"]) or (ligne == "L2" and 2 not in v["lignes"]): continue
                if ligne == "L2" and planning[d]["L1"] == m: continue
                if not est_dispo(m, [d]): continue
                
                if m != "Talbaut V.": # Exception
                    if (d - timedelta(days=1)) in assigned_dates[m] or (d + timedelta(days=1)) in assigned_dates[m]:
                        continue # Pas de consécutif
                    week_num = d.isocalendar()[1]
                    jours_semaine = [ad for ad in assigned_dates[m] if ad.isocalendar()[1] == week_num]
                    if any(ad.weekday() >= 5 for ad in jours_semaine):
                        continue # Déjà un WE, pas d'astreinte
                    elif len(jours_semaine) >= 2:
                        continue # Max 2 en semaine
                            
                candidats.append(m)
                
            choix = min(candidats, key=lambda x: scores[x]) if candidats else "⚠️ À POURVOIR"
            planning[d][ligne] = choix
            if choix != "⚠️ À POURVOIR":
                assigned_dates[choix].add(d)
                scores[choix] += 3 if (d.weekday() >= 5 or d in fr_holidays) else 1

    # Formatage de la donnée
    resultat = []
    for d in jours:
        resultat.append({
            "Date": d.strftime("%d/%m/%Y"),
            "DateObj": d,
            "Jour": JOURS_FR[d.strftime("%A")],
            "Ligne 1": planning[d]["L1"],
            "Ligne 2": planning[d]["L2"],
            "Type": "FÉRIÉ/WE" if (d.weekday() >= 5 or d in fr_holidays) else "SEMAINE"
        })
    return pd.DataFrame(resultat), scores, scores_we

# --- EXPORT EXCEL : SÉPARÉ AVEC COLONNE MODIFICATION ---
def generer_excel_liste(df_planning, dict_scores, dict_scores_we):
    output = io.BytesIO()
    wb = Workbook()
    wb.remove(wb.active)

    fill_header = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
    font_header = Font(color="FFFFFF", bold=True)
    border_thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))

    df_planning['Annee'] = df_planning['DateObj'].dt.year
    df_planning['MoisNum'] = df_planning['DateObj'].dt.month

    for (annee, mois), group in df_planning.groupby(['Annee', 'MoisNum']):
        nom_mois = MOIS_FR[mois]
        
        # --- ONGLET LIGNE 1 ---
        ws_l1 = wb.create_sheet(title=f"L1 {nom_mois} {annee}")
        en_tetes = ["Date", "Jour", "Astreinte Prévue (L1)", "Modification / Remplaçant", "Motif / Commentaire"]
        ws_l1.append(en_tetes)
        
        # --- ONGLET LIGNE 2 ---
        ws_l2 = wb.create_sheet(title=f"L2 {nom_mois} {annee}")
        en_tetes_l2 = ["Date", "Jour", "Astreinte Prévue (L2)", "Modification / Remplaçant", "Motif / Commentaire"]
        ws_l2.append(en_tetes_l2)
        
        # Remplissage
        for _, row in group.iterrows():
            d_str, j_str = row['Date'], row['Jour']
            ws_l1.append([d_str, j_str, row['Ligne 1'], "", ""])
            ws_l2.append([d_str, j_str, row['Ligne 2'], "", ""])

        # Design des colonnes pour les deux feuilles
        for ws in [ws_l1, ws_l2]:
            for col_num in range(1, 6):
                cell = ws.cell(row=1, column=col_num)
                cell.fill = fill_header
                cell.font = font_header
                cell.border = border_thin
            ws.column_dimensions['A'].width = 12
            ws.column_dimensions['B'].width = 12
            ws.column_dimensions['C'].width = 25
            ws.column_dimensions['D'].width = 30 # Grande colonne pour écrire au stylo
            ws.column_dimensions['E'].width = 30
            
            # Application des bordures sur toutes les cellules
            for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=5):
                for cell in row:
                    cell.border = border_thin

    # Onglet Bilan d'équité
    ws_scores = wb.create_sheet(title="Bilan Équité")
    ws_scores.append(["Manipulateur", "Nombre de Week-ends (Année)", "Points Globaux (Charge)"])
    for idx, m in enumerate(dict_scores.keys(), 2):
        ws_scores.cell(row=idx, column=1, value=m).border = border_thin
        ws_scores.cell(row=idx, column=2, value=dict_scores_we[m]).border = border_thin
        ws_scores.cell(row=idx, column=3, value=dict_scores[m]).border = border_thin
        
    for col in ['A', 'B', 'C']:
        ws_scores.column_dimensions[col].width = 25
        ws_scores.cell(row=1, column=ord(col)-64).fill = fill_header
        ws_scores.cell(row=1, column=ord(col)-64).font = font_header

    wb.save(output)
    return output.getvalue()

# --- INTERFACE PRINCIPALE ---
st.title("🏥 Planning de Radiologie Interventionnelle")

with st.sidebar:
    st.header("⚙️ GESTION DE L'ÉQUIPE")
    with st.expander("➕ Ajouter un manipulateur", expanded=False):
        new_name = st.text_input("Nom & Prénom")
        new_l1 = st.checkbox("Fait la Ligne 1", value=True)
        new_l2 = st.checkbox("Fait la Ligne 2", value=True)
        if st.button("Ajouter à l'équipe"):
            if new_name and new_name not in st.session_state.merms_data:
                lignes = [1] if new_l1 else []
                if new_l2: lignes.append(2)
                st.session_state.merms_data[new_name] = {"lignes": lignes, "score_cumule": 0, "score_we": 0, "pref_vendredi": False, "absences": []}
                sauvegarder_donnees(st.session_state.merms_data)
                st.rerun()

    st.write("---")
    st.write("**Équipe actuelle**")
    for m in list(st.session_state.merms_data.keys()):
        c1, c2 = st.columns([4, 1])
        l_txt = "L1/L2" if len(st.session_state.merms_data[m]['lignes']) == 2 else f"L{st.session_state.merms_data[m]['lignes'][0]}"
        c1.caption(f"**{m}** ({l_txt})")
        st.markdown('<div class="btn-supprimer">', unsafe_allow_html=True)
        if c2.button("🗑️", key=f"del_{m}"):
            del st.session_state.merms_data[m]
            sauvegarder_donnees(st.session_state.merms_data)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

col_cfg, col_res = st.columns([1, 2.2])

with col_cfg:
    st.header("1. Période (Trimestre)")
    d_start = st.date_input("Début", datetime.now())
    d_end = st.date_input("Fin", datetime.now() + timedelta(days=90))
    
    st.write("---")
    st.header("2. Desiderata")
    for merm in st.session_state.merms_data.keys():
        n_abs = len(st.session_state.merms_data[merm]["absences"])
        if st.button(f"👤 {merm} ({n_abs} j. posés)", key=f"btn_{merm}"):
            modal_desiderata(merm)

with col_res:
    st.header("3. Génération & Export")
    st.markdown('<div class="btn-generer">', unsafe_allow_html=True)
    if st.button("🚀 CALCULER LA RÉPARTITION ÉQUITABLE", use_container_width=True):
        df_resultat, scores_finaux, scores_we_finaux = generer_planning(d_start, d_end)
        st.session_state.planning_final = df_resultat
        st.session_state.scores_finaux = scores_finaux
        st.session_state.scores_we_finaux = scores_we_finaux
    st.markdown('</div>', unsafe_allow_html=True)

    if 'planning_final' in st.session_state:
        st.write("---")
        # EXPORT EXCEL LISTE MODIFIABLE
        excel_data = generer_excel_liste(st.session_state.planning_final, st.session_state.scores_finaux, st.session_state.scores_we_finaux)
        nom_fichier = f"Planning_RI_{d_start.strftime('%m')}-{d_end.strftime('%m_%Y')}.xlsx"
        
        st.download_button(
            label="📥 TÉLÉCHARGEMENT EXCEL (AVEC COLONNE MODIFICATION)",
            data=excel_data,
            file_name=nom_fichier,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
        st.write("---")
        
        onglet_l1, onglet_l2, onglet_stats = st.tabs(["📋 PLANNING LIGNE 1", "📋 PLANNING LIGNE 2", "📈 ÉQUITÉ & POINTS"])
        
        with onglet_l1:
            st.table(st.session_state.planning_final[["Date", "Jour", "Ligne 1", "Type"]])
        with onglet_l2:
            st.table(st.session_state.planning_final[["Date", "Jour", "Ligne 2", "Type"]])
            
        with onglet_stats:
            st.subheader("Bilan d'Équité (Double validation)")
            st.info("La priorité est donnée à l'équité des Week-ends, puis au lissage de la charge de semaine.")
            df_bilan = pd.DataFrame({
                "Nombre de Week-ends": st.session_state.scores_we_finaux,
                "Points Globaux (Charge)": st.session_state.scores_finaux
            })
            st.table(df_bilan)
            
            st.write("---")
            if st.button("💾 VALIDER CE TRIMESTRE ET SAUVEGARDER LES SCORES"):
                for m in st.session_state.scores_finaux:
                    st.session_state.merms_data[m]['score_cumule'] = st.session_state.scores_finaux[m]
                    st.session_state.merms_data[m]['score_we'] = st.session_state.scores_we_finaux[m]
                sauvegarder_donnees(st.session_state.merms_data)
                st.success("✅ Base de données mise à jour ! L'algorithme se souviendra du nombre de WE réalisés par chacun.")
