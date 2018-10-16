#!/usr/bin/python


from __future__ import division
import praw
import sys
import prawcore
import re
import cPickle as pickle
import datetime
import numpy as np
import os
import requests
import time
import collections
import operator
import matplotlib as mpl
mpl.use('agg')
import matplotlib.pyplot as plt

# read in USER_NAME, CLIENT_ID, CLIENT_SECRET, subreddit_name, movie_users_file

non_movie_titles = [
    'Subreddit Suggestions',
    ]

# movies where reviews have been parsed
# these are movies that we will score against
movie_to_guesses = {}

# for specific summer contest
movie_to_guesses_contest = {}

# when adding a new movie here, make sure to also add it to scrape_rt_new!
movie_to_rt = {}


# add new movie here and then run print_upcoming to get the printout for the sidebar 
movie_to_reddit = {}

movies_to_skip = []

def get_comments(subreddit_name, non_movie_titles, filename):
    '''
    Build dict of dict:
    [movie][user] = (comment, date)
    If same user has multiple comments, take the newest comment
    '''
    r = praw.Reddit(client_id=CLIENT_ID,
    client_secret= CLIENT_SECRET,
    user_agent = 'check movie guesses by {}'.format(USER_NAME))

    movie_users = {}

    for submission in r.subreddit(subreddit_name).new(limit=100):
        movie = submission.title

        if movie in non_movie_titles:
            continue # avoid any non-movie posts

        movie_users[movie] = {}
        seen_users = set()

        print(movie)

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

    pickle.dump(movie_users, open(filename_with_time,'wb'))

def parse_guesses(filename):
    '''
    Reads a pickle file that contains a dict with
    key = movie, val = dict with key = user, val = comment
    writes out a pickle file with dict with
    key = movie, val = dict with key = user, val = guess

    This file is called movie_guesses
    '''
    movie_users = pickle.load(open(filename,'rb'))

    number_pattern = re.compile('(\d+)') # captures all numbers

    movie_guesses = {}

    for movie in movie_users.keys():
        movie_guesses[movie] = {}

        for user in movie_users[movie]:
            # comment is the 1st element of tuple
            comment = movie_users[movie][user][0]

            matches = number_pattern.findall(comment)

            valid_numbers = [int(n) for n in matches if 0<=int(n)<=100]

            if len(valid_numbers) > 1:
                print('>1 number:\n', comment)
                guess = int(raw_input('What should guess be? '))
            elif len(valid_numbers) == 0:
                print('no numbers:\n', comment)
                guess = int(raw_input('What should guess be? '))
            else: 
                guess = valid_numbers[0]

            movie_guesses[movie][user] = guess

    # the pickle file will be movie_guesses_2018-XX-XX_XX_XX.pickle
    filename = filename.replace('users', 'guesses')

    pickle.dump(movie_guesses, open(filename,'wb'))

def parse_guesses_for_single_movie(filename, movie):
    '''
    Reads a pickle file that contains a dict with
    key = movie, val = dict with key = user, val = comment
    writes out a pickle file with dict with
    key = user, val = guess

    This file is called <movie>_YYYY-MM-DD.pickle
    '''
    movie_users = pickle.load(open(filename,'rb'))

    number_pattern = re.compile('(\d+)') # captures all numbers

    movie_guesses = {}

    for user in movie_users[movie]:
        if user is None:
            continue
            # case where user a comment was [deleted]
        # comment is the 1st element of tuple
        comment = movie_users[movie][user][0]

        matches = number_pattern.findall(comment)

        valid_numbers = [int(n) for n in matches if 0<=int(n)<=100]

        if len(valid_numbers) > 1:
            print('>1 number:\n', comment, str(user))
            try:
                guess = int(raw_input('What should guess be? '))
            except:
                guess = None
        elif len(valid_numbers) == 0:
            print('no numbers:\n', comment)
            try:
                guess = int(raw_input('What should guess be? '))
            except:
                guess = None
        else: 
            guess = valid_numbers[0]
        if guess is not None:
            #print(user, guess)
            movie_guesses[user] = guess
        else:
            print('Recorded no guess for that comment')

    # the pickle file will be <movie>_2018-XX-XX_XX_XX.pickle
    movie_underscores = '_'.join(movie.split()).lower()
    movie_underscores = movie_underscores.replace(':','')
    movie_underscores = movie_underscores.replace('?','')
    movie_underscores = movie_underscores.replace('/','')
    date_part = '_'.join(filename.split('_')[-3:])
    new_filename = '{}_{}'.format(movie_underscores, date_part)
    new_filename_with_path = os.path.join('parsed_guesses', new_filename)

    pickle.dump(movie_guesses, open(new_filename_with_path,'wb'))

