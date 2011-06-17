"""
Copyright (C)  2011 Aaron Steele, Andrew Hill, Sander Pick
"""
import cgi
import logging
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from google.appengine.api import images
from aeoid import users
from aeoid import middleware
from commplish.db import *
import simplejson
import pickle
import md5
import datetime
import os


class UrlTest(webapp.RequestHandler):
    def _clean(self,url):
        url = url.lower().lstrip('http://')
        url = url.lstrip('www.')
        urls = ["http://" + url, "http://www." + url]
        return urls
    def get(self):
        self.post()
    def post(self):
        url = self.request.get('url', None)
        out = {'available': None} #invalid
        if url:
            urls = self._clean(url)
            pk = Project.all(keys_only=True).filter('url = ', urls[0]).fetch(1)
            if len(pk) == 0:
                pk = Project.all(keys_only=True).filter('url = ', urls[1]).fetch(1)
                
                
            if len(pk) == 0:
                out = {'available': True}
            else: 
                out = {'available': False}
            self.response.out.write(
                    simplejson.dumps(out)
                )
        return
        
class NameTest(webapp.RequestHandler):
    def get(self,model,name):
        self.post(model,name)
    def post(self,model,name):
        if model == 'user':
            pk = db.get(db.Key.from_path('UserModel',name.strip().lower()))
        elif model == 'project':
            pk = db.get(db.Key.from_path('Project',name.strip().lower()))
            
        if pk:
            out = {'available': False}
        else:
            out = {'available': True}
        self.response.out.write(
                simplejson.dumps(out)
            )
        
class ProjectService(webapp.RequestHandler):
    def get(self,pid):
        self.post(pid)
    def post(self,pid):
        pk = db.Key.from_path('Project',pid.strip().lower())
        p = db.get(pk)
        
        sz = self.request.get('s', 64)
        
        try:
            assert int(sz) <= 256
        except:
            sz = 64
    
        age = datetime.datetime.now() - p.joinDate
        ageunit = 'days' if int(age.days) > 1 else 'day'
        memberct = len(UserModel.all(keys_only=True).filter('projects = ', pk).fetch(1000))
        memberct = str(memberct) if memberct < 1000 else "1000+"
        
        out = {
                "pid": pid,
                "name": p.name,
                "fullName": p.fullName,
                "url": p.url,
                "about": p.about,
                "icon": images.get_serving_url(p.icon, size=256),
                "age": "%s %s" % (str(age.days + 1), ageunit),
                "badgeSets": [],
                "members": memberct,
              }
        """Add all the badgesets the project belongs to"""
        for bs in p.badgeSets:
            bd = db.get(bs)
            if bd:
                s = {
                        "title": bd.title,
                        "about": bd.about,
                        "badges": []
                    }
                """Add all the badges available"""
                for b in bd.badges:
                    t = {
                            "title": b.title,
                            "about": b.about,
                            "icon": images.get_serving_url(b.icon, size=int(sz)),
                        }
                    s['badges'].append(t)
                out['badgeSets'].append(s)
                
        self.response.out.write(
            simplejson.dumps(out)
        )
            
class UserService(webapp.RequestHandler):
    def profilebymd5(self,usermd5):
        pass
    def profilebyid(self,uid):
        """uses the project's stored nickname to look up user info"""
        u = UserModel.get_by_key_name(uid.strip().lower())
        if u is not None:
            sz = self.request.get('s', 128)
            try:
                assert int(sz) <= 256
            except:
                sz = 128
            age = datetime.datetime.now() - u.joinDate
            ageunit = 'days' if int(age.days) > 1 else 'day'
            
            out = {
                    "uid": uid,
                    "nickname": u.nickname,
                    "about": u.about,
                    "email": u.user.email(),
                    "icon": "http://www.gravatar.com/avatar/%s" % u.md5,
                    "badgeSets": [],
                    "admins": [],
                    "age": "%s %s" % (str(age.days + 1), ageunit),
                  }
            for p in u.admins:
                tp = db.get(p)
                out['admins'].append(
                    {"name": tp.name,
                     "fullName": tp.fullName}
                    )
                
            bg = {}
            for b in u.badges:
                ba = b.parent()
                title = ba.set.title
                if title not in bg.keys():
                    bg[title] = {
                        "title": title,
                        "badges": [],
                        "projects": [] }
                    for p in ba.set.projects:
                        bg[title]["projects"].append(db.get(p).name)
                        
                bg[title]["badges"].append({
                        "about": ba.about,
                        "icon": images.get_serving_url(ba.icon, size=int(sz)),
                        "title": ba.title })
            for b in bg.values():
                out["badgeSets"].append(b)
                        
        self.response.out.write(
            simplejson.dumps(out)
        )
    def profilebyauth(self):
        """uses an existing session to look up user info"""
        self.user = users.get_current_user()
        m = md5.new()
        m.update(self.user.email().strip().lower())
        self.usermd5 = str(m.hexdigest())
        u = None
        um = UserModel.all().filter('md5 = ',self.usermd5).fetch(1)
        if um:
            u = um[0]
        
        if u is not None:
            sz = self.request.get('s', 128)
            try:
                assert int(sz) <= 256
            except:
                sz = 128
            age = datetime.datetime.now() - u.joinDate
            ageunit = 'days' if int(age.days) > 1 else 'day'
            
            out = {
                    "uid": u.nickname,
                    "nickname": u.nickname,
                    "about": u.about,
                    "email": u.user.email(),
                    "icon": "http://www.gravatar.com/avatar/%s" % u.md5,
                    "badgeSets": [],
                    "admins": [],
                    "age": "%s %s" % (str(age.days + 1), ageunit),
                  }
            for p in u.admins:
                tp = db.get(p)
                out['admins'].append(
                    {"name": tp.name,
                     "fullName": tp.fullName}
                    )
                
            bg = {}
            for b in u.badges:
                ba = b.parent()
                title = ba.set.title
                if title not in bg.keys():
                    bg[title] = {
                        "title": title,
                        "badges": [],
                        "projects": [] }
                    for p in ba.set.projects:
                        bg[title]["projects"].append(db.get(p).name)
                        
                bg[title]["badges"].append({
                        "about": ba.about,
                        "icon": images.get_serving_url(ba.icon, size=int(sz)),
                        "title": ba.title })
            for b in bg.values():
                out["badgeSets"].append(b)
                        
        self.response.out.write(
            simplejson.dumps(out)
        )
    def get(self,action, param=None):
        self.post(action, param)
    def post(self, action, param=None):
        if action=="id":
            self.profilebyid(param)
        if action=="auth":
            self.profilebyauth()
      
application = webapp.WSGIApplication([
                                      ('/api/project/([^/]+)', ProjectService),
                                      ('/api/user/([^/]+)', UserService),
                                      ('/api/user/([^/]+)/([^/]+)', UserService),
                                      ('/api/available/([^/]+)/([^/]+)', NameTest),
                                      ('/api/url', UrlTest),
                                     ],      
                                     debug=False)
application = middleware.AeoidMiddleware(application)

def main():
  util.run_wsgi_app(application)

if __name__ == "__main__":
  main()
