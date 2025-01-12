import boto3
import logging
from mal import Anime, AnimeSearch
import json
from datetime import datetime, timedelta
import sys
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info('Loading function')

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('anime-cache')

def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': str(err) if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json'
        },
    }

def lambda_handler(event, context):
    if 'Records' in event:
        # SNS Trigger
        for record in event['Records']:
            sns_message = json.loads(record['Sns']['Message'])
            
            if 'mal_ids' in sns_message:
                mal_ids = sns_message['mal_ids']
                # Process SNS message
                print(f'Attempting to cache the following anime ids {mal_ids}')
                
                for mal_id in mal_ids:
                    get_or_put_anime(mal_id)
                
        return respond(None, f'Cached {len(mal_ids)} animes')
    else:
        return respond(ValueError('Not support operation'))

def get_or_put_anime(mal_id):
    # Check if the item already exists in the "anime-cache" table
    response = table.get_item(
        Key={
            'mal_id': mal_id
        }
    )
    
    # If the item exists
    if 'Item' in response:
        existing_item = convert_decimals_to_floats(response['Item'])
        print(f'Found anime with id {mal_id} in cache')
        return existing_item
    else:
        # Calculate the expiration time (1 week from the current time)
        expiration_time = datetime.now() + timedelta(weeks=1)
        expiration_timestamp = int(expiration_time.timestamp())
        
        anime = Anime(mal_id)
        
        anime_details = {
                'mal_id': anime.mal_id,
                'title': anime.title,
                'title_english': anime.title_english,
                'title_japanese': anime.title_japanese,
                'title_synonyms': anime.title_synonyms,
                'url': anime.url,
                'image_url': anime.image_url,
                'type': anime.type,
                'status': anime.status,
                'genres': anime.genres,
                'themes': anime.themes,
                'external_links': anime.external_links,
                'score': anime.score,
                'scored_by': anime.scored_by,
                'rank': anime.rank,
                'popularity': anime.popularity,
                'members': anime.members,
                'favorites': anime.favorites,
                'episodes': anime.episodes,
                'aired': anime.aired,
                'premiered': anime.premiered,
                'broadcast': anime.broadcast,
                'producers': anime.producers,
                'licensors': anime.licensors,
                'studios': anime.studios,
                'source': anime.source,
                'duration': anime.duration,
                'rating': anime.rating,
                'related_anime': anime.related_anime,
                'opening_themes': anime.opening_themes,
                'ending_themes': anime.ending_themes,
                'synopsis':  anime.synopsis,
                'background': anime.background,
                'ttl': expiration_timestamp
            }
        
        
        item = convert_floats_to_decimals(anime_details)
        
        # Store the new item in the "animes" table
        table.put_item(Item=item)
        
        size_in_kb = get_dict_size(item)
        print(f"Storing anime in cache with size: {size_in_kb:.2f} KB")
        return anime_details
        
def get_dict_size(dictionary):
    size_bytes = sys.getsizeof(dictionary)
    size_kb = size_bytes / 1024
    return size_kb
    
def convert_decimals_to_floats(data):
    if isinstance(data, dict):
        return {k: convert_decimals_to_floats(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_decimals_to_floats(item) for item in data]
    elif isinstance(data, Decimal):
        return float(data)
    else:
        return data
        
def convert_floats_to_decimals(data):
    if isinstance(data, dict):
        return {k: convert_floats_to_decimals(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [convert_floats_to_decimals(item) for item in data]
    elif isinstance(data, float):
        return Decimal(str(data))
    else:
        return data
        
def get_ids_from_string(string):
    # Remove leading/trailing spaces from the string
    string = string.strip()

    # Check if the string is empty
    if len(string) == 0:
        return None

    # Split the string by commas
    numbers = string.split(',')

    ids = []
    # Check if each element is an integer
    for num in numbers:
        num = num.strip()
        if not num.isdigit():
            return None
        else:
            ids.append(int(num))

    return ids