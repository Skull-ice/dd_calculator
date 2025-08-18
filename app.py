import streamlit as st
import pandas as pd
from datetime import datetime
import sqlite3

# Connexion à la base de données SQLite pour persistance de l'historique
conn = sqlite3.connect('historique.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS historique
             (date TEXT, demandeur TEXT, source TEXT, montant_argus FLOAT, fret FLOAT, taux_cumule FLOAT, abattement TEXT, dd FLOAT, total FLOAT)''')
conn.commit()

# Titre de l'application
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

# Entrées utilisateur
st.subheader("Entrer les données")

# Utilisation de colonnes pour meilleure responsivité
col1, col2 = st.columns(2)

with col1:
    montant_argus = st.number_input("Montant Argus (en devise d'origine, ex. EUR)", min_value=0.0, value=0.0, step=0.01)
    fret = st.number_input("Fret (en XOF)", min_value=0.0, value=0.0, step=100.0)
    taux_cumule_percent = st.number_input("Taux cumulé (%)", min_value=0.0, value=0.0, step=0.01)

with col2:
    demandeur = st.text_input("Demandeur", "")
    source = st.text_input("Source", "")
    abattement_option = st.selectbox("Abattement", ["Avec abattement", "Sans abattement"])

# Bouton de calcul
if st.button("Calculer"):
    if not montant_argus or not fret or not taux_cumule_percent or not demandeur or not source:
        st.error("Veuillez remplir tous les champs.")
    else:
        # Conversion du taux en décimal
        taux_cumule = taux_cumule_percent / 100

        # Calcul de la valeur de base
        valeur_base = (montant_argus * 655.96) + fret

        # Détermination des taxes et du facteur d'abattement
        if abattement_option == "Avec abattement":
            facteur_abattement = 0.7
            taxes = 100250
            abattement_str = "Oui"
        else:
            facteur_abattement = 1.0
            taxes = 63610
            abattement_str = "Non"

        # Calcul DD et Total
        dd = valeur_base * facteur_abattement * taux_cumule
        total = dd + taxes

        # Affichage des résultats
        st.subheader("Résultats")
        st.write(f"**Valeur de base** : {valeur_base:,.2f} XOF")
        st.write(f"**Droits de douane (DD)** : {dd:,.2f} XOF")
        st.write(f"**Taxes** : {taxes:,.2f} XOF")
        st.write(f"**Total** : {total:,.2f} XOF")

        # Ajout à l'historique (SQLite pour persistance)
        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("INSERT INTO historique VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                  (current_date, demandeur, source, montant_argus, fret, taux_cumule_percent, abattement_str, dd, total))
        conn.commit()

# Affichage de l'historique dans la barre latérale à gauche (persistant via SQLite)
st.sidebar.subheader("Historique des Calculs")
df = pd.read_sql_query("SELECT * FROM historique", conn)
if not df.empty:
    st.sidebar.dataframe(df, use_container_width=True)

# Pas de bouton pour effacer l'historique (pour le maintenir)
# Si besoin de récupération, l'historique est stocké dans 'historique.db' et persiste même après relance

# Fermeture de la connexion
conn.close()