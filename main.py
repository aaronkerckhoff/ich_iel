import os

import requests
import json
from datetime import datetime
from io import BytesIO
from PIL import Image


class Post:
    def __init__(self, title: str, id: str, url: str, image_url: str, author: str, nsfw: bool, date: datetime):
        self.title = title
        self.id = id
        self.url = url
        self.image_url = image_url
        self.image_size = self.get_image_size()
        self.author = author
        self.nsfw = nsfw
        self.date = date
        self.optimize()

    # Get the size of the image
    def get_image_size(self):
        file = BytesIO(requests.get(self.image_url).content)
        image = Image.open(file)
        width, height = image.size
        return width, height

    # Returns true if the aspect ratio of the image is accepted by Instagram
    def is_aspect_ratio_accepted(self):
        width, height = self.image_size

        aspect_ratio = width / height
        if 0.8 <= aspect_ratio <= 1.9:
            return True
        else:
            if aspect_ratio < 0.8:
                return self.calculate_size(0.9)
            else:
                return self.calculate_size(1.8)

    # Optimizes the image by resizing it to the correct aspect ratio
    def change_image_size(self, size: tuple):
        # Create folder '/images' if it doesn't exist
        if not os.path.exists('images'):
            os.makedirs('images')
        # Download the image to the folder '/images'
        filetype = self.image_url.split('.')[-1]
        with open('images/' + self.id + '.' + filetype, 'wb') as f:
            f.write(requests.get(self.image_url).content)

        # Change the aspect ratio
        old_image = Image.open('images/' + self.id + '.' + filetype)
        old_size = old_image.size

        new_image = Image.new('RGB', (round(size[0]), round(size[1])), (255, 255, 255))  # Create a new white image with the correct size
        new_image.paste(old_image, (round((size[0] - old_size[0]) / 2), round((size[1] - old_size[1]) / 2)))  # Paste the old image in the center of the new image
        new_image.save('images/' + self.id + '.' + filetype)  # Save the new image
        print(new_image.size[0] / new_image.size[1])

    # Calculates the needed size of the image given the aspect ratio
    def calculate_size(self, aspect_ratio: float):
        image_width, image_height = self.image_size
        if image_width < image_height:
            image_width = image_height * aspect_ratio
        else:
            image_height = image_width / aspect_ratio

        return image_width, image_height

    def optimize(self):
        aspect_ratio = self.is_aspect_ratio_accepted()
        if aspect_ratio is not True:
            self.change_image_size(aspect_ratio)
            self.image_size = aspect_ratio


class RequestHandler:
    USER_AGENT = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/103.0.0.0 Safari/537.36'

    def __init__(self, url: str):
        self.url = url

    def get(self, path: str = "", params: dict = None, headers: dict = None, useragent: dict = USER_AGENT):
        headers = headers if headers else {}
        headers['User-Agent'] = useragent
        return requests.get(f'{self.url}{path}', params=params, headers=headers)

    def post(self, path: str, params: dict, headers: dict, data: dict, useragent: dict = USER_AGENT):
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
        id = post['id']
        url = f'https://redd.it/{id}'
        image_url = post['url']
        author = post['author']
        nsfw = post['over_18']
        date = datetime.fromtimestamp(post['created_utc'])
        return Post(title, id, url, image_url, author, nsfw, date)


print(Scraper().get_post())
