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

conn = sqlite3.connect('conversionbot.db')
c = conn.cursor();


c.execute('''create table if not exists already_done (
			id integer primary key asc,
			comment_id varchar(10),
			add_dt datetime
			)''')
c.execute('''create table if not exists banned_subreddits (
			id integer primary key asc,
			subreddit_name varchar(255),
			add_dt datetime
			)''')

already_done = []

for row in c.execute('SELECT id,comment_id,add_dt FROM already_done ORDER BY id DESC LIMIT 500'):
	already_done.append(row[1])
	#print row[0],", ",row[1],", ",row[2]

bad_subreddits = []
for row in c.execute('SELECT subreddit_name FROM banned_subreddits'):
	bad_subreddits.append(row[0])
	print "BANNED "+row[0]

bad_comment_pattern = re.compile('faq|[\(\)\[\]]',re.I|re.S)


#unitPatterns = [r'([0-9.]+)\s*(mi|miles?)',r'([0-9.]+)\s*(meters?|km|kilometers?)']
unitPatterns = [
	r'([0-9.,]+)\s*(cm|(meters?)?|km|kilometers?)\b(\/[a-z]+)?',
	r'([0-9.,]+)\s*(kg|kilograms?)\b(..?.?.?(\s|\.)|\s+|$)(\/[a-z]+)?',
    r'([0-9.,]+)\s*(lit(er|re)s?)\b(\/[a-z]+)?'
]
abbr = {
	'mile': 'mi',
	'kilometer': 'km',
	'kilometers': 'km',
	'kilogram': 'kg',
	'kilograms': 'kg',
	'liter': 'l',
	'liters': 'l',
	'litre': 'l',
	'litres': 'l'
}
conversion_factors = {
	'mi': {
		'fathoms': 880,
		'furlongs': 8,
		'parsecs': 5.215287*pow(10,-14),
		'cubits': 3520,
		'smoots': 945.671642,
		'mm': 1609344,
		'planck lengths': 9.95758409*pow(10,37)
	},
	'km': {
		'hands': 9842.51969,
		'furlongs': 4.97096954,
		'parsecs': 3.24077929*pow(10,-14),
		'cubits': 2187.2266,
		'football fields': 9.11,
		'smoots': 587.613116,
		'planck lengths': 6.1873559*pow(10,37),
		'picoParsecs': .0324077929,
		'light years': 1.05702341*pow(10,-13),
		'astronomical units': 6.68458712*pow(10,-9),
		'Japanese shakus': 3300 + 33/100,
		'beard-seconds': 200000000000,
		'sheppey' : 1/1.4,
		'potrzebie': 441832.722,
		'barleycorn': 117647.058824,
		'poronkusema': 1/7.5,
		'rods': 198.838782,
		'cubic hogshead edges': 1612.6431220770844
	},
	'kg': {
		'troy ounces': 32.15,
		'grains': 15430,
		'drams': 257.2,
		'pennyweight': 643,
		'atomic mass units': 6.022*pow(10,26),
		'slugs': 0.0685217659,
		'solar masses': 5.02739933*pow(10,-31),
		'blintz': 27.4533808,
		'bags portland cement': 0.0234534,
		'bags coffee': 0.0166667,
		'electron volts': 5.60978*pow(10,35),
		'lbs force per foot per second squared': 0.06852
	},
	'l': {
		'coombs': 0.007094,
		'US tablespoons': 67.628,
		'Imperial tablespoons': 56.3121,
		'shots': 22.5426818,
		'pecks': 0.113510367,
		'hogsheads': .00419320718,
		'firkins': .0244410175,
		'minims (US)': 16230.7309,
		'US cranberry barrels': 0.01047120418,
		'oil barrels': 0.00628981077,
		'hubble-barns': 1/13.1,
		'ngogn': 86.2528849,
		'drops': 10136.2,
		'timber feet': 0.0353147,
		'imperial gills': 7.03901304,
		'cubic beard-seconds': 8.0*pow(10,21),
		'standard volumes': 4.4615*pow(10,-5)
	},
}
base_convert = {
	'meter': {
		'factor': .001,
		'unit': 'km'
	},
	'm': {
		'factor': .001,
		'unit': 'km'
	},
	'meters': {
		'factor': .001,
		'unit': 'km'
	},
	'cm': {
		'factor': .00001,
		'unit': 'km'
	}
}


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
    
    
def fixup_units(text):
	ret = ''
	for pattern in unitPatterns:
		#print "check pattern "+pattern
		for matchOb in re.findall(pattern,text,re.I|re.S):
			#print "found pattern ",pattern
			#print "op text: ",text,"\n"
			value = matchOb[0]
			value_in = value
			unit_in = matchOb[1]
			unit = abbr.get(matchOb[1],unit_in)
			per_unit = matchOb[3]
			if unit in base_convert.keys():
				#print "mult %s * %f\n" % (value,base_convert[unit]['factor'])
				try:
					value = float(value) * base_convert[unit]['factor']
				except ValueError:
					continue
				unit = base_convert[unit]['unit']
			#print "found value "+str(value)+" unit "+unit+" unit_in "+unit_in
			if unit in conversion_factors.keys():
				ckey = random.choice(conversion_factors[unit].keys())
				factor = conversion_factors[unit][ckey]
				try:
					out = float(value) * factor
				except ValueError:
					continue

				if abs(out) > 10000000 or abs(out) < .0001:
					str_out = "%.5e" % (out)
				else:
					str_out = "%.5f" % (out)
				str_out = commify(str_out)
				
				tmp = "%s %s%s %s %s %s%s" % (value_in,unit_in,per_unit,u"\u2248",str_out,ckey,per_unit)
				if re.search(bad_comment_pattern,tmp):
					#print "error parsing: ", tmp
					tmp=re.sub(r'/r/MetricConversionBot/comments/1f53fw/faq/\)','',tmp)
					#print "fixed "+tmp
				if re.search(bad_comment_pattern,tmp):
					print "final error parsing: ", tmp
				else:
					#print "adding "+tmp
					if len(ret):
						ret += "\n\n"
					ret += tmp
	if len(ret):
		tmp = re.sub(r'(?<!hubbl)e([\-\+])0*([0-9]+)',r" x 10^\1\2",ret)
		return re.sub('\+','',tmp)
		#return ret
	else:
		return False

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
		if re.search(r'you have been banned from posting to \[/r/(\w+): .+?\]\(/r/.*',message.body):
			subreddit = re.sub(r'you have been banned from posting to \[/r/(\w+): .+?\]\(/r/.*',r'\1',message.body)
			#print "banned from "+subreddit
			if subreddit in bad_subreddits:
				continue
			else:
				bad_subreddits.append(subreddit)
				now = datetime.datetime.now()
				c.execute('insert into banned_subreddits (subreddit_name,add_dt) values (?,?)',(subreddit,now))

		last_fullname = message.fullname
	if last_fullname == '':
		return list
	return load_inbox(r,last_fullname)

