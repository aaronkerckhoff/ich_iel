import random
from pprint import pprint
import requests
import json
from datetime import datetime


class Post:
    def __init__(self, title: str, url: str, image_url: str, author: str, nsfw: bool, date: datetime):
        self.title = title
        self.url = url
        self.image_url = image_url
        self.author = author
        self.nsfw = nsfw
        self.date = date


class RequestHandler:
    USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'

    def __init__(self, url: str):
        self.url = url

    def get(self, path: str="", params: dict=None, headers: dict=None, useragent=USER_AGENT):
        headers = headers if headers else {}
        headers['User-Agent'] = useragent
        return requests.get(f'{self.url}{path}', params=params, headers=headers)

    def post(self, path: str, params: dict, headers: dict, data: dict, useragent=USER_AGENT):
        headers = headers if headers else {}
        headers['User-Agent'] = useragent
        return requests.post(f'{self.url}{path}', params=params, headers=headers, data=data)


class Scraper:
    BASE_URL = 'https://www.reddit.com/r/ich_iel'
    REQUEST_HANDLER = RequestHandler(BASE_URL)

    def get_post(self):
        url = '/top.json?limit=1'
        response = self.REQUEST_HANDLER.get(url)
        data = json.loads(response.text)
        post = data['data']['children'][0]['data']
        title = post['title']
        url = f'https://www.reddit.com/r/ich_iel/comments/{post["id"]}'
        image_url = post['url']
        author = post['author']
        nsfw = post['over_18']
        date = datetime.fromtimestamp(post['created_utc'])

        return Post(title, url, image_url, author, nsfw, date)
