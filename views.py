from flask import Flask, render_template, request, redirect, make_response
from google.appengine.ext import ndb
from google.appengine.api import mail, urlfetch, users
import json, random, string, hashlib

app = Flask(__name__)
app.config['DEBUG'] = True


@app.route('/',  methods=['GET', 'POST'])
def index():
    username = request.cookies.get('username')
    user = User.query(User.name == username)
    user = user.get()
    if user:
        daily = user.daily
    else:
        daily = False
    snaps = Snap.query(Snap.username == username)
    if request.method == "GET":
        return render_template("index.html", username = username, snaps = snaps, daily = daily)
    else:
        recipient = request.form["recipient"]
        qry = User.query(User.name == recipient)
        res = qry.get()
        if not res:
            return render_template("index.html", username = username, snaps = snaps, confirm = "No User found")
        else:
            if random.randint(0,1) == 0:
                url = get_rnd_url("cats")
            else:
                url = get_rnd_url("dogpictures")
            sid = ''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(20))
            snap = Snap(sid = sid, url = url, username = recipient, sender = username)
            snap.put()
            return render_template("index.html", username = username, snaps = snaps, confirm = "Snap sent")

@app.route('/daily_signup')
def daily_signup():
    username = request.cookies.get('username')
    if username:
        user = User.query(User.name == username)
        user = user.get()
        if not user.daily:
            user.daily = True
            user.put()
        return redirect("/")
    else:
        return redirect("/")


@app.route('/daily_cron')
def daily_cron():
    daily_users = User.query(User.daily == True)
    for d_user in daily_users:
        daily_send(d_user.name)
    return "OK"

def daily_send(username):
    for x in range(0,5):
        if random.randint(0,1) == 0:
                url = get_rnd_url("cats")
        else:
            url = get_rnd_url("dogpictures")
        sid = ''.join(random.choice(string.ascii_lowercase + string.ascii_uppercase + string.digits) for _ in range(20))
        snap = Snap(sid = sid, url = url, username = username, sender = "Daily SnapYo")
        snap.put()

@app.route('/del_snap/<sid>')
def del_snap(sid):
    snap = Snap.query(Snap.sid == sid)
    snap = snap.get()
    snap.key.delete()
    return "DELETED"

@app.route('/login',  methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        password = hashlib.sha512(password + "213wqdase2qdw").hexdigest()
        user = User.query(User.name == username)
        user = user.get()
        if user and user.password == password:
            resp = make_response(redirect("/"))
            resp.set_cookie('username', user.name)
            return resp
        else:
            return render_template("login.html")
    else:
        return render_template("login.html")

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        user = User.query(User.name == username)
        user = user.get()
        if user:
            return render_template("register.html",error_message='User already exists')
        password = hashlib.sha512(password + "213wqdase2qdw").hexdigest()
        user = User(name = username, password = password)
        user.put()
        return redirect("/login")
    else:
        return render_template("register.html")

@app.route('/logout')
def logout():
    resp = make_response(render_template("index.html"))
    resp.set_cookie('email', "")
    return resp

#Gets a list of image urls from reddit for specified subbreddit and stores them in the database
@app.route('/get_reddit_json/<subreddit>')
def get_reddit_json(subreddit):
    query_res = Link.query(Link.subreddit==subreddit)
    for qr in query_res:
        qr.key.delete()

    url = "http://www.reddit.com/r/%s/top/.json?t=week&limit=100" % subreddit
    result = urlfetch.fetch(url)
    json_data = json.loads(result.content)
    entries = json_data['data']['children']
    url_list = []
    for entry in entries:
        url = entry['data']['url']
        if (url.endswith(".jpg")):
            url_list.append(url)

    store_urls(url_list,subreddit)
    return str(subreddit)

def get_rnd_url(subreddit):
    url_list = load_urls(subreddit)
    url = url_list[random.randint(1,len(url_list)-1)]
    return url

def store_urls(url_list,subreddit):
    for url in url_list:
        rnd = random.random()
        l = Link(rnd = rnd, subreddit = subreddit, url=url)
        l.put()

def load_urls(subreddit,limit=10):
    limit_rnd = random.random()
    query = Link.query(ndb.AND(Link.subreddit==subreddit,
                                    Link.rnd >= limit_rnd))
    query_result = query.fetch(limit)
    url_list = []
    for link in query_result:
        url_list.append(link.url)
    return url_list


class Snap(ndb.Model):
    sid = ndb.StringProperty()
    url = ndb.StringProperty()
    username = ndb.StringProperty()
    sender = ndb.StringProperty()

class User(ndb.Model):
    name = ndb.StringProperty()
    password = ndb.StringProperty()
    daily = ndb.BooleanProperty(default=False)

class Link(ndb.Model):
    rnd = ndb.FloatProperty()
    subreddit = ndb.StringProperty()
    url = ndb.StringProperty()


