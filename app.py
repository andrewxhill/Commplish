"""
Copyright (C)  Andrew Hill, Aaron Steele
"""
from __future__ import with_statement
import cgi
import logging
from google.appengine.api import mail
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import images
from google.appengine.api import files
from google.appengine.api import users
from commplish.db import *
import simplejson
import md5
import os
import datetime
import urllib
import uuid
import re


if 'SERVER_SOFTWARE' in os.environ:
  PROD = not os.environ['SERVER_SOFTWARE'].startswith('Development')
else:
  PROD = True

class LogOut(webapp.RequestHandler):
    def get(self):
        if users.get_current_user():
            self.redirect(users.create_logout_url('/'))
        else:
            self.redirect('/')
            
class BaseHandler(webapp.RequestHandler):
    def __init__(self):
        self.user = users.get_current_user()
        self.usermd5 = None
        self.usermodel = None
        if self.user:
            m = md5.new()
            m.update(self.user.email().strip().lower())
            self.usermd5 = str(m.hexdigest())
            self.usermodel = UserModel.frommd5(self.usermd5)
    def post(self):
        self.get()
    def get(self):
        pass
    def render_template(self, file, template_vals):
        path = os.path.join(os.path.dirname(__file__), 'commplish', 'templates', file )
        self.response.out.write(template.render(path, template_vals))
    def push_html(self, file):
        path = os.path.join(os.path.dirname(__file__), "commplish", "html", file)
        self.response.out.write(open(path, 'r').read())
    def signup(self):
        self.push_html('user_signup.html')
        return
        
    def login(self, url=None, path=None):
        self.ID_PROVIDERS = {
                       'google' : 'http://google.com/accounts/o8/id',
                       'myopenid'  : 'http://myopenid.com/',
                       'aol' : 'http://openid.aol.com/',
                       'myspace' : 'http://myspace.com/',
                       'yahoo' : 'http://me.yahoo.com/', 
                       'versign' : 'http://pip.verisignlabs.com/',
                       'launchpad' : 'http://login.launchpad.net/',
                       'flicker': 'http://flicker.com/',
                       'wordpress': 'http://wordpress.com/',
                       'blogspot': 'http://blogspot.com/',
                       }
        if url is None:
            url = self.request.url
        if path is not None:
            url = "http://" + self.request.url.rstrip('/') + '/' + path.lstrip('/')
            
        if self.user is None:
            for s in ['http://','https://','www.']:
                url = url.lstrip(s)
            openid_url = self.request.get('openid_url', None)
            if openid_url is None or len(openid_url.strip()) == 0:
                openid_url = self.ID_PROVIDERS.get(self.request.get('provider'), None)
            if openid_url is not None:
                if PROD:
                    self.redirect(
                        users.create_login_url(
                            url,
                            federated_identity = openid_url
                        )
                    )
                else:
                    self.redirect(users.create_login_url('http://localhost:8080/home'))
                return
            self.push_html('login.html')
            return True
        if self.usermd5 is None:
            m = md5.new()
            m.update(self.user.email().strip().lower())
            self.usermd5 = str(m.hexdigest())
            
        if self.usermodel is None:
            self.usermodel = UserModel.frommd5(self.usermd5)
            if self.usermodel is None:
                self.signup()
                return True
        
            
    def _hasprojectauthority(self,pid):
        if db.Key.from_path('Project', pid.strip().lower()) in self.user.admins:
            return True
        else:
            return False

    def _hascollectionauthority(self,cid):
        col = Collection.get_by_key_name(cid)
        a = False
        for p in self.user.admins:
            if p in col.projects:
                a = True
        return a
    
class SiteHome(BaseHandler):
    def get(self):
        self.redirect('/home')
        
class UserProfile(BaseHandler):
    def get(self, name):
        self.push_html('public_user_profile.html')

