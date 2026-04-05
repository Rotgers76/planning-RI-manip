import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import holidays
from streamlit_calendar import calendar

# --- CONFIGURATION ---
st.set_page_config(page_title="Planning RI - Calendrier Expert", layout="wide")

JOURS_FR = {"Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi",
            "Thursday": "Jeudi", "Friday": "Vendredi", "Saturday": "Samedi", "Sunday": "Dimanche"}

# Style Haute Visibilité
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    .stButton>button { background-color: #0056b3; color: white !important; font-weight: bold; }
    .fc-event { cursor: pointer; } /* Style pour le calendrier */
    </style>
    """, unsafe_allow_html=True)

# --- INITIALISATION ---
if 'merms_data' not in st.session_state:
    noms = ["Lechevin L.", "Abdelaoui F.", "Laurin M.", "Cotton L.", "Bacquet V.", 
            "Leroux C.", "Brasseur O.", "Dupierris P.A.", "Talbaut V.", "Michel L.", "Dhondt F.", "Geffroy C. text_content"]
    st.session_state.merms_data = {
        name: {"lignes": [2] if "Dhondt" in name or "Geffroy" in name else [1, 2],
               "score_cumule": 0, "pref_vendredi": False, "absences": []} for name in noms
    }

# --- POPUP AVEC CALENDRIER GRAPHIQUE ---
@st.dialog("Calendrier des Desiderata", width="large")
def ouvrir_calendrier_graphique(name):
    st.write(f"### 📅 Absences de : **{name}**")
    st.info("Cliquez sur les jours ou faites glisser pour sélectionner une semaine. Les jours sélectionnés apparaissent en rouge.")

    # Configuration du calendrier interactif
    calendar_options = {
        "editable": True,
        "selectable": True,
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"},
        "locale": "fr",
    }
    
    # Transformation des absences stockées en événements pour le calendrier
    events = [{"title": "ABSENT", "start": d, "end": d, "color": "#FF4B4B"} 
              for d in st.session_state.merms_data[name]["absences"]]

    state = calendar(events=events, options=calendar_options, key=f"cal_{name}")

    # Si l'utilisateur sélectionne une plage (jour ou semaine)
    if "select" in state:
        start_select = state["select"]["start"].split("T")[0]
        end_select = (datetime.strptime(state["select"]["end"].split("T")[0], "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Générer la liste des jours entre start et end
        new_dates = pd.date_range(start_select, end_select).strftime("%Y-%m-%d").tolist()
        
        for d in new_dates:
            if d not in st.session_state.merms_data[name]["absences"]:
                st.session_state.merms_data[name]["absences"].append(d)
        st.rerun()

    if st.button("Effacer toutes mes absences"):
        st.session_state.merms_data[name]["absences"] = []
        st.rerun()
    
    st.write("---")
    v_opt = st.toggle("Coupler le vendredi à mes week-ends ?", value=st.session_state.merms_data[name]["pref_vendredi"])
    if st.button("Fermer et Valider"):
        st.session_state.merms_data[name]["pref_vendredi"] = v_opt
        st.rerun()

# --- MOTEUR D'ÉQUITÉ (Similaire au précédent mais gère les dates ISO) ---
def generer_planning_equitable(debut, fin):
    fr_holidays = holidays.France(years=[debut.year, fin.year])
    jours = pd.date_range(debut, fin)
    resultats = []
    scores_sim = {m: v['score_cumule'] for m, v in st.session_state.merms_data.items()}
    
    i = 0
    while i < len(jours):
        d = jours[i]
        d_str = d.strftime("%Y-%m-%d")
        is_we = d.weekday() >= 5 or d in fr_holidays
        
        bloc = [d]
        if d.weekday() == 5 and (i+1) < len(jours):
            bloc.append(jours[i+1])
            i += 1
            
        def est_dispo(m, dates):
            return not any(dt.strftime("%Y-%m-%d") in st.session_state.merms_data[m]["absences"] for dt in dates)

        dispos_l1 = [m for m in st.session_state.merms_data if 1 in st.session_state.merms_data[m]["lignes"] and est_dispo(m, bloc)]
        l1 = min(dispos_l1, key=lambda x: scores_sim[x]) if dispos_l1 else "⚠️ VIDE"
        
        dispos_l2 = [m for m in st.session_state.merms_data if m != l1 and est_dispo(m, bloc)]
        l2 = min(dispos_l2, key=lambda x: scores_sim[x]) if dispos_l2 else "⚠️ VIDE"

        poids = 3 if is_we else 1
        for db in bloc:
            if l1 != "⚠️ VIDE": scores_sim[l1] += poids
            if l2 != "⚠️ VIDE": scores_sim[l2] += poids
            resultats.append({"Date": db.strftime("%d/%m/%Y"), "Jour": JOURS_FR[db.strftime("%A")], "Ligne 1": l1, "Ligne 2": l2, "Type": "WE" if is_we else "Semaine"})
        i += 1
    return pd.DataFrame(resultats), scores_sim

# --- INTERFACE PRINCIPALE ---
st.title("🏥 RI Planning Pro : Calendrier Interactif")

col_left, col_right = st.columns([1, 2])

with col_left:
    st.header("1. Période")
    st.session_state.d_start = st.date_input("Du", datetime.now())
    st.session_state.d_end = st.date_input("Au", datetime.now() + timedelta(days=31))
    
    st.header("2. Desiderata")
    st.caption("Cliquez sur un nom pour ouvrir son calendrier visuel.")
    for merm in st.session_state.merms_data.keys():
        if st.button(f"📅 {merm}", key=f"btn_{merm}", use_container_width=True):
            ouvrir_calendrier_graphique(merm)

with col_right:
    st.header("3. Génération")
    if st.button("🔄 GÉNÉRER LE PLANNING ÉQUITABLE", use_container_width=True):
        df, sc = generer_planning_equitable(st.session_state.d_start, st.session_state.d_end)
        st.session_state.res_df, st.session_state.res_scores = df, sc

    if 'res_df' in st.session_state:
        t1, t2, t3 = st.tabs(["📋 Ligne 1", "📋 Ligne 2", "📊 Équité"])
        with t1: st.table(st.session_state.res_df[["Date", "Jour", "Ligne 1"]])
        with t2: st.table(st.session_state.res_df[["Date", "Jour", "Ligne 2"]])
        with t3: st.bar_chart(pd.DataFrame.from_dict(st.session_state.res_scores, orient='index'))
