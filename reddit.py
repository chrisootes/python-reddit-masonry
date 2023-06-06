#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import urllib.parse
import asyncio
import queue
import threading

import requests
import requests.auth
import json_stream
import json_stream.requests
import demoji

import config

logger = logging.getLogger(__name__)

# demoji.download_codes()

class Reddit:
    def __init__(self):
        self.session = requests.Session()

        # Create basic auth connection
        client_auth = requests.auth.HTTPBasicAuth(
            config.REDDIT_CLIENT_ID,
            config.REDDIT_CLIENT_SECRET
        )
        
        # With POST data
        post_data = {
            "grant_type": "password",
            "username": config.REDDIT_USERNAME,
            "password": config.REDDIT_PASSWORD
        }
        # User agent in headers
        headers = {
            "User-Agent": config.REDDIT_USERAGENT
        }
        # Execute request
        response = self.session.post(
            url="https://www.reddit.com/api/v1/access_token",
            auth=client_auth,
            data=post_data,
            headers=headers
        )
        # Parse response
        self.ratelimit_used = float(response.headers['x-ratelimit-used'])
        self.ratelimit_remaining = float(response.headers['x-ratelimit-remaining'])
        self.ratelimit_reset = float(response.headers['x-ratelimit-reset'])
        response_json = response.json()

        self.access_token = response_json['access_token']

    def request(self, endpoint, params={}, stream=False):
        if self.ratelimit_remaining <= 2:
            logger.warning("Rate limit exeeded waiting")
            # TODO fix block
            time.sleep(self.ratelimit_reset)

        headers = {
            "Authorization": f"bearer {self.access_token}",
            "User-Agent": config.REDDIT_USERAGENT
        }
        url = urllib.parse.urljoin(
            "https://oauth.reddit.com",
            endpoint
        )
        # Should not block much, because stream, so no big need for async
        response = self.session.get(
            url=url,
            headers=headers,
            params=params,
            stream=stream,
        )
        
        # Parse response
        status_code = int(response.status_code)
        if status_code != 200:
            raise Exception(f"Status code: {status_code}")
        self.ratelimit_used = float(response.headers['x-ratelimit-used'])
        self.ratelimit_remaining = float(response.headers['x-ratelimit-remaining'])
        self.ratelimit_reset = float(response.headers['x-ratelimit-reset'])

        if stream:
            # Convert json streamer callback to a post dict generator
            generator_queue = queue.SimpleQueue ()
            def visitor(item, path):
                #logger.debug(f"{path} = {item}")
                generator_queue.put((item, path))
            logger.debug(f"start thread")
            thread = threading.Thread(target=json_stream.requests.visit, args=(response, visitor))
            thread.start()
            current_post = {}
            last_post_number = 0
            logger.debug(f"start loop")
            while True:
                # TODO fix block
                (item, path) = generator_queue.get()
                # If path[2] changes then we have next post
                if len(path) >= 3:
                    if last_post_number != path[2]:
                        logger.debug(f"last_post_number {last_post_number}")
                        last_post_number = path[2]
                        yield current_post
                        # TODO clean current_post     
                # Common post root items
                if len(path) == 5:
                    current_post[path[4]] = item
                # One item in subdict
                elif len(path) == 11:
                    if path == ('data', 'children', path[2], 'data', 'preview', 'images', 0, 'variants', 'mp4', 'source', 'url'):
                        current_post['mp4'] = item
                # Last item in JSON
                if path[0] == 'data' and path[1] == 'before':
                    break
            thread.join()
        else:
            return response.json()

    def generator_front(self, subreddit=None, order='hot', start_after='', limit=config.PAGE_ITEM_AMOUNT, check=False):
        """
        This function returns a generator which you can loop for posts
        
        """
        params = {
            'g': 'GLOBAL',
            'after': start_after,
            'before': '',
            'count': 0,
            'limit': limit,
        }
        
        endpoint = f'/{order}'
        logger.debug(f"endpoint {endpoint}")

        for post in self.request(endpoint, params=params, stream=True):
            if check:
                if not self.check(post):
                    continue
            yield post

        logger.debug(f"Used: {self.ratelimit_used}")

    def generator_subredit(self, subreddit='all', order='hot', start_after='', limit=config.PAGE_ITEM_AMOUNT, check=False):
        """
        This function returns a generator which you can loop for posts
        For normal subbredit and subreddit1+subreddit2 should work
        """
        params = {
            'g': 'GLOBAL',
            'after': start_after,
            'before': '',
            'count': 0,
            'limit': limit,
        }
        endpoint = f'r/{subreddit}/{order}'
        logger.debug(f"endpoint {endpoint}")
        
        for post in self.request(endpoint, params=params, stream=True):
            if check:
                if not self.check(post):
                    continue
            yield post

        logger.debug(f"Used: {self.ratelimit_used}")

    def generator_multi(self, subreddit='all', order='hot', start_after='', limit=config.PAGE_ITEM_AMOUNT, check=False):
        """
        This function returns a generator which you can loop for posts
        
        """
        params = {
            'g': 'GLOBAL',
            'after': start_after,
            'before': '',
            'count': 0,
            'limit': limit,
        }

        # TODO fix broken
        mine = self.request('/api/multi/mine')
        logger.debug(f"mine: {mine}")

        #endpoint_multi = f'/api/multi/{subreddit}'
        #subreddits = self.request(endpoint_multi)

        endpoint = 'r/'

        # Convert list of subbreddits in multi to endpoint
        for multi in mine:
            if multi['data']['name'] == subreddit:
                for subreddit in multi['data']['subreddits']:
                    endpoint += subreddit['name']
                    endpoint += '+'

        endpoint += f'empty/{order}'
        logger.debug(f"endpoint: {endpoint}")

        for post in self.request(endpoint, params=params, stream=True):
            if check:
                if not self.check(post):
                    continue
            yield post

        logger.debug(f"Used: {self.ratelimit_used}")

    def check(self, post: dict):
        """
        This function checks the quality of a post
        Posts with emoji are of usually lower quality
        Returns False when it needs to been filtered
        """
        try:
            #logger.debug(post)

            if post['score'] < 2:
                logger.info(f"Score filtered: http://old.reddit.com/comments/{post['id']}")
                return False

            # Check gif
            is_gif = False
            if 'gif' in post['url']:
                is_gif = True
            if 'mp4' in post['url']:
                is_gif = True

            # Delete emojis
            filtered = demoji.replace(post['title'], "")

            # Check if string with delete emojis is shorter
            if len(filtered) < len(post['title']) or \
                ':P' in post['title'] or \
                ';)' in post['title'] or \
                ':)' in post['title'] or \
                    '(;' in post['title']:

                logger.info(f"Emoji filtered: http://old.reddit.com/comments/{post['id']}")
                return False

            if 'OC' in post['title'] or \
                '(oc)' in post['title'] or \
                '[oc]' in post['title'] or \
                'my ' in post['title'] or \
                'My ' in post['title'] or \
                '?' in post['title'] or \
                'Self' in post['title'] or \
                'self' in post['title'] or \
                'f)' in post['title'] or \
                'F)' in post['title'] or \
                'f]' in post['title'] or \
                'F]' in post['title'] or \
                'm)' in post['title'] or \
                'M)' in post['title'] or \
                'm]' in post['title'] or \
                'M]' in post['title'] or \
                    'I ' in post['title']:

                logger.info(f"Post title filtered: http://old.reddit.com/comments/{post['id']}")
                return False

            if post['is_self']:
                logger.info(f"Self filtered: http://old.reddit.com/comments/{post['id']}")
                return False

            if post['is_original_content']:
                logger.info(f"OC filtered: http://old.reddit.com/comments/{post['id']}")
                return False

            if 'reddit.com' in post['url']:
                # TODO browse to post
                logger.info(f"X-post filtered: http://old.reddit.com/comments/{post['id']}")
                return False

            author_id = post['author_fullname']
            # TODO check author, probly not smart with rate limiter

            # Check for non utf8 characters
            post_title_utf8 = post['title'].encode('utf8', 'ignore').decode('utf8')
            if len(post_title_utf8) < len(post['title']):
                logger.debug(f"Warning post {post['name']} has non utf8 characters")

            return True

        except:
            logger.exception(f"Post failed: http://old.reddit.com/comments/{post['id']}")


# Test
if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    session = Reddit()
    logger.debug(f"Access token: {session.access_token}")
    response = session.request('/api/v1/me')
    logger.debug(f"Name: {response['name']}")
    for post in session.generator():
        logger.debug(f"Title: {post['title']}")
    logger.debug(f"Used: {session.ratelimit_used}")

