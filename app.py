import requests
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import streamlit as st
import time
import re
from collections import Counter

CLIENT_ID = st.secrets["spotify"]["client_id"]
CLIENT_SECRET = st.secrets["spotify"]["client_secret"]

@st.cache_data
def obtener_datos():
    auth_response = requests.post('https://accounts.spotify.com/api/token', {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
    })
    access_token = auth_response.json()['access_token']
    headers = {'Authorization': f'Bearer {access_token}'}
    BASE_URL = 'https://api.spotify.com/v1/'

    # Buscar artista Radiohead
    search_url = BASE_URL + 'search'
    params = {'q': 'Radiohead', 'type': 'artist'}
    response = requests.get(search_url, headers=headers, params=params)
    artist_id = response.json()['artists']['items'][0]['id']

    # Álbumes de estudio oficiales
    studio_albums = [
        'Pablo Honey', 'The Bends', 'OK Computer', 'Kid A', 'Amnesiac',
        'Hail to the Thief', 'In Rainbows', 'The King of Limbs', 'A Moon Shaped Pool'
    ]

    r = requests.get(BASE_URL + f'artists/{artist_id}/albums', headers=headers, params={
        'include_groups': 'album',
        'limit': 50
    })
    albums_raw = r.json()['items']

    # Elegir versión más antigua por nombre
    filtered_albums = {}
    for album in albums_raw:
        name = album['name']
        if name in studio_albums:
            if name not in filtered_albums or album['release_date'] < filtered_albums[name]['release_date']:
                filtered_albums[name] = album
    albums_filtered = list(filtered_albums.values())

    # Obtener canciones
    tracks = []
    for album in albums_filtered:
        r = requests.get(BASE_URL + f'albums/{album["id"]}/tracks', headers=headers)
        for track in r.json()['items']:
            tracks.append({'album': album['name'], 'track_name': track['name']})

    # Obtener letras
    base_lyrics_url = 'https://api.lyrics.ovh/v1'
    lyrics_data = []
    for track in tracks:
        name = re.sub(r'\(.*?\)|- .*', '', track['track_name']).strip()
        r = requests.get(f'{base_lyrics_url}/Radiohead/{name}')
        lyrics = r.json().get('lyrics', '') if r.status_code == 200 else ''
        lyrics_data.append({
            'album': track['album'],
            'track_name': name,
            'lyrics': lyrics
        })
        time.sleep(0.5)

    return pd.DataFrame(lyrics_data)

# --------------------- Streamlit APP ---------------------

st.title("🎸 Análisis de Letras de Radiohead")

if st.button("Cargar y analizar letras"):
    with st.spinner("Cargando información..."):
        lyrics_df = obtener_datos()

    if lyrics_df.empty:
        st.error("No se encontraron letras. Intenta más tarde.")
    else:
        all_lyrics = ' '.join(lyrics_df['lyrics'].dropna()).lower()
        stopwords = set(['the', 'and', 'to', 'a', 'of', 'in', 'i', 'you', 'my', 'it', 'on', 'me'])
        words = [word.strip('.,!?"()') for word in all_lyrics.split() if word not in stopwords]
        word_freq = Counter(words)

        st.subheader("☁️ Nube de Palabras")
        wordcloud = WordCloud(width=800, height=400, background_color='white').generate(' '.join(words))
        fig_wc, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        st.pyplot(fig_wc)

        st.subheader("📊 Top 10 Palabras más Frecuentes")
        common_words_df = pd.DataFrame(word_freq.most_common(10), columns=['word', 'count'])
        fig_bar, ax2 = plt.subplots(figsize=(8, 4))
        ax2.bar(common_words_df['word'], common_words_df['count'])
        ax2.set_xlabel("Palabra")
        ax2.set_ylabel("Frecuencia")
        ax2.set_title("Top 10 palabras")
        st.pyplot(fig_bar)

        st.subheader("📋 Tabla de canciones con letras disponibles")
        st.dataframe(lyrics_df[['album', 'track_name', 'lyrics']])