def plot_hist(filename, movie_choice=None):
    '''
    Reads in a movie_guesses pickle file
    Plots histogram of guesses for a movie
    '''
    movie_guesses = pickle.load(open(filename,'rb'))

    if movie_choice:
        n_movies = 1
    else:
        n_movies = len(movie_guesses.keys())

    n = 1
    fig = plt.figure(num=1, figsize=(10, 4*n_movies))
    fig.clear()

    for movie in movie_guesses.keys():
        if movie_choice and movie != movie_choice:
            continue

        counts = [0]*101 # for 0-100
        guesses = []
        for user in movie_guesses[movie].keys():
            guess = movie_guesses[movie][user]
            guesses.append(guess)
            counts[guess] += 1

        mean = np.mean(guesses)
        median = np.median(guesses)
        stdev = np.std(guesses, ddof=1)

        ax = fig.add_subplot(n_movies, 1, n)
        ax.set_title(movie)
        ax.set_xlabel('Rotten Tomato Predictions')
        ax.set_ylabel('Count')
        #ax.bar(xrange(101), counts)
        ax.hist(guesses, bins=10)
        ax.set_xlim([0,101])
        ax.axvline(x=mean, color='red', linewidth=2)
        ax.axvline(x=median, color='red', linewidth=2, linestyle='--')

        if mean < 40:
            x_text = 0.8
        else:
            x_text = 0.1
        ax.text(x_text, .9, 'mean: {:.2f}'.format(mean), transform=ax.transAxes)
        ax.text(x_text, .8, 'median: {:.2f}'.format(median), transform=ax.transAxes)
        ax.text(x_text, .7, 'st dev: {:.2f}'.format(stdev), transform=ax.transAxes)

        movie = movie.replace(':', '-')

        n += 1

    fig.tight_layout()
    if movie_choice:
        fig.savefig('{}.png'.format(movie))
    else:
        fig.savefig('All_movies.png')

def get_all_movies(pickle_file):
    '''
    Returns list of all movies from a pickle file
    '''
    movie_guesses = pickle.load(open(pickle_file,'rb'))
    return movie_guesses.keys()

def get_stats(movie_list, guesses_file):
    '''
    Prints stats on mean, median, std dev for all movies in given list
    '''
    movie_guesses = pickle.load(open(guesses_file,'rb'))

    lines = []
    for movie in movie_list:
        guesses = movie_guesses[movie].values()

        mean = np.mean(guesses)
        median = np.median(guesses)
        stdev = np.std(guesses, ddof=1)

        mean, median, stdev = ['{:.2f}'.format(i) for i in (mean, median, stdev)]

        line = '\t'.join([i for i in (movie, mean, median, stdev)])
        lines.append(line)

    print('Movie\tMean\tMedian\tStd Dev')
    for line in lines:
        print(line)

def print_upcoming(movie_to_rt, movie_to_reddit, movies_to_skip):
    '''
    Reads in movie_users pickle file
    For each movie it gets the corresponding RT url
    It then goes and gets the release date
    It prints out a list sorted by newest to latest release dates
    Prints out to a file called 'Upcoming_releases.txt'
    '''

    special_cases = {}

    bold_movies = []

    movies = movie_to_rt.keys()

    lines = []
    p = re.compile('[A-Z][a-z][a-z] \d+, 20\d\d')
    for movie in movies:
        if movie in movies_to_skip:
            continue
        url = 'https://www.rottentomatoes.com/m/{}/'.format(movie_to_rt[movie])

        text = requests.get(url).text

        m = p.search(text)
        if not m:
            print('Unable to find a date in the url for movie {}'.format(movie))
            if movie in special_cases:
                print('Date was added as a special case')
                m = p.search(special_cases[movie])
            else:
                continue
        date = datetime.datetime.strptime(m.group(0), '%b %d, %Y')
        strike = bold = ''
        if date < datetime.datetime.now() or movie in movies_to_skip:
            strike = '~~'
        if movie in bold_movies:
            bold = '**'
        reddit_url = 'https://www.reddit.com/r/rottenpredictions/comments/{}'.format(movie_to_reddit[movie])
        line = '{4}{3}{0}\t[{1}]({2}){3}{4}\n\n'.format(m.group(0), movie, reddit_url, strike, bold)
        lines.append((date, line))
        time.sleep(10)

    # sort by the date
    lines.sort(key=operator.itemgetter(0, 1))
    output_file = 'upcoming_releases.txt'
    with open(output_file, 'w') as FHOUT:
        for line in lines:
            FHOUT.write(line[1])

