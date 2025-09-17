import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import sqlite3
import streamlit.components.v1 as components

# CSS pour style (caractères plus gros, bouton zoom)
st.markdown("""
    <style>
    .big-font { font-size: 18px !important; }  /* Zoom activé */
    .normal-font { font-size: 14px !important; }  /* Font par défaut */
    .stButton > button.zoom-btn {  /* Bouton zoom stylé */
        width: 180px;
        height: 60px;
        font-size: 22px !important;
        background-color: #4CAF50;
        color: white;
        border-radius: 8px;
    }
    .stDataFrame {  /* Style du dataframe */
        font-size: 14px;
    }
    .stDataFrame.big-font table {  /* Applique font-size au tableau */
        font-size: 18px !important;
    }
    </style>
""", unsafe_allow_html=True)

# Injecter GTM (Header)
gtm_head = """
<!-- Google Tag Manager -->
<script>(function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
})(window,document,'script','dataLayer','GTM-XXXXXX');</script>
<!-- End Google Tag Manager -->
"""
components.html(gtm_head, height=0)

# Injecter GTM (Body, noscript)
gtm_body = """
<!-- Google Tag Manager (noscript) -->
<noscript><iframe src="https://www.googletagmanager.com/ns.html?id=GTM-XXXXXX"
height="0" width="0" style="display:none;visibility:hidden"></iframe></noscript>
<!-- End Google Tag Manager (noscript) -->
"""
components.html(gtm_body, height=0)

# Connexion à SQLite avec migration
@st.cache_resource
def init_db():
    conn = sqlite3.connect('historique.db')
    c = conn.cursor()
    
    # Créer une table temporaire avec le nouveau schéma
    c.execute('''CREATE TABLE IF NOT EXISTS historique_temp
                 (date TEXT, demandeur TEXT, modele_vehicule TEXT, source TEXT, 
                  montant_argus FLOAT, fret FLOAT, taux_cumule FLOAT, abattement TEXT, 
                  valeur_base FLOAT, dd FLOAT, taxes FLOAT, total FLOAT)''')
    
    # Vérifier si l'ancienne table existe
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='historique'")
    if c.fetchone():
        # Copier les données de l'ancienne table vers la nouvelle
        c.execute('''INSERT INTO historique_temp (date, demandeur, source, montant_argus, 
                     fret, taux_cumule, abattement, dd, total)
                     SELECT date, demandeur, source, montant_argus, fret, taux_cumule, 
                            abattement, dd, total FROM historique''')
        # Ajouter valeur_base et taxes pour les anciens enregistrements (calcul rétroactif)
        c.execute("SELECT * FROM historique")
        for row in c.fetchall():
            date, demandeur, source, montant_argus, fret, taux_cumule, abattement, dd, total = row
            valeur_base = (montant_argus * 655.96) + fret
            taxes = 100250 if abattement == "Oui" else 63610
            c.execute('''UPDATE historique_temp 
                         SET valeur_base = ?, taxes = ? 
                         WHERE date = ? AND demandeur = ? AND source = ?''',
                      (valeur_base, taxes, date, demandeur, source))
        
        # Supprimer l'ancienne table et renommer la nouvelle
        c.execute("DROP TABLE historique")
        c.execute("ALTER TABLE historique_temp RENAME TO historique")
    
    # Créer la table finale si elle n'existe pas
    c.execute('''CREATE TABLE IF NOT EXISTS historique
                 (date TEXT, demandeur TEXT, modele_vehicule TEXT, source TEXT, 
                  montant_argus FLOAT, fret FLOAT, taux_cumule FLOAT, abattement TEXT, 
                  valeur_base FLOAT, dd FLOAT, taxes FLOAT, total FLOAT)''')
    conn.commit()
    return conn, c

conn, c = init_db()

# Fonction pour timestamp GMT+1
def get_gmt1_timestamp():
    utc_time = datetime.now(timezone.utc)
    gmt1_time = utc_time.astimezone(timezone(timedelta(hours=1)))
    return gmt1_time.strftime('%Y-%m-%d %H:%M:%S GMT+1')

# Titre
st.title("Calculateur de Droits de Douane")

# Explications
st.write("""
Cette application calcule les droits de douane selon la formule :
- Valeur de base = (Montant Argus * 655.96) + Fret
- Si avec abattement : DD = Valeur de base * 0.7 * Taux cumulé ; Taxes = 100250 XOF
- Si sans abattement : DD = Valeur de base * Taux cumulé ; Taxes = 63610 XOF
- Total = DD + Taxes
Entrez les valeurs ci-dessous et cliquez sur 'Calculer'. Le taux cumulé est en pourcentage (ex. 57.44 pour 57.44%).
""")

