import praw
from pprint import pprint
import re
import random
import time
import datetime
import sqlite3
import urllib2
import sys
import requests

conn = sqlite3.connect('conversionbot_inbox.db')
c = conn.cursor();


c.execute('''create table if not exists inbox (
			id integer primary key asc,
			comment_id varchar(10) unique,
			comment text
			)''')

def commify(n):
    if n is None: return None
    n = str(n)
    if '.' in n:
        dollars, cents = n.split('.')
    else:
        dollars, cents = n, None

    r = []
    for i, c in enumerate(str(dollars)[::-1]):
        if i and (not (i % 3)):
            r.insert(0, ',')
        r.insert(0, c)
    out = ''.join(r)
    if cents:
        out += '.' + cents
    return out
    
    
def load_inbox(r,after_fullname=""):
	try:
		inbox = r.get_inbox(limit=200,params={'after':after_fullname})
		#inbox = r.get_unread(limit=50,params={'after':after_fullname})
	except praw.errors.RateLimitExceeded as RateLimit:
		print("Ratelimit exceeded. sleep for ",RateLimit.sleep_time)
		time.sleep(RateLimit.sleep_time)
		return load_inbox(r,'')

	last_fullname=''
	for message in inbox:
		# you have been banned from posting to [/r/Futurology: Future(s) Studies](/r/Futurology).
		if not re.search(r'you have been banned from posting to \[/r/(\w+): .+?\]\(/r/.*',message.body):
			print "#####",message.body.encode('utf-8'),"#####"
			c.execute('insert into inbox (comment_id,comment) values (?,?)',(message.id,message.body))

		last_fullname = message.fullname
	if last_fullname == '':
		return list
	return load_inbox(r,last_fullname)

def process_inbox(r):
	replies = load_inbox(r)


try:
	user_agent = ("UselessConversionBot inbox dumper 1.2 by /u/Unabageler")
	r = praw.Reddit(user_agent=user_agent)
	r.login('UselessConversionBot','fiksnrth')
		
	process_inbox(r)
	sys.exit()
except KeyboardInterrupt:
	print "Bye"
	sys.exit()