def process_inbox(r):
	load_inbox(r)
	str = "\n".join(["* ["+s+"](/r/"+s+")" for s in bad_subreddits])

	post=r.get_submission(url="http://www.reddit.com/r/UselessConversionBot/comments/1knas0/hi_im_useless/",comment_limit=0)
	newtext = re.sub(re.compile('banned from:.*so far.',re.S),r'banned from:\n\n'+str+'\n\n\nso far.',post.selftext)
	print newtext
	if (newtext != post.selftext):
		print "time for change"
		post.edit(newtext)
	else:
		print "not changing ban list"

#fixup_units('5 miles')
#exit()

def get_metricbot_comments(r):
	comments = []
	try:
		print("getting comments")
		#comments = r.get_subreddit('friends').get_comments()
		#comments = r.get_redditor('MetricConversionBot').get_comments()
		#comments = r.get_all_comments()
		subreddit_filter = 'all-'+"-".join(bad_subreddits)
		print "filter "+subreddit_filter
		comments = r.get_subreddit(subreddit_filter).get_comments(limit=200)
	except praw.errors.RateLimitExceeded as RateLimit:
		print("Ratelimit exceeded. sleep for ",RateLimit.sleep_time)
		time.sleep(RateLimit.sleep_time)
		get_metricbot_comments(r)
	except urllib2.HTTPError as error:
		if error.getcode() == "403":
			print "banned from subreddit."
		else:
			print 'error getting posts ',error.getcode()
	except requests.exceptions.HTTPError as error:
		time.sleep(30)
		print "http error while getting posts ",error
	
	return comments

