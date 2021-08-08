#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import time
import traceback
import urllib.request
from datetime import datetime

import demoji
import praw
import praw.models

import config

# demoji.download_codes()

reddit = praw.Reddit(
    client_id=config.CLIENT_ID,
    client_secret=config.CLIENT_SECRET,
    password=config.PASSWORD,
    username=config.USERNAME,
    user_agent="PRAW",
    redirect_uri="old.reddit.com")

print(f"Logged in as: {reddit.user.me()}")


def generator(subreddit='all', last_id='', amount=config.PAGE_ITEM_AMOUNT):
    """
    This function returns a generator which you can loop for posts
    """
    params = {}
    if last_id != '':
        params['after'] = f't3_{last_id}'

    # frontpage/subscribed
    if subreddit == 'front':
        return reddit.front.top(time_filter='week', limit=amount, params=params)
    
    # simple hack to search for users multi
    elif 'multi' in subreddit:
        for multireddit in reddit.user.multireddits():
            print(multireddit.display_name)
            if multireddit.display_name == subreddit:
                return multireddit.new(limit=amount, params=params)
    
    # normal subbredit
    # subreddit1+subreddit2 should work
    else:
        return reddit.subreddit(subreddit).hot(limit=amount, params=params)


def check(post: praw.models.Submission):
    """
    This function checks the quality of a post
    Posts with emoji are of usually lower quality
    """
    try:
        # Check gif
        is_gif = False
        if 'gif' in post.url:
            is_gif = True
        if 'mp4' in post.url:
            is_gif = True

        # Delete emojis
        filtered = demoji.replace(post.title, "")

        # Check if string with delete emojis is shorter
        if len(filtered) < len(post.title) or \
            ':P' in post.title or \
            ';)' in post.title or \
            ':)' in post.title or \
                '(;' in post.title:

            print(f"Emoji filtered: {post.id}")
            return False

        if 'OC' in post.title or \
            '(oc)' in post.title or \
            '[oc]' in post.title or \
            'my ' in post.title or \
            'My ' in post.title or \
            '?' in post.title or \
            'Self' in post.title or \
            'self' in post.title or \
            'f)' in post.title or \
            'F)' in post.title or \
            'f]' in post.title or \
            'F]' in post.title or \
            'm)' in post.title or \
            'M)' in post.title or \
            'm]' in post.title or \
            'M]' in post.title or \
                'I ' in post.title:

            print(f"Post title filtered: {post.id}")
            return False

        if post.is_self:
            print(f"Self filtered: {post.id}")
            return False

        if 'reddit.com' in post.url:
            # TODO browse to post
            print(f"X-post filtered: {post.id}")
            return False

        # This should filter out author.name not existing
        author_name = ''
        try:
            author_name = post.author.name
            author_joined = "0001-01-01"
            author_description = ""
            try:
                author_joined = datetime.utcfromtimestamp(int(post.author.created_utc))
                author_joined_str = author_joined.strftime("%Y-%m-%d")

                # TODO check author description
                # was post.author.subreddit["public_description"]

                # TODO check stickied posts

            except:
                print(f"Probably banned/suspended account: {post.id} ")
                return False
        except:
            print(f"Probably deleted/removed account: {post.id}")
            return False

        # Check for non utf8 characters
        post_title_utf8 = post.title.encode('utf8', 'ignore').decode('utf8')
        if len(post_title_utf8) < len(post.title):
            print(f"Warning post {post.id} has non utf8 characters")

        return True

    except KeyboardInterrupt:
        print("Stopping")
        quit()

    except:
        print(f"Post failed: {post.id}")
        traceback.print_exc()


# Test
if __name__ == "__main__":
    test = generator()
    last_id = ''
    for i in test:
        post_url, last_id = check(i)
    print(last_id)
    test = generator(last_id=last_id)
    for i in test:
        post_url, last_id = check(i)
    print(last_id)
