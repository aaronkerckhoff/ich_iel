import base64
import os
import random
import requests
import json
import time
import schedule
import logging
import logging.config
from datetime import datetime
from io import BytesIO
from PIL import Image

global scraper, instagram, logger


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
        logger.info('Image size: ' + str(width) + 'x' + str(height))
        return width, height

    # Returns true if the aspect ratio of the image is accepted by Instagram
    def is_aspect_ratio_accepted(self):
        width, height = self.image_size

        aspect_ratio = width / height
        if 0.8 <= aspect_ratio <= 1.9:
            return True
        else:
            logger.info('Aspect ratio not accepted: ' + str(aspect_ratio))
            if aspect_ratio < 0.8:
                return self.calculate_size(0.9)
            else:
                return self.calculate_size(1.8)

    # Optimizes the image by resizing it to the correct aspect ratio
    def change_image_size(self, size: tuple):
        logger.info('Resizing image to: ' + str(size))
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
        logger.info('Optimized image: ' + self.image_url)

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
        try:
            logger.info('Scraping post from Reddit...')
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
                logger.info('Post scraped, id: ' + id)
                return Post(title, id, url, image_url, author, ups, date)
        except Exception as e:
            logger.exception('Error while scraping post from Reddit')
            logger.exception(e)
            return None


class Instagram:
    def __init__(self):
        self.access_token = None
        self.access_token_expires = None
        self.client_id = None
        self.client_secret = None
        self.facebook_page_id = None
        self.page_id = None
        self.facebook_request_handler = RequestHandler('https://graph.facebook.com/v14.0')
        self.setup()

    def setup(self):
        logger.info('Setting up instagram handler...')
        self.check_credentials()

        # Get instagram page ID
        logger.info('Getting instagram page ID...')
        params = {'access_token': self.access_token, 'fields': 'instagram_business_account'}
        response = self.facebook_request_handler.get(f'/{self.facebook_page_id}', params=params).json()
        self.page_id = response['instagram_business_account']['id']
        logger.info(f'Instagram page ID: {self.page_id}')

    def post_image(self, post: Post):
        # Check credentials
        self.check_credentials()

        # Generate caption
        response = None
        try:
            caption = f'{post.title}\n\n'
            # Add random hashtags to the caption
            with open('hashtags', 'r') as file:
                hashtags = file.read().split('\n')
            for i in range(10):
                hashtag = random.choice(hashtags)
                hashtags.remove(hashtag)
                caption += f'#{hashtag} '
            logger.info(f'Generated caption: {caption}')

            # Create media container
            params = {'access_token': self.access_token, 'image_url': post.image_url, 'caption': caption}
            response = self.facebook_request_handler.post(f'/{self.page_id}/media', params=params).json()
            media_id = response['id']
            logger.info(f'Created media container with ID {media_id}')

            # Publish media container
            params = {'access_token': self.access_token, 'creation_id': media_id}
            response = self.facebook_request_handler.post(f'/{self.page_id}/media_publish', params=params).json()
            post_id = response['id']
            logger.info(f'Published media container as post with ID {post_id}')

            # Add comment with post information
            comment = f'🔥 {post.ups} Hochwählis\n📸 Pfosten von u/{post.author}\n🔗 Verknüpfung im Internetz unter {post.url.replace("https://", "")}'
            params = {'access_token': self.access_token, 'message': comment}
            response = self.facebook_request_handler.post(f'/{post_id}/comments', params=params).json()
            comment_id = response['id']
            logger.info(f'Added comment with ID {comment_id}')
        except Exception as e:
            logger.exception('Failed to post image')
            logger.exception(e)
            if response:
                logger.error(response)

        logger.info('\nWaiting for next post...\n')

    def check_credentials(self):
        with open('instagram', 'r') as file:  # Load the access token from the file
            content = file.read().split('\n')
            self.facebook_page_id = content[0]
            self.client_id = content[1]
            self.client_secret = content[2]
            if self.access_token is not content[3]:  # If the access token differs from the one in the file, update it
                self.access_token = content[3]
                logger.info('Getting long-lived access token...')
                params = {'grant_type': 'fb_exchange_token', 'client_id': self.client_id,
                          'client_secret': self.client_secret, 'fb_exchange_token': self.access_token}
                response = self.facebook_request_handler.get('/oauth/access_token', params=params).json()
                try:
                    self.access_token = response['access_token']
                    self.access_token_expires = int(time.time()) + response['expires_in']
                    logger.info('Successfully updated access token')
                except KeyError:
                    logger.exception('KeyError occurred while getting long-lived access token')
                    logger.error(response)

        # Update file
        content[3] = self.access_token
        with open('instagram', 'w') as file:
            file.write('\n'.join(content))

        if self.access_token_expires - int(time.time()) < (60 * 60 * 24 * 7):  # If the access token is about to expire in less than 1 week
            logger.warning('Your access token is about to expire!')
            logger.warning('Please update your access token as soon as possible.')


