
import json
import os
import hashlib
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import boto3
from datetime import datetime

def lambda_handler(event, context):

    client_id = os.environ.get("client_id")
    client_secret = os.environ.get("client_secret")
    refresh_token = os.environ.get("refresh_token")

    print("Client ID exists:", bool(client_id))
    print("Client Secret exists:", bool(client_secret))
    print("Refresh Token exists:", bool(refresh_token))

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Missing Spotify environment variables")

    # Spotify authentication
    auth_manager = SpotifyOAuth(
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri="http://127.0.0.1:9090/callback",
        scope="playlist-read-private playlist-read-collaborative"
    )

    token_info = auth_manager.refresh_access_token(refresh_token)

    sp = spotipy.Spotify(auth=token_info["access_token"])

    # Get playlist items
    playlist_URI = "6tr3JfQH5gdSdh4lwVZlmn"

    spotify_data = sp.playlist_items(playlist_URI)

    print(spotify_data)

    # Connect to S3
    client = boto3.client("s3")

    # Create filename
    filename = "spotify_raw_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".json"

    # Upload raw Spotify data to S3
    client.put_object(
        Bucket="spotify-etl-project-kavzz",
        Key="raw_data/to_processed/" + filename,
        Body=json.dumps(spotify_data),
        ContentType="application/json"
    )

    print("Spotify raw data uploaded successfully:", filename)

    return {
        "statusCode": 200,
        "body": json.dumps("Spotify data fetched and saved to S3 successfully")
    }