class ProjectProfile(BaseHandler):
    def post(self,pid):
        self.get(pid)

    def get(self,pid):
        if pid=="new":
            self.push_html('project_signup.html')
            return
        self.push_html('public_project_profile.html')

class CollectionProfile(BaseHandler):
    def post(self,cid):
        self.get(cid)

    def get(self,cid):
        self.push_html('public_collection_profile.html')

class UserAdmin(BaseHandler):
    def profile(self):
        self.push_html('admin_user_profile.html')
    def get(self):
        if self.login():
            return
        self.profile()

class ProjectProfileAdmin(BaseHandler):
    def post(self,pid):
        self.get(pid)
    def get(self,pid):
        if self.login():
            return
            
        if Project.get_by_key_name(pid.strip().lower()):
            self.push_html('admin_project_profile.html')
            return
        else:
            self.redirect('/home')
            return

class CollectionProfileAdmin(BaseHandler):
    def post(self,cid):
        self.get(cid)

    def get(self,cid):
        if self.login():
            return
            
        col = Collection.get_by_key_name(cid.lower().strip())
        a = False
        for p in self.usermodel.admins:
            if p in col.projects:
                a = True

        if a:
            self.push_html('admin_collection_profile.html')
            return

        self.redirect('/home')
        return

class GiveFakeBadges(BaseHandler):
    def get(self):
        id = self.request.get('id', None)
        u = UserModel.get_by_key_name(id)
        bid = self.request.get('bid', None)
        bg = Badge.get_by_id(int(bid))
        bs = bg.collection
        p = Project.all(keys_only=True).filter('collections = ',bs).fetch(1)[0]
        if p not in u.projects:
            u.projects.append(p)
            db.put(u)
        ub = UserBadge(
                parent = bg,
                project = str(p),
                user = u,
                recieved = datetime.datetime.now(),
        )
        db.put(ub)

class LoadFakeData(BaseHandler):
    def get(self):

        """Get the user info"""
        user = users.get_current_user()

        """create the user's unique key"""
        m = md5.new()
        m.update(user.email().strip().lower())
        usermd5 = str(m.hexdigest())

        usr = UserModel.all().filter('md5 = ',usermd5).fetch(1)[0]

        """Create a user instance"""
        """
        usr = UserModel(
                    key_name = "andrewxhill",
                    nickname = "andrewxhill",
                    md5 = usermd5,
                    user = user,
                    about = 'biology, code, coffee enthusiast',
                    joinDate = datetime.datetime.now(),
                    projects = [],
                    admins = [] )
        """
        #db.put(usr)


        """get mol icon"""
        path = os.path.join(os.path.dirname(__file__), "io",'logo.png')
        #img = open(path, 'r').read()

        shortname = "MOL"

        img = files.blobstore.create(mime_type='img/png')
        with files.open(img, 'a') as f:
            f.write(open(path, 'r').read())
        files.finalize(img)
        icon_key = files.blobstore.get_blob_key(img)

        proj = Project(
                    key_name = shortname.lower(),
                    fullName = "Map of Life",
                    name = shortname,
                    url = db.Link("http://mappinglife.org"),
                    about = "Species range knowledge project",
                    collections = [],
                    admins = [usr.key()],
                    icon = str(icon_key),
                    joinDate = datetime.datetime.now(),
                    secret = str(uuid.uuid1()))

        """add the project to the user"""
        usr.projects.append(proj.key())
        usr.admins.append(proj.key())

        title = "Species cartographer"
        kn = re.sub(r'[^a-zA-Z0-9-]', '_', title.strip().lower())
        bds = Collection(
                    key_name = kn,
                    title = title,
                    about = "These badged are given to members who help us discover where species exist",
                    projects = []
                    )

        """add the collection to the project"""
        proj.collections.append(bds.key())
        db.put(proj)

        bds.projects.append(proj.key())

        bgs = []
        ubds = []
        titles = [
                'Problem solver',
                'Admin','Member',
                'Primary source',
                'Annotator',
                'Commentor','Work horse',
                'Big fish']
        abouts = [
                'Fixed a bug or data',
                'Administrator of one of the projects in this badge set',
                'Member of the one of the projects in this badge set',
                'Created new or unpublished data',
                'Made annotations on data',
                'Added to project comments',
                'Seen 20 or more days on the project',
                'Active during 100 or more days on the project']

        for i in range(10, 18):
            path = os.path.join(os.path.dirname(__file__), "io",str(i) + '.png')
            #img = open(path, 'r').read()

            img = files.blobstore.create(mime_type='img/png')
            with files.open(img, 'a') as f:
                f.write(open(path, 'r').read())
            files.finalize(img)
            icon_key = files.blobstore.get_blob_key(img)

            ttl = titles.pop()
            bkn = re.sub(r'[^a-zA-Z0-9-]', '_', ttl.strip().lower())
            bg = Badge(
                    parent = bds,
                    key_name = bkn,
                    title = ttl,
                    about = abouts.pop(),
                    collection = bds,
                    icon = str(icon_key)
                    )
            db.put(bg)

            """give some badges to myself"""
            if i in [11, 15, 16, 17]:
                ubd = UserBadge(
                        parent = bg,
                        project = str(proj.key()),
                        user = usr,
                        recieved = datetime.datetime.now(),
                )
                ubds.append(ubd)

        if True:
            db.put([usr, bds])
            db.put(ubds)

