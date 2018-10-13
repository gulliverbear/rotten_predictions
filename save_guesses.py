#!/usr/bin/python

'''
3/2/18

Run daily to save all the guesses from reddit into a pickle file
It saves the comment text and the date it was created
It doesn't do any parsing of the comment at this stage

Future goals:
Use a database
'''

import praw
import cPickle as pickle
import datetime
import time
import os
import sys

# to do: read in USER_NAME, CLIENT_ID, CLIENT_SECRET from json file
# also read in subreddit_name, guess path, and movie_users_file

non_movie_titles = [
    'Subreddit Suggestions',
    ]

def get_comments(subreddit_name, non_movie_titles, filename, guess_path):
    '''
    Build dict of dict:
    [movie][user] = (comment, date)
    If same user has multiple comments, take the newest comment
    '''
    r = praw.Reddit(client_id=CLIENT_ID,
    client_secret= CLIENT_SECRET,
    user_agent = 'check movie guesses by {}'.format(USER_NAME))

    movie_users = {}

    n_movies = 0
    n_comments = 0

    for submission in r.subreddit(subreddit_name).new(limit=100):
        movie = submission.title

        if movie in non_movie_titles or 'Weekly Discussion' in movie:
            continue # avoid any non-movie posts

        n_movies += 1
        movie_users[movie] = {}
        seen_users = set()

        for top_level_comment in submission.comments:
            comment = (
                top_level_comment.body.encode('utf-8'),
                top_level_comment.created
            )

            user = top_level_comment.author
            current_comment_date = datetime.datetime.fromtimestamp(top_level_comment.created)

            if user in seen_users:
                other_comment = movie_users[movie][user]
                other_comment_date = datetime.datetime.fromtimestamp(other_comment[1])

                if current_comment_date < other_comment_date:
                    # the previous comment is newer, so don't replace it
                    continue

            n_comments += 1
            seen_users.add(user)
            movie_users[movie][user] = comment

    now_str = str(datetime.datetime.now())
    year_month_day = now_str.split()[0]
    hour_min = '_'.join(now_str.split()[1].split(':')[:2])
    file_base = filename.split('.')[0]
    file_suffix = filename.split('.')[1]

    filename_with_time = '{}_{}_{}.{}'.format(
        file_base,
        year_month_day,
        hour_min,
        file_suffix,
    )

    filename_with_path = os.path.join(guess_path, filename_with_time)
    #print(filename_with_path)
    pickle.dump(movie_users, open(filename_with_path,'wb'))

    print('Found {} movies and {} total comments\n'.format(n_movies, n_comments))

if __name__ == '__main__':
    while True:
        print('Grabbing guesses at {}'.format(datetime.datetime.now()))
        try:
            get_comments(subreddit_name, non_movie_titles, movie_users_file, guess_path)
        except:
            print('Something went wrong\n{}'.format(sys.exc_info()[0]))
    # 86400 seconds in 24 hours
    # 21600 to check every 6 hours
    # 3600 every hour
        time.sleep(3600)
    
