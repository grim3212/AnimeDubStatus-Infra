# Anime Dub Status - Infra

Contains the backend infrastructure for the Anime Dub Status website https://animedubstatus.com/.

Frontend source can be found at https://github.com/grim3212/AnimeDubStatus

All the infrastructure is currently deployed to AWS and primarily driven via lambdas using `Python`.

> Warning things were setup very manually and are extraordinarily unorganized and messy. I never got around to cleaning things up once I got it working. 😢

### Credits

- One of the Lambdas, `dubInfoDownloader` utilizes the `AGPL-3.0` licensed [dubInfo.json](https://github.com/MAL-Dubs/MAL-Dubs/blob/main/data/dubInfo.json) from [MAL-Dubs](https://github.com/MAL-Dubs/MAL-Dubs). Having this maintained was a huge relief. ⭐
- The `dubInfoDownloader` lambda also will parse the list of [currently airing anime](https://myanimelist.net/forum/?topicid=1692966) from MyAnimeList that [Kenny_Stryker](https://myanimelist.net/profile/Kenny_Stryker) maintains.
- The MyAnimeList API used extensively through the Python package [mal-api](https://pypi.org/project/mal-api/)

### Infrastructure

The following are the 4 lambdas that drive the functionality of AnimeDubStatus. They are built in [Python](https://www.python.org/) and [Pipenv](https://pipenv.pypa.io/). As warned above things are messy so there is a lot of code that was copied between them currently.

#### dubInfoDownloader

Triggered by an event through EventBridge. Will download a new version of `dubInfo.json` once a day and stores it in an `s3` bucket.

Through the same event we will scrape the MyAnimeList page for currently airing anime and store it into a JSON file that we can use. This JSON is also stored in the same `s3` bucket.

This will then retrieve and cache any anime returned by the currently airing anime list so that the client doesn't need to wait for the other Lambda's to cache what is currently shown when you load the website.

The cached anime details are stored within `DynamoDB`.

#### animeSearch

Triggered by an `API Gateway` this is the endpoint that is triggered when you search on the website. It will return a short list of results from the MAL API. It will then publish an `SNS` message to trigger another lambda to go and find full details for each anime and then cache them.

#### animeDetails

Triggered by an `API Gateway` this endpoint will return full details for the given mal_ids. It will first check if we have already cached the items and if not then go and find the details and cache them in `DynamoDB`. Once everything has been cached it will return you the Anime information.

#### animeCaching

Triggered by a publish to the `SNS` topic that the `animeSearch` lambda would trigger. Pretty much performs the exact same task as `animeDetails`. Just gets a list of `mal_ids` to get information on. Then caches those details in `dynamodb`.

### TODO

- Everything was setup manually and is quite a mess. Eventually I would like to automate this with some IAC setup like [AWS SAM](https://aws.amazon.com/serverless/sam/) or something similar.

