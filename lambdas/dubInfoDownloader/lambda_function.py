import boto3
import logging
import urllib.request
from mal import Anime
from bs4 import BeautifulSoup
import re
import json
from datetime import datetime, timedelta
import sys
from decimal import Decimal

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info('Loading function')

sns_client = boto3.client('sns')
dubInfoUrl = 'https://raw.githubusercontent.com/MAL-Dubs/MAL-Dubs/main/data/dubInfo.json'
bucketName = 'www.animedubstatus.com'
fileName = 'dubInfo.json'

s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('anime-cache')

def lambda_handler(event, context):
    try:
        pullDubInfo()
        pullCurrentlyAiring()
        return True
    except Exception as e:
        logging.error(e)
        raise e
    
def pullDubInfo():
    logger.info(f'Grabbing dubInfo.json from {dubInfoUrl}')
    with urllib.request.urlopen(dubInfoUrl) as f:
        s3.upload_fileobj(f, bucketName, fileName)
    return True
    
def pullCurrentlyAiring():
    results = parseMyAnimeListForumPage()
    s3.put_object(Body=results, Bucket=bucketName, Key='currentlyAiring.json')
    return True


days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday','Friday', 'Saturday', 'Sunday']
# Bracket search
bracketPattern = r'\((.*?)\)'
# Regular expression pattern to extract episode counts and types
pattern = r'([A-Za-z\s]+):\s(\d+)/(\d+)'

currentlyAiringUrl = 'https://myanimelist.net/forum/?topicid=1692966'

def parseMyAnimeListForumPage():
    logger.info('Grabbing currently airing information')
    animes = {}

    with urllib.request.urlopen(currentlyAiringUrl) as response:
        html = response.read().decode("utf-8")
        soup = BeautifulSoup(html, 'html.parser')
        
        for day in days:
            dayAnimes = parseWeekList(soup, day)
            animes[day] = dayAnimes
    return json.dumps(animes)
            

def parseWeekList(soup: BeautifulSoup, dayOfWeek: str):
    dayResults = []
    print(f'Searching for anime for {dayOfWeek}')
    dayTag = soup.find(string=dayOfWeek)
    listTag = dayTag.parent.ul
    if listTag != None:
        print('Found anime entries')
        for tag in listTag.find_all('li'):
            aTag = tag.find('a')
            if aTag == None:
                continue

            href = aTag.get('href')
            id_start_index = href.find("/anime/") + len("/anime/")
            id_end_index = href.find("/", id_start_index)
            mal_id = int(href[id_start_index:id_end_index])
            anime_name = aTag.string

            episodes = []
            match = re.search(bracketPattern, tag.text)
            if match:
                content = match.group(1)
                # Extract episode counts and types from string1
                episodeProgress = re.findall(pattern, content)
                for source, curr, total in episodeProgress:
                    episodes.append({
                        source.strip(): {'current': curr, 'total': total}
                    })
            
            anime_details = get_or_put_anime(mal_id)
            
            anime = {
                'mal_id': mal_id,
                'name': anime_name,
                'episodes': episodes,
                'details': anime_details
            }
            dayResults.append(anime)
    
    return dayResults
    
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