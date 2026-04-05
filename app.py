import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import holidays
from streamlit_calendar import calendar
import json
import os
import io

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

# --- SYSTÈME DE SAUVEGARDE LOCALE (MÉMOIRE APP) ---
FICHIER_SAUVEGARDE = "equipe_ri.json"

def charger_donnees():
    if os.path.exists(FICHIER_SAUVEGARDE):
        with open(FICHIER_SAUVEGARDE, "r", encoding="utf-8") as f:
            return json.load(f)
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
                "score_cumule": 0, "pref_vendredi": False, "absences": []
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
        "selectable": True, 
        "locale": "fr", 
        "firstDay": 1, 
        "height": "450px"
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
        v_pref = st.toggle("Coupler le vendredi", value=st.session_state.merms_data[name]["pref_vendredi"])

    st.write("---")
    st.markdown('<div class="btn-valider">', unsafe_allow_html=True)
    if st.button("✅ CONFIRMER ET ENREGISTRER MES CHOIX", use_container_width=True):
        st.session_state.merms_data[name]["absences"] = st.session_state[temp_key]
        st.session_state.merms_data[name]["pref_vendredi"] = v_pref
        del st.session_state[temp_key]
        sauvegarder_donnees(st.session_state.merms_data)
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- MOTEUR ALGORITHMIQUE D'ÉQUITÉ ---
def generer_planning(debut, fin):
    fr_holidays = holidays.France(years=[debut.year, fin.year])
    jours = pd.date_range(debut, fin)
    planning = []
    scores = {m: v['score_cumule'] for m, v in st.session_state.merms_data.items()}
    
    idx = 0
    while idx < len(jours):
        d = jours[idx]
        is_we_fete = d.weekday() >= 5 or d in fr_holidays
        bloc = [d]
        if d.weekday() == 5 and (idx + 1) < len(jours):
            bloc.append(jours[idx+1]); idx += 1
            
        def est_dispo(m, dates_bloc):
            return not any(dt.strftime("%Y-%m-%d") in st.session_state.merms_data[m]["absences"] for dt in dates_bloc)

        cand_l1 = [m for m, v in st.session_state.merms_data.items() if 1 in v["lignes"] and est_dispo(m, bloc)]
        l1 = min(cand_l1, key=lambda x: scores[x]) if cand_l1 else "⚠️ À POURVOIR"
        
        cand_l2 = [m for m, v in st.session_state.merms_data.items() if m != l1 and 2 in v["lignes"] and est_dispo(m, bloc)]
        l2 = min(cand_l2, key=lambda x: scores[x]) if cand_l2 else "⚠️ À POURVOIR"

        poids = 3 if is_we_fete else 1
        for jb in bloc:
            planning.append({"Date": jb.strftime("%d/%m/%Y"), "Jour": JOURS_FR[jb.strftime("%A")], 
                             "Ligne 1": l1, "Ligne 2": l2, "Type": "FÉRIÉ/WE" if (jb.weekday() >= 5 or jb in fr_holidays) else "SEMAINE"})
            if l1 != "⚠️ À POURVOIR": scores[l1] += poids
            if l2 != "⚠️ À POURVOIR": scores[l2] += poids
        idx += 1
    return pd.DataFrame(planning), scores

# --- FONCTION D'EXPORT EXCEL ---
def generer_excel(df_planning, dict_scores):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_planning.to_excel(writer, index=False, sheet_name="Planning Trimestriel")
        df_scores = pd.DataFrame.from_dict(dict_scores, orient='index', columns=['Points Cumulés'])
        df_scores.to_excel(writer, sheet_name="Scores Équité")
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
                st.session_state.merms_data[new_name] = {"lignes": lignes, "score_cumule": 0, "pref_vendredi": False, "absences": []}
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
    # Date par défaut modifiée pour couvrir ~90 jours (3 mois)
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
        df_resultat, scores_finaux = generer_planning(d_start, d_end)
        st.session_state.planning_final = df_resultat
        st.session_state.scores_finaux = scores_finaux
    st.markdown('</div>', unsafe_allow_html=True)

    if 'planning_final' in st.session_state:
        st.write("---")
        # Format du nom de fichier : ex Planning_RI_01-03_2026.xlsx
        excel_data = generer_excel(st.session_state.planning_final, st.session_state.scores_finaux)
        nom_fichier = f"Planning_RI_{d_start.strftime('%m')}-{d_end.strftime('%m_%Y')}.xlsx"
        
        st.download_button(
            label="📥 TÉLÉCHARGEMENT EXCEL (TRIMESTRE)",
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
            st.subheader("Bilan des points attribués sur la période")
            st.info("Le système équilibre automatiquement le planning. (Semaine = 1 pt | WE & Férié = 3 pts)")
            df_scores = pd.DataFrame.from_dict(st.session_state.scores_finaux, orient='index', columns=['Points Cumulés'])
            st.bar_chart(df_scores)
            
            st.write("---")
            if st.button("💾 VALIDER CE TRIMESTRE ET SAUVEGARDER LES SCORES"):
                for m in st.session_state.scores_finaux:
                    st.session_state.merms_data[m]['score_cumule'] = st.session_state.scores_finaux[m]
                sauvegarder_donnees(st.session_state.merms_data)
                st.success("✅ Base de données mise à jour ! Le calcul du prochain trimestre prendra en compte cet historique.")
