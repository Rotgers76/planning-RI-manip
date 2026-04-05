import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import holidays
import locale

# --- CONFIGURATION DE L'INTERFACE ---
st.set_page_config(page_title="Planning RI Nordik", layout="wide")

# Style Scandinave Intégré
st.markdown("""
    <style>
    .stApp { background-color: #ECEFF4; } /* Fond gris très clair */
    h1, h2 { color: #2E3440; font-family: 'Helvetica'; }
    .stHeader { background-color: #5E81AC; color: white; padding: 10px; border-radius: 5px; }
    .css-1544893 { background-color: #D8DEE9; } /* Sidebar */
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; background-color: white; border-radius: 5px 5px 0 0; }
    </style>
    """, unsafe_allow_html=True)

# --- DONNÉES INTÉGRÉES (Pas besoin de fichiers externes) ---
if 'merms_data' not in st.session_state:
    st.session_state.merms_data = {
        "Lechevin L.": {"lignes": [1, 2], "score": 0},
        "Abdelaoui F.": {"lignes": [1, 2], "score": 0},
        "Laurin M.": {"lignes": [1, 2], "score": 0},
        "Cotton L.": {"lignes": [1, 2], "score": 0},
        "Bacquet V.": {"lignes": [1, 2], "score": 0},
        "Leroux C.": {"lignes": [1, 2], "score": 0},
        "Brasseur O.": {"lignes": [1, 2], "score": 0},
        "Dupierris P.A.": {"lignes": [1, 2], "score": 0},
        "Talbaut V.": {"lignes": [1, 2], "score": 0},
        "Michel L.": {"lignes": [1, 2], "score": 0},
        "Dhondt F.": {"lignes": [2], "score": 0},
        "Geffroy C.": {"lignes": [2], "score": 0}
    }

# --- FONCTION DE GÉNÉRATION ---
def generer_planning(debut, fin, abs_dict, couplage_vendredi):
    fr_holidays = holidays.France(years=[debut.year, fin.year])
    jours = pd.date_range(debut, fin)
    planning = []
    
    # On travaille sur une copie locale des scores pour l'équité du mois
    temp_scores = {m: st.session_state.merms_data[m]['score'] for m in st.session_state.merms_data}
    
    current_idx = 0
    while current_idx < len(jours):
        jour = jours[current_idx]
        
        # Identification du bloc (Week-end ou Journée seule)
        is_we = jour.weekday() >= 5 or jour in fr_holidays
        bloc = [jour]
        
        # Logique de couplage
        if couplage_vendredi and jour.weekday() == 4: # Vendredi
            if current_idx + 2 < len(jours):
                bloc = [jours[current_idx], jours[current_idx+1], jours[current_idx+2]]
                current_idx += 2
        elif jour.weekday() == 5: # Samedi
            if current_idx + 1 < len(jours):
                bloc = [jours[current_idx], jours[current_idx+1]]
                current_idx += 1

        # Attribution Ligne 1
        dispo_l1 = [m for m, v in st.session_state.merms_data.items() 
                    if 1 in v['lignes'] and not any(d in abs_dict.get(m, []) for d in bloc)]
        l1 = min(dispo_l1, key=lambda x: temp_scores[x]) if dispo_l1 else "⚠️ À FIXER"
        
        # Attribution Ligne 2
        dispo_l2 = [m for m, v in st.session_state.merms_data.items() 
                    if 2 in v['lignes'] and m != l1 and not any(d in abs_dict.get(m, []) for d in bloc)]
        l2 = min(dispo_l2, key=lambda x: temp_scores[x]) if dispo_l2 else "⚠️ À FIXER"

        # Remplissage
        for d in bloc:
            poids = 3 if (d.weekday() >= 5 or d in fr_holidays) else 1
            if l1 != "⚠️ À FIXER": temp_scores[l1] += poids
            if l2 != "⚠️ À FIXER": temp_scores[l2] += poids
            
            planning.append({
                "Date": d.strftime("%d/%m/%Y"),
                "Jour": d.strftime("%A"),
                "Ligne 1": l1,
                "Ligne 2": l2,
                "Férié": "Oui" if d in fr_holidays else "Non"
            })
        current_idx += 1
        
    return pd.DataFrame(planning), temp_scores

# --- INTERFACE PRINCIPALE ---
st.title("❄️ Nordik Planning RI")
st.write("Gestion des astreintes sans import de fichiers.")

with st.sidebar:
    st.header("⚙️ Configuration")
    d_start = st.date_input("Date de début", datetime.now())
    d_end = st.date_input("Date de fin", datetime.now() + timedelta(days=30))
    c_vendredi = st.checkbox("Coupler Vendredi au WE", value=True)
    
    if st.button("🗑️ Réinitialiser les scores"):
        for m in st.session_state.merms_data: st.session_state.merms_data[m]['score'] = 0
        st.success("Scores remis à zéro")

# Section Desiderata
st.header("📅 Calendrier des Desiderata")
expander = st.expander("Saisir les absences et vacances")
abs_input = {}
with expander:
    cols = st.columns(3)
    for i, merm in enumerate(st.session_state.merms_data.keys()):
        with cols[i % 3]:
            abs_input[merm] = st.multiselect(f"{merm}", 
                                             pd.date_range(d_start, d_end).tolist(),
                                             format_func=lambda x: x.strftime("%d/%m"),
                                             key=f"abs_{merm}")

# Génération
if st.button("💎 Générer le Planning"):
    df, nouveaux_scores = generer_planning(d_start, d_end, abs_input, c_vendredi)
    
    tab1, tab2, tab3 = st.tabs(["📋 Ligne d'Astreinte 1", "📋 Ligne d'Astreinte 2", "📊 Équité"])
    
    with tab1:
        st.subheader("Planning Ligne 1")
        st.dataframe(df[["Date", "Jour", "Ligne 1", "Férié"]], use_container_width=True)
        
    with tab2:
        st.subheader("Planning Ligne 2")
        st.dataframe(df[["Date", "Jour", "Ligne 2", "Férié"]], use_container_width=True)
        
    with tab3:
        st.subheader("Compteurs de points (Équité)")
        st.write("Semaine = 1pt | WE & Férié = 3pts")
        st.table(pd.DataFrame.from_dict(nouveaux_scores, orient='index', columns=['Points cumulés']))
        if st.button("💾 Enregistrer ces scores pour le mois prochain"):
            for m in nouveaux_scores: st.session_state.merms_data[m]['score'] = nouveaux_scores[m]
            st.success("Scores enregistrés !")