def post_image(posts: int = 1):
    for i in range(posts):
        post = scraper.get_post()
        instagram.post_image(post)
        logger.info(f'Posted image {post.title}, url: {post.url}, image: {post.image_url}, author: {post.author}, ups: {post.ups}, date: {post.date}')


def initialize_logger():
    global logger

    current_time = datetime.now()

    def create_directory(path: str):
        if not os.path.exists(path):
            os.makedirs(path)

    logging_config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'default_formatter': {
                'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            },
        },
        'handlers': {
            'stream_handler': {
                'class': 'logging.StreamHandler',
                'formatter': 'default_formatter',
            },
            'file_handler': {
                'class': 'logging.FileHandler',
                'filename': f'logs/{current_time.strftime("%Y")}/{current_time.strftime("%B")}/{current_time.strftime("%d")}{current_time.strftime("%m")}{current_time.strftime("%Y")}.log',
                'mode': 'a',
                'formatter': 'default_formatter',
            },
        },
        'loggers': {
            'ich_iel': {
                'handlers': ['stream_handler', 'file_handler'],
                'level': 'INFO',
                'propagate': False,
            },
        },
    }

    create_directory(f'logs/{current_time.strftime("%Y")}/{current_time.strftime("%B")}')

    logging.config.dictConfig(logging_config)
    logger = logging.getLogger('ich_iel')
    logger.info('Logger initialized')


def main():
    global scraper, instagram

    initialize_logger()
    logger.info('Starting ich_iel...')

    scraper = Scraper()
    instagram = Instagram()

    schedule.every().day.at('11:00').do(lambda: post_image(1))  # 1 total post
    schedule.every().day.at('12:00').do(lambda: post_image(1))  # 2 total posts
    schedule.every().day.at('13:00').do(lambda: post_image(2))  # 4 total posts
    schedule.every().day.at('13:30').do(lambda: post_image(2))  # 6 total posts
    schedule.every().day.at('14:00').do(lambda: post_image(2))  # 8 total posts
    schedule.every().day.at('14:30').do(lambda: post_image(2))  # 10 total posts
    schedule.every().day.at('15:00').do(lambda: post_image(2))  # 12 total posts
    schedule.every().day.at('15:30').do(lambda: post_image(2))  # 14 total posts
    schedule.every().day.at('16:00').do(lambda: post_image(1))  # 16 total posts
    schedule.every().day.at('16:30').do(lambda: post_image(1))  # 17 total posts
    schedule.every().day.at('17:00').do(lambda: post_image(1))  # 18 total posts
    schedule.every().day.at('17:30').do(lambda: post_image(1))  # 19 total posts
    schedule.every().day.at('18:00').do(lambda: post_image(1))  # 20 total posts
    schedule.every().day.at('19:00').do(lambda: post_image(1))  # 21 total posts
    schedule.every().day.at('20:00').do(lambda: post_image(1))  # 22 total posts
    schedule.every().day.at('21:00').do(lambda: post_image(1))  # 23 total posts
    schedule.every().day.at('22:00').do(lambda: post_image(1))  # 24 total posts
    logger.info('Scheduled posting times')

    # Create new log file on every new day
    schedule.every().day.at('00:00').do(lambda: initialize_logger())

    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == '__main__':
    main()
