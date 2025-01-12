import boto3
import logging
from mal import Anime, AnimeSearch
import json
from datetime import datetime, timedelta
import sys
from decimal import Decimal
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

logger.info('Loading function')

sns_client = boto3.client('sns')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('anime-cache')

def respond(err, res=None):
    return {
        'statusCode': '400' if err else '200',
        'body': str(err) if err else json.dumps(res),
        'headers': {
            'Content-Type': 'application/json',
            "Access-Control-Allow-Headers" : "Content-Type",
            "Access-Control-Allow-Origin": "https://animedubstatus.com",
            "Access-Control-Allow-Methods": "OPTIONS,GET"
        },
    }

def lambda_handler(event, context):
    operation = event['httpMethod']
    if operation == 'GET':
        queryParams = event['queryStringParameters']
        
        if 'query' in queryParams:
            searchString = queryParams['query']
            
            if searchString == None:
                return respond(ValueError('No search string provided'))
            
            search = AnimeSearch(searchString)
            if search == None or len(search.results) <= 0:
                return respond(ValueError('Failed to get results. Please adjust your query or try again.'))
            
            results = move_matching_title_to_front(keep_max(search.results, 20), searchString)
            
            searchResults = []
            mal_ids = []
            for anime in results:
                anime_details = {
                    'mal_id': anime.mal_id,
                    'title': anime.title,
                    'url': anime.url,
                    'image_url': anime.image_url,
                    'type': anime.type,
                    'score': anime.score,
                    'synopsis':  anime.synopsis
                }
                searchResults.append(anime_details)
                mal_ids.append(anime.mal_id)
                
            sns_client.publish(
                TopicArn=os.environ['CacheAnimeTopic'],
                Message=json.dumps({
                    'mal_ids': mal_ids
                })
            )
                
            return respond(None, searchResults)
        else:
            return respond(ValueError('Did not supply proper query string for `search`'))
            
    else:
        return respond(ValueError('Unsupported method "{}"'.format(operation)))
    
def keep_max(array, max):
    if len(array) > max:
        return array[:max]
    else:
        return array
    
def move_matching_title_to_front(array, title):
    lower_title = title.lower()  # Convert the title to lowercase for case-insensitive comparison
    new_array = []
    for obj in array:
        if obj != None and obj.title.lower() == lower_title:
            new_array.insert(0, obj)  # Add matching object to the front of the new array
        else:
            new_array.append(obj)  # Add non-matching objects to the end of the new array
    return new_array