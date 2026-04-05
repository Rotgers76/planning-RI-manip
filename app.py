import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import holidays
from streamlit_calendar import calendar
import json
import os
import io

from openpyxl import Workbook
from openpyxl.styles import Alignment, PatternFill, Font, Border, Side

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="Planning RI Pro", layout="wide", initial_sidebar_state="expanded")

# --- THÈME MODERNE & ERGONOMIQUE (BOUCLIER ANTI DARK-MODE) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    .stApp, .stApp p, .stApp span, .stApp label, .stApp div, [data-testid="stTable"] th, [data-testid="stTable"] td { 
        font-family: 'Inter', sans-serif;
        color: #1E293B !important; 
    }
    
    .stApp { background-color: #F8FAFC !important; }
    h1 { color: #0F172A !important; font-weight: 800; border-bottom: 4px solid #2563EB; padding-bottom: 10px; margin-bottom: 1rem; }
    h2, h3 { color: #334155 !important; font-weight: 700; margin-top: 1.5rem; }
    
    .stButton>button { width: 100%; border-radius: 8px; border: 1px solid #CBD5E1; background-color: #FFFFFF !important; color: #334155 !important; padding: 0.6rem; transition: all 0.2s; text-align: left; font-weight: 600; box-shadow: 0 1px 2px rgba(0,0,0,0.05); }
    .stButton>button:hover { border-color: #2563EB; color: #2563EB !important; background-color: #EFF6FF !important; transform: translateY(-1px); box-shadow: 0 4px 6px rgba(37, 99, 235, 0.1); }
    
    .btn-valider button, .btn-valider button span { background-color: #059669 !important; color: white !important; font-weight: 800; }
    .btn-generer button, .btn-generer button span { background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important; color: white !important; font-weight: 800; padding: 1rem !important; }
    .btn-supprimer button, .btn-supprimer button span { background-color: #DC2626 !important; color: white !important; padding: 2px 10px !important; }
    .btn-indispo button, .btn-indispo button span { background-color: #DC2626 !important; color: white !important; font-weight: bold; }
    .btn-dispo button, .btn-dispo button span { background-color: #16A34A !important; color: white !important; font-weight: bold; }
    .btn-clear button, .btn-clear button span { background-color: #64748B !important; color: white !important; font-weight: bold; }

    .stTabs [data-baseweb="tab-list"] { gap: 10px; background-color: #E2E8F0; padding: 6px; border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { border-radius: 6px; background-color: transparent; font-weight: 600; color: #64748B !important;}
    .stTabs [aria-selected="true"] { background-color: white !important; color: #2563EB !important; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    [data-testid="stTable"] { background-color: white !important; border-radius: 8px; overflow: hidden; border: 1px solid #E2E8F0; }
    </style>
    """, unsafe_allow_html=True)

JOURS_FR = {"Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi",
            "Thursday": "Jeudi", "Friday": "Vendredi", "Saturday": "Samedi", "Sunday": "Dimanche"}
MOIS_FR = {1: "Janvier", 2: "Février", 3: "Mars", 4: "Avril", 5: "Mai", 6: "Juin",
           7: "Juillet", 8: "Août", 9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Décembre"}

FICHIER_SAUVEGARDE = "equipe_ri.json"

def charger_donnees():
    if os.path.exists(FICHIER_SAUVEGARDE):
        with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Mise à jour pour les nouveaux compteurs (Sécurité)
            for m in data:
                if "score_we" not in data[m]: data[m]["score_we"] = 0
                if "nb_l1" not in data[m]: data[m]["nb_l1"] = 0
                if "nb_l2" not in data[m]: data[m]["nb_l2"] = 0
            return data
    return None

def sauvegarder_donnees(data):
    with open(FICHIER_SAUVEGARDE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

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
                "score_cumule": 0, "score_we": 0, 
                "nb_l1": 0, "nb_l2": 0, # Nouveaux compteurs pour ratio L1/L2
                "pref_vendredi": False, "absences": []
            } for name in noms
        }
        sauvegarder_donnees(st.session_state.merms_data)

if 'modal_ouvert' not in st.session_state:
    st.session_state.modal_ouvert = None

# --- FENÊTRE POP-UP DESIDERATA ---
@st.dialog("Saisie des Desiderata", width="large")
def modal_desiderata(name):
    st.write(f"### 👤 Agent : **{name}**")
    st.info("1️⃣ Cliquez ou glissez pour sélectionner un ou plusieurs jours (ils s'afficheront en bleu).\n2️⃣ Choisissez ensuite leur statut en bas.")
    
    temp_abs_key = f"temp_abs_{name}"
    temp_sel_key = f"temp_sel_{name}"
    last_sel_key = f"last_sel_{name}"
    
    if temp_abs_key not in st.session_state:
        st.session_state[temp_abs_key] = st.session_state.merms_data[name]["absences"].copy()
    if temp_sel_key not in st.session_state:
        st.session_state[temp_sel_key] = set() 

    str_debut = st.session_state.d_start.strftime("%Y-%m-%d")
    str_fin = (st.session_state.d_end + timedelta(days=1)).strftime("%Y-%m-%d")

    cal_options = {
        "timeZone": "UTC", 
        "initialDate": str_debut, 
        "validRange": {"start": str_debut, "end": str_fin},
        "headerToolbar": {"left": "prev,next", "center": "title", "right": ""},
        "selectable": True, "locale": "fr", "firstDay": 1, "height": "450px",
        "unselectAuto": False 
    }
    
    events = []
    for d in st.session_state[temp_abs_key]:
        if d not in st.session_state[temp_sel_key]:
            events.append({"title": "INDISPO", "start": d, "end": d, "color": "#DC2626"})
            
    for d in st.session_state[temp_sel_key]:
        events.append({"title": "SÉLECTION", "start": d, "end": d, "color": "#3B82F6"}) 

    res = calendar(events=events, options=cal_options, key=f"cal_{name}")

    if "select" in res:
        current_sel = str(res["select"])
        if current_sel != st.session_state.get(last_sel_key):
            st.session_state[last_sel_key] = current_sel
            
            start_str = res["select"].get("startStr", res["select"]["start"].split("T")[0])
            end_str = res["select"].get("endStr", res["select"]["end"].split("T")[0])
            
            start_dt = datetime.strptime(start_str.split("T")[0], "%Y-%m-%d")
            end_dt = datetime.strptime(end_str.split("T")[0], "%Y-%m-%d")
            
            if end_dt > start_dt:
                end_dt -= timedelta(days=1)
                
            new_days = pd.date_range(start_dt, end_dt).strftime("%Y-%m-%d").tolist()
            
            for d in new_days:
                st.session_state[temp_sel_key].add(d)
            st.rerun()

    col_act1, col_act2, col_act3 = st.columns(3)
    with col_act1:
        st.markdown('<div class="btn-indispo">', unsafe_allow_html=True)
        if st.button("🔴 Rendre Indisponible", use_container_width=True):
            for d in st.session_state[temp_sel_key]:
                if d not in st.session_state[temp_abs_key]:
                    st.session_state[temp_abs_key].append(d)
            st.session_state[temp_sel_key].clear() 
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
            
    with col_act2:
        st.markdown('<div class="btn-dispo">', unsafe_allow_html=True)
        if st.button("🟢 Rendre Disponible", use_container_width=True):
            for d in st.session_state[temp_sel_key]:
                if d in st.session_state[temp_abs_key]:
                    st.session_state[temp_abs_key].remove(d)
            st.session_state[temp_sel_key].clear() 
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_act3:
        st.markdown('<div class="btn-clear">', unsafe_allow_html=True)
        if st.button("⚪ Vider la sélection", use_container_width=True):
            st.session_state[temp_sel_key].clear()
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.write("---")
    v_pref = st.toggle("Coupler le vendredi au WE", value=st.session_state.merms_data[name]["pref_vendredi"])

    st.write("---")
    st.markdown('<div class="btn-valider">', unsafe_allow_html=True)
    if st.button("✅ CONFIRMER ET ENREGISTRER MES CHOIX", use_container_width=True):
        st.session_state.merms_data[name]["absences"] = st.session_state[temp_abs_key]
        st.session_state.merms_data[name]["pref_vendredi"] = v_pref
        del st.session_state[temp_abs_key]
        del st.session_state[temp_sel_key]
        sauvegarder_donnees(st.session_state.merms_data)
        st.session_state.modal_ouvert = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- MOTEUR ALGORITHMIQUE AVEC MULTI-ÉQUITÉ ---
def generer_planning(debut, fin):
    debut = pd.Timestamp(debut)
    fin = pd.Timestamp(fin)
    fr_holidays = holidays.France(years=[debut.year, fin.year])
    jours = pd.date_range(debut, fin)
    
    planning = {d: {"L1": "⚠️ À POURVOIR", "L2": "⚠️ À POURVOIR"} for d in jours}
    
    # Récupération de tous les compteurs
    scores = {m: v['score_cumule'] for m, v in st.session_state.merms_data.items()}
    scores_we = {m: v['score_we'] for m, v in st.session_state.merms_data.items()}
    nb_l1 = {m: v.get('nb_l1', 0) for m, v in st.session_state.merms_data.items()}
    nb_l2 = {m: v.get('nb_l2', 0) for m, v in st.session_state.merms_data.items()}
    assigned_dates = {m: set() for m in st.session_state.merms_data.keys()}
    
    def total_ast(m): return nb_l1[m] + nb_l2[m]
    
    def est_dispo(m, dates_list):
        return not any(dt.strftime("%Y-%m-%d") in st.session_state.merms_data[m]["absences"] for dt in dates_list)

    # 1. PASSE DES WEEK-ENDS
    for d in jours:
        if d.weekday() == 5: 
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
                
                # Tri Complexe : 1. Nbr WE -> 2. Points totaux -> 3. Nbr d'astreintes totales -> 4. Equilibre L1/L2
                if ligne == "L1":
                    choix = min(candidats, key=lambda x: (scores_we[x], scores[x], total_ast(x), nb_l1[x])) if candidats else None
                else:
                    choix = min(candidats, key=lambda x: (scores_we[x], scores[x], total_ast(x), nb_l2[x])) if candidats else None
                
                if choix:
                    scores_we[choix] += 1 
                    for wd in we_days:
                        planning[wd][ligne] = choix
                        assigned_dates[choix].add(wd)
                        scores[choix] += 3
                        if ligne == "L1": nb_l1[choix] += 1
                        else: nb_l2[choix] += 1
                    
                    if st.session_state.merms_data[choix]["pref_vendredi"] and d_fri >= debut:
                        planning[d_fri][ligne] = choix
                        assigned_dates[choix].add(d_fri)
                        scores[choix] += 1
                        if ligne == "L1": nb_l1[choix] += 1
                        else: nb_l2[choix] += 1
                        
    # 2. PASSE DE LA SEMAINE
    for d in jours:
        for ligne in ["L1", "L2"]:
            if planning[d][ligne] != "⚠️ À POURVOIR": continue
            
            candidats = []
            for m, v in st.session_state.merms_data.items():
                if (ligne == "L1" and 1 not in v["lignes"]) or (ligne == "L2" and 2 not in v["lignes"]): continue
                if ligne == "L2" and planning[d]["L1"] == m: continue
                if not est_dispo(m, [d]): continue
                
                # Règles de sécurité et quotas
                if (d - timedelta(days=1)) in assigned_dates[m] or (d + timedelta(days=1)) in assigned_dates[m]: continue
                week_num = d.isocalendar()[1]
                jours_semaine_ad = [ad for ad in assigned_dates[m] if ad.isocalendar()[1] == week_num]
                a_un_we = any(ad.weekday() >= 5 for ad in jours_semaine_ad)
                jours_en_semaine = [ad for ad in jours_semaine_ad if ad.weekday() < 5]
                
                if a_un_we and len(jours_en_semaine) >= 1: continue 
                elif not a_un_we and len(jours_en_semaine) >= 2: continue 
                            
                candidats.append(m)
                
            # Tri Complexe : 1. Points totaux -> 2. Nbr d'astreintes totales -> 3. Equilibre L1/L2
            if ligne == "L1":
                choix = min(candidats, key=lambda x: (scores[x], total_ast(x), nb_l1[x])) if candidats else "⚠️ À POURVOIR"
            else:
                choix = min(candidats, key=lambda x: (scores[x], total_ast(x), nb_l2[x])) if candidats else "⚠️ À POURVOIR"
                
            planning[d][ligne] = choix
            if choix != "⚠️ À POURVOIR":
                assigned_dates[choix].add(d)
                scores[choix] += 3 if (d.weekday() >= 5 or d in fr_holidays) else 1
                if ligne == "L1": nb_l1[choix] += 1
                else: nb_l2[choix] += 1

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
    return pd.DataFrame(resultat), scores, scores_we, nb_l1, nb_l2

# --- EXPORT EXCEL ---
def generer_excel_liste(df_planning, dict_scores, dict_scores_we, dict_nbl1, dict_nbl2):
    output = io.BytesIO()
    wb = Workbook()
    wb.remove(wb.active)

    fill_header = PatternFill(start_color="1E40AF", end_color="1E40AF", fill_type="solid")
    font_header = Font(color="FFFFFF", bold=True)
    border_thin = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    fill_we_ferie = PatternFill(start_color="F1F5F9", end_color="F1F5F9", fill_type="solid")

    df_planning['Annee'] = df_planning['DateObj'].dt.year
    df_planning['MoisNum'] = df_planning['DateObj'].dt.month

    for (annee, mois), group in df_planning.groupby(['Annee', 'MoisNum']):
        nom_mois = MOIS_FR[mois]
        ws_l1 = wb.create_sheet(title=f"L1 {nom_mois} {annee}")
        ws_l2 = wb.create_sheet(title=f"L2 {nom_mois} {annee}")
        en_tetes = ["Jour", "Date", "Astreinte Prévue", "Modification / Remplaçant"]
        
        for ws in [ws_l1, ws_l2]:
            ws.append(en_tetes)
            for col_num in range(1, 5):
                cell = ws.cell(row=1, column=col_num)
                cell.fill = fill_header
                cell.font = font_header
                cell.border = border_thin
            ws.column_dimensions['A'].width = 15
            ws.column_dimensions['B'].width = 15
            ws.column_dimensions['C'].width = 25
            ws.column_dimensions['D'].width = 40

        row_idx = 2
        for _, row in group.iterrows():
            d_str, j_str, type_jour = row['Date'], row['Jour'], row['Type']
            ws_l1.append([j_str, d_str, row['Ligne 1'], ""])
            ws_l2.append([j_str, d_str, row['Ligne 2'], ""])
            for ws in [ws_l1, ws_l2]:
                for col_num in range(1, 5):
                    cell = ws.cell(row=row_idx, column=col_num)
                    cell.border = border_thin
                    if type_jour == "FÉRIÉ/WE": cell.fill = fill_we_ferie
            row_idx += 1

    ws_scores = wb.create_sheet(title="Bilan Équité")
    ws_scores.append(["Manipulateur", "Total Points (Charge)", "Total Astreintes", "Total L1", "Total L2", "Nb Week-ends"])
    
    for idx, m in enumerate(dict_scores.keys(), 2):
        total_ast = dict_nbl1[m] + dict_nbl2[m]
        ws_scores.cell(row=idx, column=1, value=m).border = border_thin
        ws_scores.cell(row=idx, column=2, value=dict_scores[m]).border = border_thin
        ws_scores.cell(row=idx, column=3, value=total_ast).border = border_thin
        ws_scores.cell(row=idx, column=4, value=dict_nbl1[m]).border = border_thin
        ws_scores.cell(row=idx, column=5, value=dict_nbl2[m]).border = border_thin
        ws_scores.cell(row=idx, column=6, value=dict_scores_we[m]).border = border_thin
        
    for col in ['A', 'B', 'C', 'D', 'E', 'F']:
        ws_scores.column_dimensions[col].width = 20
        ws_scores.cell(row=1, column=ord(col)-64).fill = fill_header
        ws_scores.cell(row=1, column=ord(col)-64).font = font_header

    wb.save(output)
    return output.getvalue()

# --- INTERFACE PRINCIPALE ---
st.title("🏥 Planning de Radiologie Interventionnelle")

col_cfg, col_res = st.columns([1, 2.2])

with col_cfg:
    st.header("1. Période (Trimestre)")
    st.session_state.d_start = st.date_input("Début", datetime.now())
    st.session_state.d_end = st.date_input("Fin", datetime.now() + timedelta(days=90))

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
                st.session_state.merms_data[new_name] = {"lignes": lignes, "score_cumule": 0, "score_we": 0, "nb_l1": 0, "nb_l2": 0, "pref_vendredi": False, "absences": []}
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

with col_cfg:
    st.write("---")
    st.header("2. Desiderata")
    for merm in st.session_state.merms_data.keys():
        n_abs = len(st.session_state.merms_data[merm]["absences"])
        if st.button(f"👤 {merm} ({n_abs} j. posés)", key=f"btn_{merm}"):
            st.session_state.modal_ouvert = merm
            st.rerun() 

if st.session_state.modal_ouvert:
    modal_desiderata(st.session_state.modal_ouvert)

with col_res:
    st.header("3. Génération & Export")
    st.markdown('<div class="btn-generer">', unsafe_allow_html=True)
    if st.button("🚀 CALCULER LA RÉPARTITION ÉQUITABLE", use_container_width=True):
        df_resultat, scores_finaux, scores_we_finaux, nbl1_finaux, nbl2_finaux = generer_planning(st.session_state.d_start, st.session_state.d_end)
        st.session_state.planning_final = df_resultat
        st.session_state.scores_finaux = scores_finaux
        st.session_state.scores_we_finaux = scores_we_finaux
        st.session_state.nbl1_finaux = nbl1_finaux
        st.session_state.nbl2_finaux = nbl2_finaux
    st.markdown('</div>', unsafe_allow_html=True)

    if 'planning_final' in st.session_state:
        st.write("---")
        excel_data = generer_excel_liste(st.session_state.planning_final, st.session_state.scores_finaux, st.session_state.scores_we_finaux, st.session_state.nbl1_finaux, st.session_state.nbl2_finaux)
        nom_fichier = f"Planning_RI_{st.session_state.d_start.strftime('%m')}-{st.session_state.d_end.strftime('%m_%Y')}.xlsx"
        
        st.download_button(
            label="📥 TÉLÉCHARGEMENT EXCEL",
            data=excel_data,
            file_name=nom_fichier,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )
        st.write("---")
        
        onglet_l1, onglet_l2, onglet_stats = st.tabs(["📋 PLANNING LIGNE 1", "📋 PLANNING LIGNE 2", "📈 BILAN D'ÉQUITÉ"])
        with onglet_l1: st.table(st.session_state.planning_final[["Jour", "Date", "Ligne 1", "Type"]])
        with onglet_l2: st.table(st.session_state.planning_final[["Jour", "Date", "Ligne 2", "Type"]])
        with onglet_stats:
            st.info("L'algorithme équilibre dans l'ordre : 1. Nbr de Week-ends -> 2. Pénibilité (Points Globaux) -> 3. Nbr Astreintes Totales -> 4. Ratio L1/L2.")
            
            df_bilan = pd.DataFrame({
                "Total Points (Charge)": st.session_state.scores_finaux,
                "Total Astreintes (L1+L2)": {m: st.session_state.nbl1_finaux[m] + st.session_state.nbl2_finaux[m] for m in st.session_state.merms_data.keys()},
                "Total L1": st.session_state.nbl1_finaux,
                "Total L2": st.session_state.nbl2_finaux,
                "Nombre de Week-ends": st.session_state.scores_we_finaux
            })
            st.table(df_bilan)
            
            if st.button("💾 VALIDER CE TRIMESTRE ET SAUVEGARDER L'HISTORIQUE"):
                for m in st.session_state.scores_finaux:
                    st.session_state.merms_data[m]['score_cumule'] = st.session_state.scores_finaux[m]
                    st.session_state.merms_data[m]['score_we'] = st.session_state.scores_we_finaux[m]
                    st.session_state.merms_data[m]['nb_l1'] = st.session_state.nbl1_finaux[m]
                    st.session_state.merms_data[m]['nb_l2'] = st.session_state.nbl2_finaux[m]
                sauvegarder_donnees(st.session_state.merms_data)
                st.success("✅ Historique sauvegardé ! La prochaine répartition s'appuiera sur ces données pour corriger les écarts restants.")
