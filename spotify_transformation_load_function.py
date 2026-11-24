import json
import boto3
from datetime import datetime
from io import StringIO
import pandas as pd


def album(data):
    album_list = []

    for row in data['items']:
        album_id = row['item']['album']['id']
        album_name = row['item']['album']['name']
        album_release_date = row['item']['album']['release_date']
        album_total_tracks = row['item']['album']['total_tracks']
        album_url = row['item']['album']['external_urls']['spotify']

        album_elements = {
            "album_id": album_id,
            "album_name": album_name,
            "album_release_date": album_release_date,
            "album_total_tracks": album_total_tracks,
            "album_url": album_url
        }

        album_list.append(album_elements)

    return album_list


def artist(data):
    artist_list = []

    for row in data['items']:
        for key, value in row.items():
            if key == 'item':
                for artist in value['artists']:
                    artist_dict = {
                        "artist_id": artist["id"],
                        "artist_name": artist["name"],
                        "external_url": artist["href"]
                    }

                    artist_list.append(artist_dict)

    return artist_list


def song(data):
    song_list = []

    for row in data['items']:
        song_id = row['item']['id']
        song_name = row['item']['name']
        song_duration = row['item']['duration_ms']
        song_url = row['item']['external_urls']['spotify']
        song_added = row['added_at']
        album_id = row['item']['album']['id']
        artist_id = row['item']['artists'][0]['id']

        song_element = {
            'song_id': song_id,
            'song_name': song_name,
            'duration_ms': song_duration,
            'url': song_url,
            'song_added': song_added,
            'album_id': album_id,
            'artist_id': artist_id
        }

        song_list.append(song_element)

    return song_list


def lambda_handler(event, context):

    s3 = boto3.client('s3')

    Bucket = "spotify-etl-project-kavzz"
    Key = "raw_data/to_processed/"

    spotify_data = []
    spotify_keys = []

    response = s3.list_objects_v2(
        Bucket=Bucket,
        Prefix=Key
    )

    for file in response.get('Contents', []):

        file_key = file['Key']

        if file_key.endswith('.json') and '/processed/' not in file_key:

            response = s3.get_object(
                Bucket=Bucket,
                Key=file_key
            )

            content = response['Body']
            jsonObject = json.loads(content.read())

            spotify_data.append(jsonObject)
            spotify_keys.append(file_key)

    if not spotify_data:
        return {
            "statusCode": 200,
            "body": json.dumps("No raw JSON files found")
        }

    for data in spotify_data:

        album_list = album(data)
        artist_list = artist(data)
        song_list = song(data)

        album_df = pd.DataFrame(album_list)
        album_df = album_df.drop_duplicates(subset=["album_id"])

        artist_df = pd.DataFrame(artist_list)
        artist_df = artist_df.drop_duplicates(subset=["artist_id"])

        song_df = pd.DataFrame(song_list)
        song_df = song_df.drop_duplicates(subset=["song_id"])

        album_df['album_release_date'] = pd.to_datetime(
            album_df['album_release_date'], errors='coerce'
        )

        song_df['song_added'] = pd.to_datetime(
            song_df['song_added'], errors='coerce'
        )

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Save song data
        song_key = "transformed_data/song_data/song_transformed_" + timestamp + ".csv"

        song_buffer = StringIO()
        song_df.to_csv(song_buffer, index=False)

        s3.put_object(
            Bucket=Bucket,
            Key=song_key,
            Body=song_buffer.getvalue()
        )

        # Save album data
        album_key = "transformed_data/album_data/album_transformed_" + timestamp + ".csv"

        album_buffer = StringIO()
        album_df.to_csv(album_buffer, index=False)
    
        s3.put_object(
            Bucket=Bucket,
            Key=album_key,
            Body=album_buffer.getvalue()
        )

        # Save artist data
        artist_key = "transformed_data/artist_data/artist_transformed_" + timestamp + ".csv"

        artist_buffer = StringIO()
        artist_df.to_csv(artist_buffer, index=False)

        s3.put_object(
            Bucket=Bucket,
            Key=artist_key,
            Body=artist_buffer.getvalue()
        )

    # Move original JSON files after successful transformation
    s3_resource = boto3.resource('s3')

    for key in spotify_keys:
        copy_source = {
            'Bucket': Bucket,
            'Key': key
        }

        destination_key = "raw_data/processed/" + key.split("/")[-1]

        s3_resource.meta.client.copy(
            copy_source,
            Bucket,
            destination_key
        )

        s3_resource.Object(Bucket, key).delete()

    return {
        "statusCode": 200,
        "body": json.dumps("Spotify ETL completed successfully")
    }