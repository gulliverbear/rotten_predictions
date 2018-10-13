#!/usr/bin/python

'''
3/3/18
Scrape a particular movie to report when reviews are posted

3/25/18
changing script so that it only saves a file when there is a change!
'''

import requests
from bs4 import BeautifulSoup
import re
import time
import datetime
import os
import sys
import json

movie_to_rt = {}
movies_to_check = movie_to_rt.values()

movies_to_skip = []

REVIEW_PATH = 'saved_reviews'

def get_reviews(movie):
    '''
    Returns the # of reviews for a given movie
    '''
    url = 'http://www.rottentomatoes.com/m/{}/'.format(movie)

    text = requests.get(url).text

    p = re.compile('All Critics \((\d+)\)')

    m = p.search(text)

    if not m:
        return 0
    else:
        return int(m.group(1))

def check_movies(movies_to_check, movies_to_skip):
    '''
    Given a list of movies to check (and movies to skip)
    It will get the # of reviews for each one
    Returns a dict with movie:# of reviews
    '''
    # need to read in guess_path
    movie_to_reviews = {}
    for movie in movies_to_check:
        if movie not in movies_to_skip:
            movie_to_reviews[movie] = get_reviews(movie)
            time.sleep(60)

    return movie_to_reviews

def save_json(d):
    '''
    Gets the filename with path for current moment in time
    Saves the json
    '''
    now_str = str(datetime.datetime.now())
    year_month_day = now_str.split()[0]
    hour_min = '_'.join(now_str.split()[1].split(':')[:2])

    filename_with_time = 'review_check_{}_{}.json'.format(
        year_month_day,
        hour_min,
    )

    filename_with_path = os.path.join(REVIEW_PATH, filename_with_time)

    with open(filename_with_path, 'w') as FHOUT:
        json.dump(d, FHOUT)

def initialize(movies_to_check, movies_to_skip):
    '''
    Run this the first time to create a json file
    '''
    movie_to_reviews = check_movies(movies_to_check, movies_to_skip)
    save_json(movie_to_reviews)


if __name__ == '__main__':
    #initialize(movies_to_check, movies_to_skip)

    dont_save_first = True # set to True means it wont save the first json
    # this is so when you restart after removing a movie it won't save the first file

    if len(movies_to_check) - len(movies_to_skip) > 50:
        sys.exit('Too many movies!!!')

    last_review_file = os.path.join(REVIEW_PATH, 'review_check_2018-03-30_09_23.json')

    with open(last_review_file) as FH:
        last_movie_to_reviews = json.load(FH)

    while True:
        try:
            current_movie_to_reviews = check_movies(movies_to_check, movies_to_skip)
        except:
            print('Something went wrong\n{}\n{}'.format(
                sys.exc_info()[0],
                sys.exc_info()[1],
                sys.exc_info()[2],
            ))

        if current_movie_to_reviews != last_movie_to_reviews:
            if dont_save_first:
                dont_save_first = False
            else:
                save_json(current_movie_to_reviews)
                
                print('\n###')
                print('\nNew json file saved at {}'.format(datetime.datetime.now()))

                # dicts could not be equal due to a new movie being added, if so we don't want an alert about that
                # so check each movie individually to see

                new_reviews = []
                for movie in current_movie_to_reviews:
                    if current_movie_to_reviews[movie] != last_movie_to_reviews.get(movie, 0):
                        new_reviews.append(movie)
                if new_reviews:
                    print('New reviews detected for:')
                    for movie in new_reviews:
                        print(movie)
                print('###\n')
            last_movie_to_reviews = current_movie_to_reviews
        else:
            print('No new reviews at {}'.format(datetime.datetime.now()))

        # sleep until the next hour (will be a problem if have more than 60 movies to check!)
        time.sleep(60 * (60 - datetime.datetime.now().minute))
