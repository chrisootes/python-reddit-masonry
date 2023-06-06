
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