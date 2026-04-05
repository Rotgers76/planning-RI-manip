import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import holidays
from streamlit_calendar import calendar

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(page_title="RI Planning Pro", layout="wide")

# --- THÈME MODERNE & ERGONOMIQUE (CSS) ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; color: #1E293B; }
    .stApp { background-color: #F8FAFC; }
    
    /* Titres */
    h1 { color: #0F172A; font-weight: 800; border-bottom: 3px solid #3B82F6; padding-bottom: 10px; }
    h2 { color: #334155; font-weight: 600; margin-top: 2rem; }

    /* Cartes Manipulateurs */
    .stButton>button {
        width: 100%; border-radius: 10px; border: 1px solid #E2E8F0;
        background-color: white; color: #475569; padding: 0.5rem;
        transition: all 0.2s; text-align: left;
    }
    .stButton>button:hover {
        border-color: #3B82F6; color: #3B82F6; background-color: #EFF6FF;
    }

    /* Bouton de Validation Vert */
    .btn-save button {
        background-color: #10B981 !important; color: white !important;
        border: none !important; font-weight: bold;
    }

    /* Onglets */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background-color: #F1F5F9; padding: 5px; border-radius: 10px; }
    .stTabs [data-baseweb="tab"] { border-radius: 7px; background-color: transparent; }
    .stTabs [aria-selected="true"] { background-color: white !important; color: #3B82F6 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- TRADUCTIONS ---
JOURS_FR = {"Monday": "Lundi", "Tuesday": "Mardi", "Wednesday": "Mercredi",
            "Thursday": "Jeudi", "Friday": "Vendredi", "Saturday": "Samedi", "Sunday": "Dimanche"}

# --- INITIALISATION DES DONNÉES ---
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

# --- FENÊTRE POPUP : DESIDERATA ---
@st.dialog("Calendrier des Desiderata", width="large")
def modal_desiderata(name):
    st.write(f"### 👤 Agent : {name}")
    st.caption("Sélectionnez vos jours (clic) ou semaines (glisser). Les absences s'affichent en rouge.")

    # Clé temporaire pour ne pas valider tant qu'on n'a pas cliqué sur le bouton
    temp_key = f"temp_{name}"
    if temp_key not in st.session_state:
        st.session_state[temp_key] = st.session_state.merms_data[name]["absences"].copy()

    cal_options = {
        "headerToolbar": {"left": "prev,next today", "center": "title", "right": "dayGridMonth"},
        "selectable": True, "locale": "fr", "height": "400px",
    }
    
    events = [{"title": "ABSENT", "start": d, "end": d, "color": "#EF4444"} for d in st.session_state[temp_key]]
    
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
        if st.button("🗑️ Effacer les choix", use_container_width=True):
            st.session_state[temp_key] = []
            st.rerun()
    with col_b:
        v_pref = st.toggle("Coupler le vendredi au WE", value=st.session_state.merms_data[name]["pref_vendredi"])

    st.write("---")
    st.markdown('<div class="btn-save">', unsafe_allow_html=True)
    if st.button("✅ ENREGISTRER ET FERMER", use_container_width=True):
        st.session_state.merms_data[name]["absences"] = st.session_state[temp_key]
        st.session_state.merms_data[name]["pref_vendredi"] = v_pref
        del st.session_state[temp_key]
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- MOTEUR D'ÉQUITÉ ---
def generer_planning(debut, fin):
    fr_holidays = holidays.France(years=[debut.year, fin.year])
    jours = pd.date_range(debut, fin)
    planning = []
    scores = {m: v['score_cumule'] for m, v in st.session_state.merms_data.items()}
    
    idx = 0
    while idx < len(jours):
        d = jours[idx]
        bloc = [d]
        is_we_fete = d.weekday() >= 5 or d in fr_holidays
        
        # Gestion des blocs WE (Samedi + Dimanche)
        if d.weekday() == 5 and (idx + 1) < len(jours):
            bloc.append(jours[idx+1])
            idx += 1
            
        def dispo(m, dates):
            return not any(dt.strftime("%Y-%m-%d") in st.session_state.merms_data[m]["absences"] for dt in dates)

        # Attribution L1
        cand_l1 = [m for m in st.session_state.merms_data if 1 in st.session_state.merms_data[m]["lignes"] and dispo(m, bloc)]
        l1 = min(cand_l1, key=lambda x: scores[x]) if cand_l1 else "⚠️ VIDE"
        
        # Attribution L2
        cand_l2 = [m for m in st.session_state.merms_data if m != l1 and dispo(m, bloc)]
        l2 = min(cand_l2, key=lambda x: scores[x]) if cand_l2 else "⚠️ VIDE"

        poids = 3 if is_we_fete else 1
        for db in bloc:
            if l1 != "⚠️ VIDE": scores[l1] += poids
            if l2 != "⚠️ VIDE": scores[l2] += poids
            planning.append({
                "Date": db.strftime("%d/%m/%Y"),
                "Jour": JOURS_FR[db.strftime("%A")],
                "Ligne 1": l1, "Ligne 2": l2,
                "Type": "FÉRIÉ/WE" if (db.weekday() >= 5 or db in fr_holidays) else "Semaine"
            })
        idx += 1
    return pd.DataFrame(planning), scores

# --- INTERFACE PRINCIPALE ---
st.title("🏥 Planning de Radiologie Interventionnelle")

col_side, col_main = st.columns([1, 2.5])

with col_side:
    st.header("⚙️ Configuration")
    d1 = st.date_input("Début", datetime.now())
    d2 = st.date_input("Fin", datetime.now() + timedelta(days=31))
    
    st.write("---")
    st.write("**Desiderata des manipulateurs**")
    for merm in st.session_state.merms_data.keys():
        n_abs = len(st.session_state.merms_data[merm]["absences"])
        if st.button(f"👤 {merm} ({n_abs}j)", key=f"btn_{merm}"):
            modal_desiderata(merm)

with col_main:
    st.header("📊 Planning d'Astreintes")
    if st.button("🚀 GÉNÉRER LA RÉPARTITION ÉQUITABLE", type="primary", use_container_width=True):
        res_df, res_scores = generer_planning(d1, d2)
        st.session_state.final_df = res_df
        st.session_state.final_scores = res_scores

    if 'final_df' in st.session_state:
        t1, t2, t3 = st.tabs(["📋 LIGNE 1", "📋 LIGNE 2", "📈 ÉQUITÉ"])
        with t1: st.table(st.session_state.final_df[["Date", "Jour", "Ligne 1", "Type"]])
        with t2: st.table(st.session_state.final_df[["Date", "Jour", "Ligne 2", "Type"]])
        with t3:
            st.write("Points cumulés (Semaine: 1, WE: 3)")
            st.bar_chart(pd.DataFrame.from_dict(st.session_state.final_scores, orient='index'))
            if st.button("💾 Enregistrer ces scores pour le futur"):
                for m in st.session_state.final_scores:
                    st.session_state.merms_data[m]['score_cumule'] = st.session_state.final_scores[m]
                st.success("Base de données mise à jour.")