def score_guesses_contest(movie_to_guesses, subreddit_name):
    '''
    Just for the summer movie contest
    lots of duplicate code with score_guesses so I should clean it up later...
    Just makes a top ten list if you have entered in each summer movie
    edit - changing it to allow for 1 not entered since I didn't enter Jurassic World
    '''
    # get refresh token
    r = praw.Reddit(client_id=CLIENT_ID,
        client_secret= CLIENT_SECRET,
        user_agent = 'set user flair by {}'.format(USER_NAME),
        refresh_token = refresh_token,
    )

    p = re.compile('ratingValue":(\d+),')

    movie_names = [movie for movie in movie_to_guesses.keys()]
    user_to_deltas = collections.defaultdict(list)
    movie_user_delta = {} # to be able to print the delta for each movie for each user

    for movie in movie_names:
        movie_user_delta[movie] = {}

    
    # get current tomatometer for each movie
    for movie, parsed_guesses_file in movie_to_guesses.items():
        url = 'http://www.rottentomatoes.com/m/{}/'.format(movie_to_rt[movie])
        text = requests.get(url).text
        m = p.search(text)

        if not m:
            sys.exit('Unable to get tomato meter for {}'.format(movie))
        tomato_meter = int(m.group(1))
        print(movie, tomato_meter)
        
        parsed_guesses_file = os.path.join('parsed_guesses', parsed_guesses_file)
        user_guesses = pickle.load(open(parsed_guesses_file,'rb'))

        for user, guess in user_guesses.items():
            delta = abs(guess - tomato_meter)

            movie_user_delta[movie][user] = delta
            user_to_deltas[user].append(delta)
            if delta == 0:
                print(user, movie)

        time.sleep(10)

    # now find users that have made guesses for all the contest movies
    min_guesses = len(movie_to_guesses)-1

    user_median_mean_best_guesses = []
    for user, deltas in user_to_deltas.items():
        user_name = str(user)
        abs_deltas = sorted(deltas)[:min_guesses] # get the smallest deltas (drop highest one)
        sum_deltas = sum(abs_deltas)
        # median_delta = np.median(abs_deltas)
        # mean_delta = np.mean(abs_deltas)
        # best_delta = min(abs_deltas)

        if len(deltas) >= min_guesses:
            # user_median_mean_best_guesses.append((user_name, sum_deltas, median_delta, mean_delta, best_delta))
            movies_for_this_user = []
            for movie in movie_names:
                movies_for_this_user.append(movie_user_delta[movie].get(user, 'X'))
            print(movies_for_this_user)
            list_for_user = [user_name, sum_deltas]
            for i in movies_for_this_user:
                list_for_user.append(i)
            user_median_mean_best_guesses.append(list_for_user)

    # get the top ten list
    user_median_mean_best_guesses.sort(key=operator.itemgetter(1,0))
    top_ten = user_median_mean_best_guesses[:20]

    # for now just printing out to file
    # but would be good to edit directly via praw...
    lines = ['**Summer Movie Contest Top 20:**\n']
    lines.append('\n')
    lines.append('Player |Total|MI|AV|D2|O8|SO|I2|AM|JW|')
    lines.append(':------|:-|:-|:-|:-|:-|:-|:-|:-|:-|')
    for user, sum_delta, movie1, movie2, movie3, movie4, movie5, movie6, movie7, movie8 in top_ten:
        lines.append('{}|{}|{}|{}|{}|{}|{}|{}|{}|{}|'.format(user, sum_delta, movie1, movie2, movie3, movie4, movie5, movie6, movie7, movie8))
    with open('contest_top_ten.out', 'w') as FHOUT:
        for n, movie in enumerate(movie_names):
            FHOUT.write('{}\t{}\n'.format(n, movie))
        FHOUT.write('\n'.join(lines))

