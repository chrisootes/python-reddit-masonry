#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import urllib.parse
import queue
import threading

import requests
import requests.auth
import json_stream
import json_stream.requests

import config

logger = logging.getLogger(__name__)

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
            raise Exception(f"Invalid status code response: {status_code}")
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
                elif len(path) == 6:
                    if path == ('data', 'children', path[2], 'data', 'media', 'reddit_video', 'dash_url'):
                        current_post['dash_url'] = item

                # Last item in JSON
                if path[0] == 'data' and path[1] == 'before':
                    break
            thread.join()
        else:
            return response.json()

    def generator(self, endpoint='', start_after='', limit=20):
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

        logger.debug(f"endpoint {endpoint}")

        for post in self.request(endpoint, params=params, stream=True):
            yield post

        logger.debug(f"Used: {self.ratelimit_used}")

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

