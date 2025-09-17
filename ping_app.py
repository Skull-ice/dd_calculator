import requests
     import time

     url = "https://tonapp.streamlit.app"  # Remplace par l'URL de ton app
     while True:
         try:
             response = requests.get(url)
             print(f"Ping OK: {response.status_code}")
         except Exception as e:
             print(f"Erreur ping: {e}")
         time.sleep(10800)  # 3h