def score_guesses(movie_to_guesses, subreddit_name):
    '''
    Given movie_to_guesses global dict
    this dict has the movies we want to score against

    '''
    r = praw.Reddit(client_id=CLIENT_ID,
        client_secret= CLIENT_SECRET,
        user_agent = 'set user flair by {}'.format(USER_NAME),
        refresh_token = refresh_token,
    )

    p = re.compile('ratingValue":(\d+),')

    user_to_deltas = collections.defaultdict(list)
    movie_user_guess = {}
    all_usernames = set()
    all_movies = set()
    all_x = []
    all_y = []
    # get current tomatometer for each movie
    for movie, parsed_guesses_file in movie_to_guesses.items():
        
        url = 'http://www.rottentomatoes.com/m/{}/'.format(movie_to_rt[movie])
        text = requests.get(url).text
        m = p.search(text)

        if not m:
            sys.exit('Unable to get tomato meter for {}'.format(movie))
        tomato_meter = int(m.group(1))
        print(movie, tomato_meter)
        movie_user_guess[movie + ' ({})'.format(tomato_meter)] = {}
        parsed_guesses_file = os.path.join('parsed_guesses', parsed_guesses_file)
        user_guesses = pickle.load(open(parsed_guesses_file,'rb'))

        for user, guess in user_guesses.items():
            all_x.append(guess)
            all_y.append(tomato_meter)
            all_usernames.add(str(user))
            all_movies.add(movie + ' ({})'.format(tomato_meter))
            movie_user_guess[movie + ' ({})'.format(tomato_meter)][str(user)] = guess
            delta = guess - tomato_meter
            user_to_deltas[user].append(delta)
            if delta == 0:
                print(user, movie)


        time.sleep(10)

    # print out all users and all guesses to csv file

    # fig, ax = plt.subplots()
    # ax.scatter(all_x, all_y)
    # plt.savefig('test.png')

    all_usernames = sorted(all_usernames)
    with open('all_data.txt', 'w') as f:
        l = ['user']
        for movie in sorted(all_movies):
            l.append(movie)
        f.write(','.join(l) + '\n')
        for user in all_usernames:
            l = [user]
            for movie in sorted(all_movies):
                l.append(str(movie_user_guess[movie].get(user, '')))
            f.write(','.join(l) + '\n')

    ist_cutoff = 0.6 # cutoff for how frequent to be considered optimist, pessimist, etc

    min_guesses = np.ceil(len(movie_to_guesses) / 2)

    user_median_mean_best_guesses = []
    for user, deltas in user_to_deltas.items():
        #print(str(user), deltas)

        # find out if optimist or pessimist
        # maybe fine tune this so if > 66% of guesses are one way you get the term?
        n_over = sum([1 for delta in deltas if delta > 0])
        n_under = sum([1 for delta in deltas if delta < 0])
        over_freq = n_over / len(deltas)
        under_freq = n_under / len(deltas)

        if over_freq > ist_cutoff:
            ist_term = 'optimist'
        elif under_freq > ist_cutoff:
            ist_term = 'pessimist'
        else:
            ist_term = 'pragmatist'

        user_name = str(user)
        abs_deltas = [abs(i) for i in deltas]
        median_delta = np.median(abs_deltas)
        mean_delta = np.mean(abs_deltas)
        best_delta = min(abs_deltas)

        if len(deltas) >= min_guesses:
            user_median_mean_best_guesses.append((user_name, median_delta, mean_delta, best_delta, len(deltas)))
        #print(user_name, mean_delta)
        if len(deltas) > 1:
            movie_suffix = 's'
        else:
            movie_suffix = ''

        s = '+/- {}% over {} movie{}, {}'.format(int(median_delta), len(deltas), movie_suffix, ist_term)
        #print(s)
        #print('setting flair for {}'.format(user_name))

        # add golden tomato flair if they have a perfect guess
        # I would like to have multiple tomatos for multiple perfect guesses but not sure how...
        if False:
            if 0 in deltas:
                r.subreddit(subreddit_name).flair.set(user_name, s, 'goldentomato')
            else:
                r.subreddit(subreddit_name).flair.set(user_name, s, '')
                # if they previously had a goldentomato but then scores change - will this remove it?
            time.sleep(3)

    # get the top ten list
    user_median_mean_best_guesses.sort(key=operator.itemgetter(1,2,3,4)) # **** mistake! want to sort len_deltas other way so more is better!!!
    top_ten = user_median_mean_best_guesses[:10]

    # for now just printing out to file
    # but would be good to edit directly via praw...

    lines = ['**Top Ten Guessers:**\n']
    lines.append('(*min {:.0f} guesses*)'.format(min_guesses))
    lines.append('\n')
    lines.append('Player | +/-   | Best | Guesses')
    lines.append(':------|:------|:-----|--------')
    for user, median_delta, _, best_delta, n_guesses in top_ten:
        lines.append('{}|{}|{}|{}'.format(user, median_delta, best_delta, n_guesses))
    with open('top_ten.out', 'w') as FHOUT:
        FHOUT.write('\n'.join(lines))

if __name__ == '__main__':
    print_upcoming(movie_to_rt, movie_to_reddit, movies_to_skip)
    score_guesses(movie_to_guesses, subreddit_name)
    score_guesses_contest(movie_to_guesses_contest, subreddit_name)
