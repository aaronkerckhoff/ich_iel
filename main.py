import random
import requests
import json
from datetime import datetime


class Post:
    def __init__(self, title: str, description: str, url: str, image_url: str, author: str, date: datetime):
        self.title = title
        self.description = description
        self.url = url
        self.image_url = image_url
        self.author = author
        self.date = date
