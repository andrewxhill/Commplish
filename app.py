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
            
            logging.error(self.request.get('provider'))
            logging.error(self.request.get('provider'))
            logging.error(self.request.get('provider'))
            logging.error(self.request.get('provider'))
            logging.error(self.request.get('provider'))
            if openid_url is not None:
                logging.error(PROD)
                logging.error(PROD)
                logging.error(PROD)
                logging.error(PROD)
                logging.error(PROD)
                logging.error(PROD)
                logging.error(PROD)
                logging.error(PROD)
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
        self.push_html('home.html')
        
class UserProfile(BaseHandler):
    def get(self, name):
        self.push_html('public_user_profile.html')

class ProjectProfile(BaseHandler):
    def post(self,pid):
        self.get(pid)

    def get(self,pid):
        if pid=="new" and self.usermodel:
            if self.usermodel.limit >= len(self.usermodel.admins):
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
             ],
             debug=True)

def main():
    util.run_wsgi_app(application)

if __name__ == "__main__":
    main()
