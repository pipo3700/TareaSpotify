# app.py
import requests
import pandas as pd
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import streamlit as st
import time
import re
from collections import Counter

# --- Autenticación Spotify ---
CLIENT_ID = '1ca3b8b35e844555a718cd928a0a964e'
CLIENT_SECRET = '62774e39c57141f7870ccf312213f1b5'

# Obtener token de acceso
auth_response = requests.post('https://accounts.spotify.com/api/token', {
    'grant_type': 'client_credentials',
    'client_id': CLIENT_ID,
    'client_secret': CLIENT_SECRET,
})
access_token = auth_response.json()['access_token']
headers = {'Authorization': f'Bearer {access_token}'}
BASE_URL = 'https://api.spotify.com/v1/'

# --- Configurar artista ---
artist_name = 'The Smiths'

# Buscar ID del artista
search_url = BASE_URL + 'search'
params = {'q': artist_name, 'type': 'artist'}
response = requests.get(search_url, headers=headers, params=params)
artist_id = response.json()['artists']['items'][0]['id']

# Obtener álbumes (solo "album", sin singles ni compilaciones)
r = requests.get(BASE_URL + f'artists/{artist_id}/albums', headers=headers, params={
    'include_groups': 'album',
    'limit': 50
})
albums_raw = r.json()['items']

# Filtrar álbumes de estudio oficiales según Wikipedia
studio_albums = ['The Smiths', 'Meat Is Murder', 'The Queen Is Dead', 'Strangeways, Here We Come']

# Elegir versión más antigua de cada álbum
filtered_albums = {}
for album in albums_raw:
    name = album['name']
    if name in studio_albums:
        if name not in filtered_albums or album['release_date'] < filtered_albums[name]['release_date']:
            filtered_albums[name] = album
albums_filtered = list(filtered_albums.values())

# Obtener canciones de los álbumes
tracks = []
for album in albums_filtered:
    r = requests.get(BASE_URL + f'albums/{album["id"]}/tracks', headers=headers)
    for track in r.json()['items']:
        tracks.append({'album': album['name'], 'track_name': track['name']})

# Obtener letras desde lyrics.ovh
base_lyrics_url = 'https://api.lyrics.ovh/v1'
lyrics_data = []

for track in tracks:
    name = re.sub(r'\(.*?\)|- .*', '', track['track_name']).strip()
    r = requests.get(f'{base_lyrics_url}/{artist_name}/{name}')
    lyrics = r.json().get('lyrics', '') if r.status_code == 200 else ''
    lyrics_data.append({
        'album': track['album'],
        'track_name': name,
        'lyrics': lyrics
    })
    time.sleep(0.5)

# Crear DataFrame
lyrics_df = pd.DataFrame(lyrics_data)

# --- Streamlit App ---
st.title("Análisis de Letras de The Smiths 🎶")

album_selected = st.selectbox("Selecciona un álbum", lyrics_df['album'].unique())
df_album = lyrics_df[lyrics_df['album'] == album_selected]

if df_album.empty or df_album['lyrics'].str.len().sum() == 0:
    st.warning("No hay letras disponibles para este álbum.")
else:
    all_lyrics = ' '.join(df_album['lyrics'].dropna()).lower()
    stopwords = set(['the', 'and', 'to', 'a', 'of', 'in', 'i', 'you', 'my', 'it', 'on', 'me'])
    words = [word.strip('.,!?"()') for word in all_lyrics.split() if word not in stopwords]
    word_freq = Counter(words)

    st.subheader("Nube de Palabras")
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(' '.join(words))
    fig_wc, ax = plt.subplots(figsize=(10, 5))
    ax.imshow(wordcloud, interpolation='bilinear')
    ax.axis('off')
    st.pyplot(fig_wc)

    st.subheader("Top 10 Palabras más Frecuentes")
    common_words_df = pd.DataFrame(word_freq.most_common(10), columns=['word', 'count'])
    fig_bar, ax2 = plt.subplots(figsize=(8, 4))
    common_words_df.plot(kind='bar', x='word', y='count', ax=ax2, legend=False)
    ax2.set_title('Frecuencia de Palabras')
    st.pyplot(fig_bar)
