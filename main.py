import random
from pprint import pprint

import requests
import json
from datetime import datetime


class Post:
    def __init__(self, title: str, url: str, image_url: str, author: str, date: datetime):
        self.title = title
        self.url = url
        self.image_url = image_url
        self.author = author
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
