import streamlit as st
import requests
import pandas as pd
import openai

def get_access_token(client_id, client_secret):
    auth_response = requests.post('https://accounts.spotify.com/api/token', {
        'grant_type': 'client_credentials',
        'client_id': client_id,
        'client_secret': client_secret,
    })
    if auth_response.status_code == 200:
        return auth_response.json()['access_token']
    else:
        st.error("Failed to authenticate with Spotify API")
        return None

def get_playlist_artists(playlist_id, token):
    """Retrieve artists from a specific playlist"""
    url = f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
    headers = {"Authorization": f"Bearer {token}"}
    artist_ids = set()
    artist_data = []
    response = requests.get(url, headers=headers)
    while response.status_code == 200 and url:
        items = response.json()['items']
        for item in items:
            track = item['track']
            if track:
                for artist_info in track['artists']:
                    if artist_info['id'] not in artist_ids:
                        artist_data.append({
                            "id": artist_info['id'],
                            "name": artist_info['name']
                        })
                        artist_ids.add(artist_info['id'])
        url = response.json().get('next')
        if url:
            response = requests.get(url, headers=headers)
        else:
            break
    return artist_data

def get_artists_details(artists, token, num_artists):
    artist_details = []
    for artist in artists:
        url = f"https://api.spotify.com/v1/artists/{artist['id']}"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            artist_details.append({
                "id": data['id'],
                "name": data['name'],
                "popularity": data['popularity'],
                "followers": data['followers']['total'],
                "image": data['images'][0]['url'] if data['images'] else None
            })
    return sorted(artist_details, key=lambda x: x['popularity'], reverse=True)[:num_artists]

def get_top_tracks(artist_id, token):
    """Get top tracks of the artist by artist ID"""
    url = f"https://api.spotify.com/v1/artists/{artist_id}/top-tracks?market=US"
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        tracks = response.json()['tracks']
        sorted_tracks = sorted(tracks, key=lambda x: x['popularity'], reverse=True)[:5]
        return sorted_tracks
    else:
        return []

def openai_query(artist_name, api_key):
    """Query OpenAI API for artist information"""
    openai.api_key = api_key
    response = openai.Completion.create(
        engine="davinci",
        prompt=f"Provide a brief summary, list of members, and debut date for the music artist: {artist_name}.",
        max_tokens=150
    )
    return response['choices'][0]['text'].strip()

def main():
    st.title("Spotify Playlist Artist Popularity Tracker")

    client_id = st.sidebar.text_input("Client ID")
    client_secret = st.sidebar.text_input("Client Secret")
    playlist_id = st.sidebar.text_input("Playlist ID", value='37i9dQZF1DX3QbJYj9DkHB')
    openai_api_key = st.sidebar.text_input("OpenAI API Key", type="password")
    num_artists = st.sidebar.slider("Number of Top Artists to Display", 5, 30, 10, 1)

    if client_id and client_secret:
        token = get_access_token(client_id, client_secret)
        if token:
            artist_data = get_playlist_artists(playlist_id, token)
            if artist_data:
                detailed_artists = get_artists_details(artist_data, token, num_artists)
                if detailed_artists:
                    df = pd.DataFrame(detailed_artists)
                    st.subheader(f"Top {num_artists} Artists by Popularity:")
                    df.index = df.index + 1  # Adjust index to start from 1
                    st.dataframe(df[['name', 'popularity', 'followers']])

                    artist_choice = st.selectbox("Select an artist for more details", df['name'])
                    artist_info = df[df['name'] == artist_choice].iloc[0]
                    st.subheader("Artist Details:")
                    st.write(f"Name: {artist_info['name']}")
                    st.write(f"Popularity: {artist_info['popularity']}")
                    st.write(f"Followers: {artist_info['followers']}")
                    if artist_info['image']:
                        st.image(artist_info['image'], width=200)

                    top_tracks = get_top_tracks(artist_info['id'], token)
                    if top_tracks:
                        st.subheader("Top 5 Tracks:")
                        for track in top_tracks:
                            st.write(f"{track['name']} (Popularity: {track['popularity']})")
                            st.write(f"[Listen on Spotify]({track['external_urls']['spotify']})")
                            if 'album' in track and track['album']['images']:
                                st.image(track['album']['images'][0]['url'], width=200)

                    if openai_api_key:
                        openai_info = openai_query(artist_info['name'], openai_api_key)
                        st.subheader("Additional Artist Info from OpenAI")
                        st.write(openai_info)

if __name__ == "__main__":
    main()