def process_comments(r):
	comments = get_metricbot_comments(r)
	
	done_one = False
	for comment in comments:
		if comment.subreddit.display_name.lower() in bad_subreddits:
			#print "skip subreddit "+comment.subreddit.display_name
			continue
		if comment.author.name.lower() == "uselessconversionbot":
			continue
		op_text = comment.body
		#print "op: ",op_text,"\n"
		if comment.id not in already_done:
			newcomment = fixup_units(comment.body)
			#print "newcomment: \n"+newcomment+"\n__EOC__\n"
			already_done.insert(0,comment.id)
			now = datetime.datetime.now()
			try:
				c.execute('insert into already_done (comment_id,add_dt) values (?,?)',(comment.id,now))
				conn.commit()
			except error:
				print "error adding to db: ",error
			if newcomment:
				already_replied = 0
				try:
					if comment.replies and len(comment.replies):
						#print "Replies: ",comment.replies
						for reply in comment.replies:
							#print "reply ",vars(reply.author)
							if reply.author.name == u'UselessConversionBot':
								print "already replied to "+reply.id
								already_replied = 1
								continue
				except:
					print "trouble getting replies"
					time.sleep(5)
					continue

				if not already_replied:
					try:
						comment.upvote()
					except praw.errors.RateLimitExceeded as RateLimit:
						time.sleep(RateLimit.sleep_time)
						comment.upvote()
					except urllib2.HTTPError as error:
						if error.getcode() == "403":
							print "banned from subreddit for comment ",comment.id
						else:
							print error.getcode()
					except requests.exceptions.HTTPError as error:
						print error
					except praw.errors.APIException as error:
						print error

					newcomment += "\n\n^^^[WHY](/r/UselessConversionBot/comments/1knas0/hi_im_useless/)"
					try:
						print "replying to the comment ",comment.id," with ",newcomment,"\n"
						comment.reply(newcomment)
						done_one = True
					except praw.errors.RateLimitExceeded as RateLimit:
						print("Ratelimit exceeded. sleep for ",RateLimit.sleep_time)
						time.sleep(RateLimit.sleep_time)
						print "retry replying to the comment ",comment.id," with ",newcomment,"\n"
						comment.reply(newcomment)
					except urllib2.HTTPError as error:
						if error.getcode() == "403":
							print "banned from subreddit for comment ",comment.id
						else:
							print error.getcode()
					except requests.exceptions.HTTPError as error:
						print "error doing reply ",comment,"\n",error
					except praw.errors.APIException as error:
						print error
			#else:
			#	print "comment "+comment.id+" has nothing to convert"
			
		else:
			print "already done with ",comment.id," ",re.sub(r'\n.*','',comment.body,re.S)
	return done_one


random.seed()

if 0:
	newcomment = fixup_units("\
If you're not closing on them, stay at 150km+ of everyone so you can warp to whoever does catch them.\
Go at least 2km/s, preferably 3km/s+\
")
	if newcomment:
		print newcomment
	sys.exit()

delay=120
try:
	user_agent = ("UselessConversionBot 1.2 by /u/Unabageler")
	r = praw.Reddit(user_agent=user_agent)
	r.login('UselessConversionBot','fiksnrth')
		
	i=0;
	while True:
		i += 1
		if (i % 10 == 1):
			print "iteration ",i,", getting inbox\n";
			process_inbox(r)
		else:
			print "iteration ",i,", not getting inbox"

		print "getting posts\n"
		done = process_comments(r)
		if done:
			delay = 120
		else:
			delay -= 10
			if delay <= 0:
				delay = 30
		print "sleeping for "+str(delay)
		time.sleep(delay)
except KeyboardInterrupt:
	print "Bye"
	sys.exit()






