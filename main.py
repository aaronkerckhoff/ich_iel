import base64
import requests
import json
import time
from datetime import datetime
from io import BytesIO
from PIL import Image


class Post:
    def __init__(self, title: str, id: str, url: str, image_url: str, author: str, ups: int, date: datetime):
        self.title = title
        self.id = id
        self.url = url
        self.image_url = image_url
        self.image_size = self.get_image_size()
        self.author = author
        self.ups = ups
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
        image = Image.open(BytesIO(requests.get(self.image_url).content))

        new_image = Image.new('RGB', (round(size[0]), round(size[1])), (255, 255, 255))  # Create a new white image with the correct size
        new_image.paste(image, (round((size[0] - self.image_size[0]) / 2), round((size[1] - self.image_size[1]) / 2)))  # Paste the old image in the center of the new image

        # Upload the image to Imgur and get the link
        filetype = self.image_url.split('.')[-1]
        filetype = filetype.replace('jpg', 'jpeg')  # Imgur doesn't accept jpg

        image_bytes = BytesIO()
        new_image.save(image_bytes, format=filetype)
        image_bytes.getvalue()

        url = 'https://api.imgur.com/3/image'  # Imgur API endpoint
        with open('imgur', 'r') as file:
            imgur_client_id = file.read()

        headers = {'Authorization': 'Client-ID ' + imgur_client_id}
        payload = {'image': base64.b64encode(image_bytes.getvalue()).decode('utf-8')}
        response = requests.post(url, headers=headers, data=payload)

        # Get the link of the optimized image
        self.image_url = json.loads(response.text)['data']['link']

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

    def post(self, path: str = "", params: dict = None, headers: dict = None, data: dict = None, useragent: dict = USER_AGENT):
        headers = headers if headers else {}
        headers['User-Agent'] = useragent
        return requests.post(f'{self.url}{path}', params=params, headers=headers, data=data)


class Scraper:
    BASE_URL = 'https://www.reddit.com/r/ich_iel'
    REQUEST_HANDLER = RequestHandler(BASE_URL)

    def get_post(self):
        url = '/top.json?limit=100'
        response = self.REQUEST_HANDLER.get(url)
        data = json.loads(response.text)
        # Create a file to store ids of posts that have already been returned
        with open('posts', 'a+') as file:
            file.write('')

        with open('posts', 'r') as file:
            posts = file.read().split('\n')

        for post in data['data']['children']:
            post = post['data']
            title = post['title']
            id = post['id']
            url = f'https://redd.it/{id}'
            image_url = post['url']
            author = post['author']
            ups = post['ups']
            date = datetime.fromtimestamp(post['created_utc'])
            nsfw = post['over_18']
            video = post['is_video']
            if nsfw or video or id in posts:
                continue
            # Append the id to the file so that it won't be returned again
            with open('posts', 'a') as file:
                file.write(id + '\n')
            # Return the post
            return Post(title, id, url, image_url, author, ups, date)


class Instagram:
    def __init__(self):
        self.access_token = input('Enter your access token: ')
        self.access_token_expires = None
        self.client_id = None
        self.client_secret = None
        self.facebook_page_id = None
        self.page_id = None
        self.facebook_request_handler = RequestHandler('https://graph.facebook.com/v14.0')
        self.setup()

    def setup(self):
        with open('instagram', 'r') as file:
            content = file.read().split('\n')
            self.facebook_page_id = content[0]
            self.client_id = content[1]
            self.client_secret = content[2]

        # Get long-lived access token
        print('Getting long-lived access token...')
        params = {'grant_type': 'fb_exchange_token', 'client_id': self.client_id, 'client_secret': self.client_secret, 'fb_exchange_token': self.access_token}
        response = self.facebook_request_handler.get('/oauth/access_token', params=params).json()
        self.access_token = response['access_token']
        self.access_token_expires = int(time.time()) + response['expires_in']

        # Get instagram page ID
        print('Getting instagram page ID...')
        params = {'access_token': self.access_token, 'fields': 'instagram_business_account'}
        response = self.facebook_request_handler.get(f'/{self.facebook_page_id}', params=params).json()
        self.page_id = response['instagram_business_account']['id']

    def post_image(self, post: Post):
        # Create media container
        params = {'access_token': self.access_token, 'image_url': post.image_url, 'caption': post.title}
        response = self.facebook_request_handler.post(f'/{self.page_id}/media', params=params).json()
        media_id = response['id']

        # Publish media container
        params = {'access_token': self.access_token, 'creation_id': media_id}
        response = self.facebook_request_handler.post(f'/{self.page_id}/media_publish', params=params).json()
        post_id = response['id']

        # Add comment with post information
        comment = f'🔥 {post.ups} Hochwählis\n📸 Pfosten von u/{post.author}\n🔗 Verknüpfung im Internetz unter {post.url.replace("https://", "")}'
        params = {'access_token': self.access_token, 'message': comment}
        response = self.facebook_request_handler.post(f'/{post_id}/comments', params=params).json()


def main():
    instagram = Instagram()
    instagram.post_image(Scraper().get_post())


if __name__ == '__main__':
    main()
