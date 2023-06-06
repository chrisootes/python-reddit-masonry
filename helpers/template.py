#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import logging
import urllib.parse
import mimetypes

import aiofiles

import config

logger = logging.getLogger(__name__)

class Template:
    def __init__(self, scope: dict, receive, send):
        self.filename = ''
        self.file = None
        self.scope = scope
        self.receive = receive
        self.send = send
        self.path = scope['path']
        self.path_relative = scope['path'][1:]
        self.path_splitted = scope['path'].split('/')
        self.query_string = scope['query_string'].decode('utf-8')
        self.query_string_parsed = urllib.parse.parse_qs(self.query_string)
        self.latest_send_future = None

    def pget(self, index, default=None):
        try:
            return self.path_splitted[index]
        except IndexError:
            return default

    def qget(self, key, default=''):
        return self.query_string_parsed.get(key, [default])[0]
        
    async def error(self):
        await self.send({
            'type': 'http.response.start',
            'status': 404,
            'headers': [
                [b'content-type', b'text/html'],
            ],
        })

    async def body(self, body='', more_body=True):
        if self.latest_send_future is not None:
            await self.latest_send_future

        if isinstance(body, str):
            self.latest_send_future = self.send({
                'type': 'http.response.body',
                'body': body.encode('utf-8'),
                'more_body': more_body
            })
        elif isinstance(body, bytes):
            self.latest_send_future = self.send({
                'type': 'http.response.body',
                'body': body,
                'more_body': more_body
            })
        else:
            raise Exception(f"Unkown body type: {type(body)}")

    async def default(self):
        # default file
        file_type = mimetypes.guess_type(self.path_relative)[0] or 'text/plain'
        logger.debug(f"Default routing to file: {self.path_relative} with type: {file_type}")
        try:
            static_file = await aiofiles.open(self.path_relative, mode='rb')
        except IOError as e:
            logger.error(f"Requested file: {self.path_relative} with type: {file_type} not found")
            # Send 404 header
            await self.send({
                'type': 'http.response.start',
                'status': 404,
            })
        else:
            # Send header
            await self.send({
                'type': 'http.response.start',
                'status': 200,
                'headers': [
                    [b'content-type', file_type.encode('utf-8')],
                ],
            })
            # Send file contents
            more_body = True
            while more_body:
                data = await static_file.read(config.FILE_BLOCK_SIZE)
                more_body = len(data) == config.FILE_BLOCK_SIZE
                await self.body(data, more_body)

            # prevent RuntimeWarning: coroutine 'RequestResponseCycle.send' was never awaited
            await self.latest_send_future

    async def load(self, filename):
        self.filename = filename
        self.file = await aiofiles.open(filename, mode='r')

    async def generator(self, raw):
        # Loop template
        await self.send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [
                [b'content-type', b'text/html'],
            ],
        })
        more_body = True
        dollar_count = 0
        while more_body:
            data = await self.file.read(config.FILE_BLOCK_SIZE)
            more_body = len(data) == config.FILE_BLOCK_SIZE
            for i, split_part in enumerate(data.split('$')):
                #logger.debug(f"Splitted part: {split_part}")
                if i > 0:
                    dollar_count += 1
                # Static content
                if dollar_count % 2 == 0:
                    if not raw:
                        await self.body(split_part)
                # Dynamic content
                else:
                    yield split_part

        # End more body
        await self.body('', False)
