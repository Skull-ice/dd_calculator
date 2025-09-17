import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import sqlite3

# Fonction pour initialiser la DB
def init_db():
    conn = sqlite3.connect('historique.db', check_same_thread=False)
    c = conn.cursor()
    
    # Schéma cible
    expected_columns = ['date', 'modele_vehicule', 'source', 'demandeur', 'total']
    
    # Vérifier si la table existe
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='historique'")
    if c.fetchone():
        # Vérifier les colonnes actuelles
        c.execute("PRAGMA table_info(historique)")
        current_columns = [info[1] for info in c.fetchall()]
        
        # Si schéma incompatible, recréer la table
        if set(current_columns) != set(expected_columns):
            c.execute("DROP TABLE IF EXISTS historique")
            c.execute('''CREATE TABLE historique
                         (date TEXT, modele_vehicule TEXT, source TEXT, demandeur TEXT, total FLOAT)''')
    else:
        # Créer la table si elle n'existe pas
        c.execute('''CREATE TABLE historique
                     (date TEXT, modele_vehicule TEXT, source TEXT, demandeur TEXT, total FLOAT)''')
    
    conn.commit()
    conn.close()

# Appeler init_db au démarrage
init_db()

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
st.subheader("Détermination du montant initial")
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
        else:
            facteur_abattement = 1.0
            taxes = 63610

        dd = valeur_base * facteur_abattement * taux_cumule
        total = dd + taxes

        # Affichage résultats
        st.subheader("Résultats")
        st.write(f"**Valeur de base** : {valeur_base:,.2f} XOF")
        st.write(f"**Droits de douane (DD)** : {dd:,.2f} XOF")
        st.write(f"**Taxes** : {taxes:,.2f} XOF")
        st.write(f"**Total** : {total:,.2f} XOF")

        # Ajout à l'historique
        conn = sqlite3.connect('historique.db', check_same_thread=False)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO historique (date, modele_vehicule, source, demandeur, total) VALUES (?, ?, ?, ?, ?)",
                      (get_gmt1_timestamp(), modele_vehicule, source, demandeur, total))
            conn.commit()
        except sqlite3.ProgrammingError as e:
            st.error(f"Erreur d'insertion dans l'historique : {str(e)}")
        finally:
            conn.close()

# Historique dans sidebar
st.sidebar.subheader("Historique des Calculs")
conn = sqlite3.connect('historique.db', check_same_thread=False)
c = conn.cursor()
try:
    df = pd.read_sql_query("SELECT * FROM historique", conn)
    if not df.empty:
        st.sidebar.dataframe(df, use_container_width=True)
    else:
        st.sidebar.write("Aucun calcul dans l'historique.")
except sqlite3.ProgrammingError as e:
    st.sidebar.error(f"Erreur de lecture de l'historique : {str(e)}")
finally:
    conn.close()
