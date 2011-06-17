"""
Copyright (C)  Andrew Hill
"""
from __future__ import with_statement
import cgi
import logging
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import images
from google.appengine.api import files
from aeoid import users
from aeoid import middleware
from commplish.db import *
import simplejson
import md5
import os
import datetime
import urllib
import uuid

class AppsFederationHandler(webapp.RequestHandler):
  """Handles openid login for federated Google Apps Marketplace apps."""
  def get(self):
    domain = self.request.get("domain")
    if not domain:
      self.redirect("/user/view")
    else:
      openid_url = "https://www.google.com/accounts/o8/site-xrds?hd=" + domain
      self.redirect("%s?openid_url=%s" %
                    (users.OPENID_LOGIN_PATH, urllib.quote(openid_url)))


class LoginHandler(webapp.RequestHandler):
  def get(self):
    if users.get_current_user():
      login = LoginRecord()
      logging.warn(login.user)
      login.put()
    self.redirect('/home')

class LogOut(webapp.RequestHandler):
  def get(self):
    if users.get_current_user():
        self.redirect(users.create_logout_url('/'))
        
class BaseHandler(webapp.RequestHandler):
    def render_template(self, file, template_vals):
        path = os.path.join(os.path.dirname(__file__), 'commplish', 'templates', file )
        logging.error(path)
        self.response.out.write(template.render(path, template_vals))
    def push_html(self, file):
        path = os.path.join(os.path.dirname(__file__), "commplish", "html", file)
        self.response.out.write(open(path, 'r').read())
    def signup(self):
        self.push_html('user_signup.html')
        
    def login(self, url):
        self.redirect(users.create_login_url(url))
        
class SiteHome(webapp.RequestHandler):
    def get(self):
        self.redirect('/home')
            
class UserAdmin(BaseHandler):
    def __init__(self):
        self.usermd5 = None
        self.user = None
    
    def profile(self):
        self.user = users.get_current_user()
        
        if self.user is None:
            self.login('/home')
            return 
            
        m = md5.new()
        m.update(self.user.email().strip().lower())
        self.usermd5 = str(m.hexdigest())
        um = UserModel.all(keys_only=True).filter('md5 = ',self.usermd5).fetch(1)
        
        if len(um) == 0:
            self.signup()
            return
                
        self.push_html('admin_user_profile.html')
        
    def get(self):
        self.profile()
            
class UserProfile(BaseHandler):
    def __init__(self):
        self.usermd5 = None
        self.user = None
    def get(self, name):
        self.push_html('public_user_profile.html')
            
class ProjectProfile(BaseHandler):
    def __init__(self):
        pass
        
    def post(self,pid):
        self.get(pid)
    
    def get(self,pid):
        if pid=="new":
            self.push_html('project_signup.html')
            return
        self.push_html('public_project_profile.html')

class CreateNewProject(BaseHandler):
    def __init__(self):
        self.user = None
        self.classpath = '/new/'
        
    def post(self,stage):
        self.get(stage)
        
    
    def _updatehandler(self):
        if self.request.get('cancel', None):
            self.redirect('/')
            
        is_next = self.request.get('next', None) 
        is_save = self.request.get('save', None) 
        
        if is_next:
            tg = self.request.get('target', None) 
            if tg:
                self.redirect(self.classpath + tg)
            else:
                self.redirect('/')
        else:
            self.redirect('/')
                
    def details(self):
        self.push_html('project_details.html')
            
    def create(self):
        self.push_html('project_signup.html')
        
    def addbadges(self):
        self.push_html('project_badges.html')
        
    def trackedbadges(self):
        self.push_html('project_badges_tracked.html')
        
    def sharedbadges(self):
        self.push_html('project_badges_shared.html')
        
    def admins(self):
        self.push_html('project_admins.html')
        
    def get(self, stage=None):
        self.user = users.get_current_user()
        if stage==None:
            self.create()
        if self.user is not None:
            if stage=="update":
                self._updatehandler()
            elif stage=="details":
                self.details()
            elif stage=="badges":
                self.addbadges()
            elif stage=="tracked":
                self.trackedbadges()
            elif stage=="shared":
                self.sharedbadges()
            elif stage=="admins":
                self.admins()
        else:
            self.redirect('/user')


class GiveFakeBadges(BaseHandler):
    def get(self):
        id = self.request.get('id', None)
        u = UserModel.get_by_key_name(id)
        bid = self.request.get('bid', None)
        bg = Badge.get_by_id(int(bid))
        bs = bg.set
        p = Project.all(keys_only=True).filter('badgeSets = ',bs).fetch(1)[0]
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
                    badgeSets = [],
                    admins = [usr.key()],
                    icon = str(icon_key),
                    joinDate = datetime.datetime.now(),
                    secret = str(uuid.uuid1()))
        
        """add the project to the user"""
        usr.projects.append(proj.key())
        usr.admins.append(proj.key())
        
        title = "Species cartographer"
        bds = BadgeSet(
                    key_name = title.lower().replace(' ','_'),
                    title = title,
                    about = "These badged are given to members who help us discover where species exist",
                    projects = []
                    )
                    
        """add the set to the project"""
        proj.badgeSets.append(bds.key())
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
        
            bg = Badge(
                    title = titles.pop(),
                    about = abouts.pop(),
                    set = bds,
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
   
class CreateNewUser(BaseHandler):
    def __init__(self):
        self.user = None
        self.sendurl = '/home'
        
    def post(self,action):
        self.get(action)
    
    def get(self,action):
        if action=='create':
            self._createuser()
            
    def _createuser(self):
        if self.request.get('cancel', None):
            self.redirect('/')
            
        self.user = users.get_current_user()
        
        nickname = self.request.get('nickname', None)
        
        if self.user is not None and UserModel.get_by_key_name(nickname.strip().lower()) is None:
            
            m = md5.new()
            m.update(self.user.email().strip().lower())
            
            u = UserModel(
                    key_name = nickname.strip().lower(),
                    nickname = nickname,
                    user = self.user,
                    md5 = str(m.hexdigest()),
                    about = self.request.get('about', None),
                    joinDate = datetime.datetime.now()
                    )
            db.put(u)
            
        self.redirect(self.sendurl)
            
                              
application = webapp.WSGIApplication([('/', SiteHome),
                                      ('/user/([^/]+)', UserProfile),
                                      ('/home', UserAdmin),
                                      ('/project/([^/]+)', ProjectProfile),
                                      ('/org/user/([^/]+)', CreateNewUser),
                                      ('/new', CreateNewProject),
                                      #('/new/([^/]+)', CreateNewProject),
                                      
                                      ('/give', GiveFakeBadges),
                                      ('/load', LoadFakeData),
                                      #('/user/login', LoginHandler),
                                      ('/logout', LogOut),
                                      ('/apps_login', AppsFederationHandler),
                                     ],      
                                     debug=False)
application = middleware.AeoidMiddleware(application)

def main():
  util.run_wsgi_app(application)

if __name__ == "__main__":
  main()

