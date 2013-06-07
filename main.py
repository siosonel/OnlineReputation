__author__ = "Alberto Boschetti"
__status__ = "Prototype"

import re
import urllib
import json
import nltk
from nltk.corpus import stopwords
import time
from senti_classifier import senti_classifier
from makehtml import array_to_html_page
import params
from TwitterSearch import *
from DbConnector import DBConnector


# DEFINES
OUTFILE = 'test.html'
#see params.py
keywords = ['apple', 'iphone', 'ios', 'aapl']

#keywords = {'apple', 'aapl', 'tim cook', 'iphone', 'steve jobs', 'cupertino', 'wwdc', 'macbook',
#            'ipod', 'itunes', 'ipad', 'macos', 'snow leopard', 'mountain lion', 'ios', 'xcode',
#            'facetime', 'appstore', 'osx', 'nsobject'}


def normalize_tweet(text):
    """
    Clean the tweet before sentiment analysis. Remove cashtags, links and account names. Transform hashtags in words
    :param text: the body of a tweet
    :return: a clean version of the body
    """
    pattern = re.compile(r"(.)\1{2,}", re.DOTALL)
    text = text.lower().replace("\"", "").replace("'", "").replace(":", "").replace(".", " ")\
                       .replace("(", "").replace(")", "").replace(";", "")\
                       .replace("?", "").replace("!", "").replace("#", "").replace("`","")\
                       .replace('\n', ' ').replace('\r', ' ')

    clean_text = ""

    for word in text.split():
        if word not in stopwords.words('english'):

            word = word.strip()

            if word.startswith("@"):
                word = "*ACCOUNT*"
            elif word.startswith("http"):
                word = "*LINK*"
            elif word.find("$") >= 0:
                word = ""
            elif len(word) < 3:
                word = ""
            else:
                word = pattern.sub(r"\1\1\1", word)
                #word = nltk.PorterStemmer().stem(word)

            clean_text = clean_text + " " + word

    return clean_text


def getTweetsForKeyword(keyword, last_id=None):
    """
    Get the (recent) tweets for a given keyword
    :param keyword: the query keyword
    :return: a list of tweets. List is empty if an error occurs
    """
    tweet_list = []

    try:
        print '*** Searching tweets for keyword:', keyword, ' ...'
        tso = TwitterSearchOrder()
        tso.setKeywords([keyword])
        tso.setLanguage('en')
        tso.setResultType('recent')
        tso.setCount(100)
        tso.setIncludeEntities(True)

        if last_id is not None:
            tso.setSinceID(last_id)

        ts = TwitterSearch(
            consumer_key=params.CONSUMER_KEY,
            consumer_secret=params.CONSUMER_SECRET,
            access_token=params.ACCESS_TOKEN,
            access_token_secret=params.ACCESS_TOKEN_SECRET
        )

        ts.authenticate()

        counter = 0

        for tweet in ts.searchTweetsIterable(tso):
            counter += 1
            tweet_list.append(tweet)
        print '*** Found a total of %i tweets for keyword:' % counter, keyword
        return tweet_list

    except TwitterSearchException, e:
        print "[ERROR]", e.message
        return tweet_list


def sentimentTweet(tweet):
    pos_score, neg_score = senti_classifier.polarity_scores([tweet])
    if pos_score > neg_score:
        vote = 1
    elif pos_score < neg_score:
        vote = -1
    else:
        vote = 0
    return vote


def extractLocation(tweet):
    try:
        location = tweet["place"]["country_code"]
    except Exception:
        location = "unknown"
    return location


if __name__ == '__main__':

    counter = {}
    db = DBConnector()
    db.testDB()

    for keyword in keywords:

        last_id = db.getLastIdForQuery(keyword)
        tweet_list = getTweetsForKeyword(keyword, last_id)

        for tweet in tweet_list:
            country = extractLocation(tweet)
            id = int(tweet["id"])
            clean_text = normalize_tweet(tweet["text"]).encode("utf-8")

            if country != "unknown":
                vote = sentimentTweet(clean_text)
                db.insertTweet(keyword, id, clean_text, country, vote)

                try:
                    counter[country] += vote
                except KeyError:
                    counter[country] = vote
            else:
                db.insertTweet(keyword, id, clean_text, country)


    sentiment_score = db.getSentimentTweets(keywords)

    htmllist = []

    for entry in sentiment_score:
        htmllist.append(([entry[0], entry[1]]))

    array_to_html_page(htmllist, OUTFILE)
    print "Check out the " + OUTFILE + " file"



    #TODO:
    #implement new twitter 1.1 (library :) V
    #sqlite storage of tweets              V
    #classify with tweet data, not movie!  -
    #store tweeet with keyword, not keyword list. Easier to retrieve and last id is fully working V