# Calcul préliminaire du Montant Argus
st.subheader("Calcul Préliminaire du Montant Argus (Optionnel)")
col_prelim1, col_prelim2 = st.columns(2)
with col_prelim1:
    petite_valeur = st.number_input("Petite Valeur", min_value=0.0, value=0.0, step=0.01)
with col_prelim2:
    grande_valeur = st.number_input("Grande Valeur", min_value=0.0, value=0.0, step=0.01)

# Calcul automatique de la moyenne si les deux valeurs sont fournies
montant_argus = 0.0
if petite_valeur > 0 and grande_valeur > 0:
    montant_argus = (petite_valeur + grande_valeur) / 2
    st.write(f"**Montant Argus calculé automatiquement** : {montant_argus:,.2f}")
else:
    st.write("Entrez les deux valeurs pour calculer la moyenne automatiquement.")

# Entrées utilisateur principales
st.subheader("Entrer les données")
col1, col2 = st.columns(2)

with col1:
    montant_argus = st.number_input("Montant Argus (en devise d'origine, ex. EUR)", min_value=0.0, value=montant_argus, step=0.01)
    fret = st.number_input("Fret (en XOF)", min_value=0.0, value=0.0, step=100.0)
    taux_cumule_percent = st.number_input("Taux cumulé (%)", min_value=0.0, value=0.0, step=0.01)

with col2:
    demandeur = st.text_input("Demandeur", "")
    modele_vehicule = st.text_input("Modèle du Véhicule", "")  # Avant source
    source = st.text_input("Source", "")
    abattement_option = st.selectbox("Abattement", ["Avec abattement", "Sans abattement"])

# Bouton de calcul
if st.button("Calculer"):
    components.html("<script>window.dataLayer.push({'event': 'calculate_click'});</script>", height=0)
    if not montant_argus or not fret or not taux_cumule_percent or not demandeur or not source:
        st.error("Veuillez remplir tous les champs obligatoires.")
    else:
        # Conversion du taux
        taux_cumule = taux_cumule_percent / 100
        valeur_base = (montant_argus * 655.96) + fret

        # Calcul avec/sans abattement
        if abattement_option == "Avec abattement":
            facteur_abattement = 0.7
            taxes = 100250
            abattement_str = "Oui"
        else:
            facteur_abattement = 1.0
            taxes = 63610
            abattement_str = "Non"

        dd = valeur_base * facteur_abattement * taux_cumule
        total = dd + taxes

        # Affichage résultats
        st.subheader("Résultats")
        st.write(f"**Valeur de base** : {valeur_base:,.2f} XOF")
        st.write(f"**Droits de douane (DD)** : {dd:,.2f} XOF")
        st.write(f"**Taxes** : {taxes:,.2f} XOF")
        st.write(f"**Total** : {total:,.2f} XOF")

        # Ajout à l'historique (GMT+1, avec modele_vehicule, valeur_base, taxes)
        current_date = get_gmt1_timestamp()
        c.execute("INSERT INTO historique VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (current_date, demandeur, modele_vehicule, source, montant_argus, fret, 
                   taux_cumule_percent, abattement_str, valeur_base, dd, taxes, total))
        conn.commit()

# Historique dans sidebar
st.sidebar.subheader("Historique des Calculs")
if 'zoom' not in st.session_state:
    st.session_state.zoom = False

# Bouton zoom
if st.sidebar.button("Zoom Historique", key="zoom_btn", help="Agrandir/réduire le texte"):
    components.html("<script>window.dataLayer.push({'event': 'zoom_click'});</script>", height=0)
    st.session_state.zoom = not st.session_state.zoom
    st.rerun()

# Afficher historique avec font-size dynamique
df = pd.read_sql_query("SELECT * FROM historique", conn)
if not df.empty:
    font_class = "big-font" if st.session_state.zoom else "normal-font"
    st.sidebar.markdown(f'<div class="{font_class}">', unsafe_allow_html=True)
    st.sidebar.dataframe(df, use_container_width=True)
    st.sidebar.markdown('</div>', unsafe_allow_html=True)

# Bouton reset DB (décommenter si besoin pour recréer la table)
# if st.sidebar.button("Reset Historique (Supprime tout)"):
#     c.execute("DROP TABLE IF EXISTS historique")
#     c.execute('''CREATE TABLE historique
#                  (date TEXT, demandeur TEXT, modele_vehicule TEXT, source TEXT, 
#                   montant_argus FLOAT, fret FLOAT, taux_cumule FLOAT, abattement TEXT, 
#                   valeur_base FLOAT, dd FLOAT, taxes FLOAT, total FLOAT)''')
#     conn.commit()
#     st.sidebar.success("Historique réinitialisé.")

# Fermer connexion
conn.close()