class LoadPublicIcons(webapp.RequestHandler):
    def get(self):
        path = os.path.join(os.path.dirname(__file__), "publicbadges",'titles.csv')
        titles = open(path, 'r')
        ct = 1
        for t in titles.readlines():
            t = t.replace(',','').strip()
            if t != 'none':
                imgpath = os.path.join(os.path.dirname(__file__), "publicbadges",'black-comment-bubble-icon_%03d.png' % ct)
                logging.error(imgpath)
                img = files.blobstore.create(mime_type='img/png')
                with files.open(img, 'a') as f:
                    f.write(open(imgpath, 'r').read())
                files.finalize(img)
                icon_key = files.blobstore.get_blob_key(img)
                
                tags = []
                tags.append(t.strip().lower())
                ts = t.strip().lower().split(' ')
                if len(ts)>1:
                    for s in ts:
                        s = s.strip()
                        tags.append(s)
                b = PublicBadges(
                        title = t,
                        icon = str(icon_key),
                        tags = tags,
                        credit = "http://icons.mysitemyway.com"
                    )
                db.put(b)
                url = images.get_serving_url(icon_key, size=int(128))
                self.response.out.write("""
                    <p>
                        %s </br>
                        <img src="%s" />
                    </p>""" % (t,url)
                )
                
            ct+=1

class UserStatus(webapp.RequestHandler):
    def post(self):
        self.get()
    def get(self):
        self.user = users.get_current_user()
        if self.user:
            endpoint = users.create_logout_url('/')
            text = 'logout'
            home = "/home"
        else:
            endpoint = "/home"
            text = 'login'
            home = "/"
        out = {'text': text,
               'url': endpoint,
               'home': home}
               
        self.response.out.write(
            simplejson.dumps(out) )
        return
        
application = webapp.WSGIApplication([
              ('/', SiteHome),
              ('/user/([^/]+)', UserProfile),
              ('/collection/([^/]+)', CollectionProfile),
              ('/project/([^/]+)', ProjectProfile),
              ('/home', UserAdmin),
              ('/admin/project/([^/]+)', ProjectProfileAdmin),
              ('/admin/collection/([^/]+)', CollectionProfileAdmin),
              ('/status', UserStatus),
              ('/logout', LogOut),

              ('/give', GiveFakeBadges),
              ('/load', LoadFakeData),
              ('/public', LoadPublicIcons),
             ],
             debug=True)

def main():
    util.run_wsgi_app(application)

if __name__ == "__main__":
    main()
