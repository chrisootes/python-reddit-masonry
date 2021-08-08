#!python

import time
import datetime
from urllib import parse

import requests

import config
import streamer
import reddit

def format_post(post) -> str:
    good_content = reddit.check(post)
    if good_content:
        parsed = parse.urlparse(post.url)
        response = requests.head(post.url)
        print(f"Sending {post.id}")
        content_type = response.headers.get('content-type', '')
        print(f"Content type {content_type}")
        if 'image' in content_type:
            return f"""
                <div id="{post.id}" class="col-sm-12 col-lg-6 col-xxl-4">
                    <div class="card">
                        <img class="card-img-top" src="{post.url}">
                        <div class="card-body">
                            <h5 class="card-title">{post.title} <a href="http://old.reddit.com/comments/{post.id}" class="btn btn-primary">Comments</a></h5>
                        </div>
                    </div>
                </div>
            """
        elif 'imgur' in post.url:
            imgur_id = parsed.path.split('.')[0].split('/')[-1]
            return f"""
                <div id="{post.id}" class="col-sm-12 col-lg-6 col-xxl-4">
                    <div class="card">
                        <iframe allowfullscreen="true" mozallowfullscreen="true" webkitallowfullscreen="true" class="imgur-embed-iframe-pub" scrolling="no" src="http://imgur.com/{imgur_id}/embed" id="imgur-embed-iframe-pub-{imgur_id}"></iframe>
                        <div class="card-body">
                            <h5 class="card-title">{post.title} <a href="http://old.reddit.com/comments/{post.id}" class="btn btn-primary">Comments</a></h5>
                        </div>
                    </div>
                </div>
            """
        elif 'redgif' in post.url:
            redgifs_id = parsed.path.split('.')[0].split('/')[-1]
            return f"""
                <div id="{post.id}" class="col-sm-12 col-lg-6 col-xxl-4">
                    <div class="card">
                        <div style='position:relative; padding-bottom:88.67%;'>
                            <iframe src='https://redgifs.com/ifr/{redgifs_id}' frameborder='0' scrolling='no' width='100%' height='100%' style='position:absolute;top:0;left:0;' allowfullscreen></iframe>
                        </div>
                        <div class="card-body">
                            <h5 class="card-title">{post.title} <a href="http://old.reddit.com/comments/{post.id}" class="btn btn-primary">Comments</a></h5>
                        </div>
                    </div>
                </div>
            """
        elif content_type == '':
            return f"""
                <div id="{post.id}" class="col-sm-12 col-lg-6 col-xxl-4">
                    <div class="card">
                        <div class="card-body">
                            <div class="d-grid gap-2">
                                <a href="{post.url}" class="btn btn-secondary">Video</a>
                            </div>
                            <h5 class="card-title">{post.title} <a href="http://old.reddit.com/comments/{post.id}" class="btn btn-primary">Comments</a></h5>
                        </div>
                    </div>
                </div>
            """
        elif 'text/html' in content_type:
            return f"""
                <div id="{post.id}" class="col-sm-12 col-lg-6 col-xxl-4">
                    <div class="card">
                        <div class="card-body">
                            <div class="d-grid gap-2">
                                <a href="{post.url}" class="btn btn-primary">Link</a>
                            </div>
                            <h5 class="card-title">{post.title} <a href="http://old.reddit.com/comments/{post.id}" class="btn btn-primary">Comments</a></h5>
                        </div>
                    </div>
                </div>
            """
        else:
            print("TODO")
    return ''


def streamer_callback(path: str):
    """
    Callback generator that yields utf-8 bytes of html
    """

    # parse path
    path_parsed = parse.urlparse(path)
    #print(f"Path: {path_parsed}")
    splitted = path_parsed.path.split('/')
    subreddit = 'all'
    if len(splitted) > 1:
        if splitted[1] != '':
            subreddit = splitted[1]
    page = ''
    if len(splitted) > 2:
        page = splitted[2]

    # parse query
    query = parse.parse_qs(path_parsed.query)
    infinite = query.get('infinite', False)
    
    if infinite:
        print(f"Infinite {subreddit} on page {page}")
        posts = reddit.generator(subreddit=subreddit, last_id=page, amount=config.PAGE_ITEM_AMOUNT)
        for post in posts:
            last_id = post.id
            yield format_post(post).encode('utf-8')

    else:
        template = open('template_page.html', 'r')
        
        # Loop template
        while True:
            line = template.readline()
            # Chek for end file
            if line == '':
                break
            # Check for template item
            elif '$' in line:
                splitted = line.split('$')
                #print(f"Splitted template: {splitted}")
                # Send everythin before first $
                yield splitted[0].encode('utf-8')
                # Send between
        
                # Template key: date
                if splitted[1] == 'date':
                    yield datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S").encode('utf-8')

                # Template key: page
                elif splitted[1] == 'page':
                    yield f"/{subreddit}/{last_id}".encode('utf-8')

                # Template key: items
                elif splitted[1] == 'items':
                    print(f"Getting {subreddit} on page {page}")
                    posts = reddit.generator(subreddit=subreddit, last_id=page, amount=config.PAGE_ITEM_AMOUNT)
                    for post in posts:
                        last_id = post.id
                        yield format_post(post).encode('utf-8')

                # Send everythin after second $
                yield splitted[2].encode('utf-8')

            # Everything else is static content
            else:
                yield line.encode('utf-8')


if __name__ == "__main__":
    streamer.create_server(
        config.SERVER_HOSTNAME,
        config.SERVER_PORT,
        config.STATIC_FILES,
        streamer_callback)
