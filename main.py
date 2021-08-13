#!python

import datetime
import urllib.parse
import logging

import config
import server
import reddit

logger = logging.getLogger(__name__)

def format_post(post: dict) -> str:
    """
    This function generates a embedded card html code from a PRAW post object
    """
    good_content = reddit.session.check(post)
    if good_content:
        parsed = urllib.parse.urlparse(post['url'])
        logger.debug(f"Sending post: {post['name']}")
        if 'i.redd.it' in post['url']:
            return f"""
                <div id="{post['name']}" class="col-sm-12 col-lg-6 col-xxl-4">
                    <div class="card">
                        <img class="card-img-top" src="{post['url']}">
                        <div class="card-body">
                            <h5 class="card-title">{post['title']} <a href="http://old.reddit.com/comments/{post['id']}" class="btn btn-primary">Comments</a></h5>
                        </div>
                    </div>
                </div>
            """
        elif 'v.redd.it' in post['url']:
            if post['media'] is not None:
                return f"""
                    <div id="{post['name']}" class="col-sm-12 col-lg-6 col-xxl-4">
                        <div class="card">
                            <video data-dashjs-player autoplay src="{post['media']['reddit_video']['dash_url']}" controls></video>
                            <div class="card-body">
                                <h5 class="card-title">{post['title']} <a href="http://old.reddit.com/comments/{post['id']}" class="btn btn-primary">Comments</a></h5>
                            </div>
                        </div>
                    </div>
                """
        elif 'imgur' in post['url'] and ('gif' in post['url'] or 'mp4' in post['url']):
            imgur_id = parsed.path.split('.')[0].split('/')[-1]
            return f"""
                <div id="{post['name']}" class="col-sm-12 col-lg-6 col-xxl-4">
                    <div class="card">
                        <video controls poster="//i.imgur.com/{imgur_id}.jpg" preload="auto" autoplay="autoplay" muted="muted" loop="loop" webkit-playsinline="" style="width: 100%; height: 100%;">
                            <source src="//i.imgur.com/{imgur_id}.mp4" type="video/mp4">
                        </video>
                        <div class="card-body">
                            <h5 class="card-title">{post['title']} <a href="http://old.reddit.com/comments/{post['id']}" class="btn btn-primary">Comments</a></h5>
                        </div>
                    </div>
                </div>
            """
        elif 'imgur' in post['url']:
            imgur_id = parsed.path.split('.')[0].split('/')[-1]
            return f"""
                <div id="{post['name']}" class="col-sm-12 col-lg-6 col-xxl-4">
                    <div class="card">
                        <blockquote class="imgur-embed-pub" lang="en" data-id="{imgur_id}" ><a href="{post['url']}">{post['title']}</a></blockquote><script async src="//s.imgur.com/min/embed.js" charset="utf-8"></script>
                        <div class="card-body">
                            <h5 class="card-title">{post['title']} <a href="http://old.reddit.com/comments/{post['id']}" class="btn btn-primary">Comments</a></h5>
                        </div>
                    </div>
                </div>
            """
        elif 'redgif' in post['url']:
            redgifs_id = parsed.path.split('.')[0].split('/')[-1]
            return f"""
                <div id="{post['name']}" class="col-sm-12 col-lg-6 col-xxl-4">
                    <div class="card">
                        <div style='position:relative; padding-bottom:88.67%;'>
                            <iframe src='https://redgifs.com/ifr/{redgifs_id}' frameborder='0' scrolling='no' width='100%' height='100%' style='position:absolute;top:0;left:0;' allowfullscreen></iframe>
                        </div>
                        <div class="card-body">
                            <h5 class="card-title">{post['title']} <a href="http://old.reddit.com/comments/{post['id']}" class="btn btn-primary">Comments</a></h5>
                        </div>
                    </div>
                </div>
            """
        else:
            thumbnail = post.get('thumbnail', 'http://localhost/favicon.ico')
            return f"""
                <div id="{post['name']}" class="col-sm-12 col-lg-6 col-xxl-4">
                    <div class="card">
                        <a href="{post['url']}"><img class="card-img-top" src="{thumbnail}"></a>
                        <div class="card-body">
                            <h5 class="card-title">{post['title']} <a href="http://old.reddit.com/comments/{post['id']}" class="btn btn-primary">Comments</a></h5>
                        </div>
                    </div>
                </div>
            """
    return ''


def streamer_callback(self: server.RequestHandler, path: str):
    """
    Callback generator for the streamer server that yields utf-8 bytes of html code
    """
    
    # TODO if subbredit does not exist 404
    self.send_response(200)
    self.send_header("Content-type", "text/html")
    self.end_headers()

    # Parse path
    path_parsed = urllib.parse.urlparse(path)
    #logger.debug(f"Path: {path_parsed}")
    splitted = path_parsed.path.split('/')
    subreddit = 'all'
    if len(splitted) > 1:
        if splitted[1] != '':
            subreddit = splitted[1]
    first_id = ''
    if len(splitted) > 2:
        first_id = splitted[2]

    if subreddit == 'undefined':
        logger.warning(f"Page not completly loaded previously")
        return
        
    # Parse query
    query = urllib.parse.parse_qs(path_parsed.query)
    items_only = query.get('items_only', False)
    
    if items_only:
        logger.debug(f"Items only {subreddit} on after {first_id}")
        posts = reddit.session.generator(subreddit=subreddit, start_after=first_id)
        for post in posts:
            last_id = post['name']
            yield format_post(post)

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
                #logger.debug(f"Splitted template: {splitted}")
                # Send everythin before first $
                yield splitted[0]
                # Send between
        
                # Template key: date
                if splitted[1] == 'date':
                    yield datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # Template key: page
                elif splitted[1] == 'page':
                    yield f"/{subreddit}/{last_id}"

                # Template key: items
                elif splitted[1] == 'items':
                    logger.debug(f"Getting {subreddit} on page {first_id}")
                    posts = reddit.session.generator(subreddit=subreddit, start_after=first_id)
                    for post in posts:
                        last_id = post['name']
                        yield format_post(post)

                # Send everythin after second $
                yield splitted[2]

            # Everything else is static content
            else:
                yield line


if __name__ == "__main__":
    reddit.session = reddit.Reddit()
    server.create_server(
        config.SERVER_HOSTNAME,
        config.SERVER_PORT,
        config.STATIC_FILES,
        streamer_callback)
