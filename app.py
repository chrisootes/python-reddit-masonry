#!python

import datetime
import logging

import config
import helpers.template
import helpers.reddit
import helpers.check
import template.post

logger = logging.getLogger(__name__)
reddit_session: helpers.reddit.Reddit = None

async def app(scope, receive, send):
    """
    Async app
    """
    try:
        #logger.debug(f"Scope: {scope}")

        if scope['type'] == 'lifespan':
            while True:
                message = await receive()
                # Handle startup event
                if message['type'] == 'lifespan.startup':
                    logger.info("Starting app")
                    global reddit_session
                    reddit_session = helpers.reddit.Reddit()
                    await send({'type': 'lifespan.startup.complete'})
                    return

                # Handle shudown event
                elif message['type'] == 'lifespan.shutdown':
                    logger.info("Stopping app")
                    await send({'type': 'lifespan.shutdown.complete'})
                    return

        elif scope['type'] != 'http':
            raise Exception("Unkown scope type")
        
        #logger.debug(f"Path: {scope['path']}")
        
        # Template helper
        t = helpers.template.Template(scope, receive, send)
        
        # Redit posts generator
        endpoint = ''
        #logger.debug(f"Match: {t.pget(1)}")
        match t.pget(1):
            case None:
                # front
                endpoint = "/hot"
            case '':
                # front
                endpoint = "/hot"
            case 'r':
                # subreddit
                if t.pget(3,'') == 'self':
                    return
                elif t.pget(2) is not None:
                    endpoint = f"/r/{t.pget(2)}/{t.pget(3,'hot')}"
                else:
                    await t.error()
            case 'm':
                # multi
                pass
            case _:
                await t.default()
                return

        # Load different templete for background
        post_formatter = None
        if t.qget('background', False):
            await t.load('template/background.html')
            post_formatter = template.post.background
        # Load default
        else:
            await t.load('template/default.html')
            post_formatter = template.post.default

        # Send template and get dynamic keys
        incomplete_key = ''
        next_after = ''
        async for key in t.generator(t.qget('raw', False)):
            # Template key: date
            if key == 'date':
                if not t.qget('raw', False):
                    await t.body(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            # Template key: items
            elif key == 'items':
                logger.debug(f"Sending {endpoint} on page {t.qget('after')}")
                for post in reddit_session.generator(endpoint, t.qget('after')):
                    # Used in template key: page
                    next_after = post['name']
                    if t.qget('check'):
                        if helpers.check.check(post):
                            await t.body(post_formatter(post))
                    else:
                        await t.body(post_formatter(post))

            # Template key: page
            elif key == 'page':
                if not t.qget('raw', False):
                    # Build next url with all options in query string so next page has also the options like order and check
                    next_url = f"{scope['path']}?after={next_after}&{t.query_string}"
                    logger.debug(f"next_url: {next_url}")
                    await t.body(next_url)

            # TODO Incomplete key
            else:
                incomplete_key += key
                raise Exception(f"TODO incomplete_key: {incomplete_key}")

                # Dont clear incomplete
                continue

            # Clear incomplete
            incomplete_key = ''

        # prevent RuntimeWarning: coroutine 'RequestResponseCycle.send' was never awaited
        await t.latest_send_future

                
    except Exception as e:
        logger.exception("Catched exception")
        await send({
            'type': 'http.response.start',
            'status': 500,
        })
        await send({
            'type': 'http.response.body',
            'body': str(e).encode('utf-8'),
            'more_body': False
        })


