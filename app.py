import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import holidays

# --- CONFIGURATION ---
st.set_page_config(page_title="Planning RI - Haute Visibilité", layout="wide")

# Traduction manuelle pour garantir le français partout (plus fiable que locale)
JOURS_FR = {
    "Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi",
    "Thursday": "Jeudi", "Friday": "Vendredi", "Saturday": "Samedi", "Sunday": "Dimanche"
}

# Style Haute Visibilité (Noir sur Blanc / Bleu Roi)
st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF; }
    h1, h2 { color: #1A202C !important; font-weight: 800; border-left: 5px solid #0056b3; padding-left: 15px; }
    .stButton>button { 
        background-color: #0056b3; 
        color: white !important; 
        font-weight: bold; 
        border-radius: 4px;
        border: 1px solid #003d7a;
    }
    .stDataFrame { border: 1px solid #E2E8F0; }
    /* Amélioration du contraste des tableaux */
    [data-testid="stTable"] td { color: #1A202C !important; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

# --- INITIALISATION DE L'ÉQUIPE ---
if 'merms_data' not in st.session_state:
    noms = [
        "Lechevin L.", "Abdelaoui F.", "Laurin M.", "Cotton L.", 
        "Bacquet V.", "Leroux C.", "Brasseur O.", "Dupierris P.A.", 
        "Talbaut V.", "Michel L.", "Dhondt F.", "Geffroy C."
    ]
    st.session_state.merms_data = {
        name: {
            "lignes": [2] if name in ["Dhondt F.", "Geffroy C."] else [1, 2],
            "score_cumule": 0,
            "pref_vendredi": False,
            "absences": []
        } for name in noms
    }

# --- POPUP DESIDERATA (DIALOG) ---
@st.dialog("Saisie des Desiderata")
def ouvrir_config_perso(name):
    st.write(f"### 👤 Paramètres : {name}")
    
    # Calendrier de sélection multiple
    absences = st.multiselect(
        "Indiquez vos jours d'indisponibilité (vacances/repos) :",
        pd.date_range(st.session_state.d_start, st.session_state.d_end).tolist(),
        format_func=lambda x: x.strftime("%d/%m/%Y"),
        default=st.session_state.merms_data[name]["absences"]
    )
    
    # Option Vendredi
    v_opt = st.toggle("Coupler le vendredi à mes week-ends ?", 
                     value=st.session_state.merms_data[name]["pref_vendredi"])
    
    if st.button("Enregistrer les modifications"):
        st.session_state.merms_data[name]["absences"] = absences
        st.session_state.merms_data[name]["pref_vendredi"] = v_opt
        st.rerun()

# --- MOTEUR D'ÉQUITÉ FRANÇAIS ---
def generer_planning_equitable(debut, fin):
    fr_holidays = holidays.France(years=[debut.year, fin.year])
    jours = pd.date_range(debut, fin)
    resultats = []
    
    # Copie des scores pour la simulation
    scores_sim = {m: v['score_cumule'] for m, v in st.session_state.merms_data.items()}
    
    i = 0
    while i < len(jours):
        d = jours[i]
        is_fete = d in fr_holidays
        is_we = d.weekday() >= 5 or is_fete
        
        # Définition du bloc pour l'équité (Samedi+Dimanche ou Vendredi+Samedi+Dimanche)
        bloc_dates = [d]
        if d.weekday() == 5 and (i + 1) < len(jours): # Samedi
            bloc_dates.append(jours[i+1])
            i += 1
            
        # Filtrage des agents disponibles sur tout le bloc
        def est_dispo(m, dates):
            return not any(jd in st.session_state.merms_data[m]["absences"] for jd in dates)

        # Attribution Ligne 1 (Sauf Dhondt et Geffroy)
        dispos_l1 = [m for m in st.session_state.merms_data if 1 in st.session_state.merms_data[m]["lignes"] and est_dispo(m, bloc_dates)]
        l1 = min(dispos_l1, key=lambda x: scores_sim[x]) if dispos_l1 else "⚠️ À DÉFINIR"
        
        # Attribution Ligne 2
        dispos_l2 = [m for m in st.session_state.merms_data if m != l1 and est_dispo(m, bloc_dates)]
        l2 = min(dispos_l2, key=lambda x: scores_sim[x]) if dispos_l2 else "⚠️ À DÉFINIR"

        # Calcul des points (Semaine=1, WE/Férié=3)
        poids = 3 if is_we else 1
        
        for date_b in bloc_dates:
            if l1 != "⚠️ À DÉFINIR": scores_sim[l1] += poids
            if l2 != "⚠️ À DÉFINIR": scores_sim[l2] += poids
            
            resultats.append({
                "Date": date_b.strftime("%d/%m/%Y"),
                "Jour": JOURS_FR[date_b.strftime("%A")],
                "Ligne d'Astreinte 1": l1,
                "Ligne d'Astreinte 2": l2,
                "Type": "FÉRIÉ" if date_b in fr_holidays else ("WEEK-END" if date_b.weekday() >= 5 else "SEMAINE")
            })
        i += 1
        
    return pd.DataFrame(resultats), scores_sim

# --- INTERFACE ---
st.title("📅 Planning de Radiologie Interventionnelle")

col_params, col_main = st.columns([1, 2])

with col_params:
    st.header("1. Période")
    st.session_state.d_start = st.date_input("Date de début", datetime.now())
    st.session_state.d_end = st.date_input("Date de fin", datetime.now() + timedelta(days=31))
    
    st.write("---")
    st.header("2. Desiderata")
    st.info("Cliquez sur un nom pour ouvrir son calendrier.")
    for merm in st.session_state.merms_data.keys():
        if st.button(f"👤 {merm}", key=f"btn_{merm}", use_container_width=True):
            ouvrir_config_perso(merm)

with col_main:
    st.header("3. Génération du Planning")
    if st.button("🔄 CALCULER LA RÉPARTITION ÉQUITABLE", use_container_width=True):
        df_final, scores_finaux = generer_planning_equitable(st.session_state.d_start, st.session_state.d_end)
        st.session_state.res_df = df_final
        st.session_state.res_scores = scores_finaux

    if 'res_df' in st.session_state:
        ong1, ong2, ong3 = st.tabs(["📋 LIGNE 1", "📋 LIGNE 2", "📊 ÉQUITÉ (POINTS)"])
        
        with ong1:
            st.table(st.session_state.res_df[["Date", "Jour", "Ligne d'Astreinte 1", "Type"]])
        with ong2:
            st.table(st.session_state.res_df[["Date", "Jour", "Ligne d'Astreinte 2", "Type"]])
        with ong3:
            st.subheader("Compteur d'équité annuel")
            df_bilan = pd.DataFrame.from_dict(st.session_state.res_scores, orient='index', columns=['Points'])
            st.bar_chart(df_bilan)
            if st.button("💾 Valider et Enregistrer ces scores"):
                for m in st.session_state.res_scores:
                    st.session_state.merms_data[m]['score_cumule'] = st.session_state.res_scores[m]
                st.success("Les scores ont été enregistrés pour la prochaine génération.")
