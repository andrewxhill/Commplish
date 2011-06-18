"""
Copyright (C)  Andrew Hill
"""
from __future__ import with_statement

# Use Django 1.2.
#from google.appengine.dist import use_library
#use_library('django', '1.2')

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
import re

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
    def __init__(self):
        self.user = users.get_current_user()
        self.usermd5 = None
        if self.user:
            m = md5.new()
            m.update(self.user.email().strip().lower())
            self.usermd5 = str(m.hexdigest())

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

class SiteHome(webapp.RequestHandler):
    def get(self):
        self.redirect('/home')

class UserAdmin(BaseHandler):
    def profile(self):
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

class ProjectProfileAdmin(BaseHandler):
    def post(self,pid):
        self.get(pid)

    def get(self,pid):
        um = UserModel.all(keys_only=True).filter('md5 = ',self.usermd5).fetch(1)
        if len(um)==0:
            self.redirect('/home')
            return
        if Project.get_by_key_name(pid.strip().lower()):
            self.push_html('admin_project_profile.html')
            return
        else:
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

class AdminUser(BaseHandler):
    def __init__(self):
        self.user = None
        self.sendurl = '/home'

    def post(self,action):
        self.get(action)

    def get(self,action):
        if action=='create':
            self._createuser()

    def _createuser(self):
        if self.request.get('action', None) == "cancel":
            self.redirect('/')
            return

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

class AdminProject(BaseHandler):
    def __init__(self):
        self.user = None
        self.sendurl = '/project'

    def post(self,action):
        self.get(action)

    def get(self,action):
        if action=='create':
            self._createproject()
        elif action == 'add-admin':
            self._addadmin()
        elif action == 'join-collection':
            self._handlecollection('join')
        elif action == 'follow-collection':
            self._handlecollection('follow')
        elif action == 'drop-collection':
            self._handlecollection('drop')

    def _handlecollection(self, action):
        """Handles a collection action by joining, following, or dropping a collection."""
        pid = self.request.get('project-id', None) # Project id
        cid = self.request.get('collection-id', None) # Collection id
        if not pid or not cid:
            logging.error('Unable to join collection %s to project %s' % (cid, pid))
            self.redirect('/home')
            return

        usermodel = UserModel.fromemail(users.get_current_user().email())
        # TODO: Verify that usermodel is admin of project?
        
        # Gets the Project entity for pid and redirects if None:
        project = Project.fromname(pid)
        if not project:
            logging.error('Invalid project id ' + pid)
            self.redirect('/home')
            return

        # Gets the Collection entity for cid and redirects if None:
        collection = Collection.fromtitle(cid)
        if not collection:
            logging.error('Invalid collection %s' % cid)
            self.redirect('/home')
            return
        
        pkey = project.key()
        ckey = collection.key()

        # Updates Collection and Project entities based on action:
        if action == 'join':
            if pkey not in collection.projects_joined:            
                collection.projects_joined.append(pkey)        
                collection.put()
            if ckey not in project.collections_joined:
                project.collections_joined.append(ckey)
                project.put()
        elif action == 'follow':
            if pkey not in collection.projects_following:
                collection.projects_following.append(pkey)
                collection.put()
            if ckey not in project.collections_following:
                project.collections_following.append(ckey)
                project.put()
        elif action == 'drop':
            collection.projects_following.remove(pkey)
            collection.projects_joined.remove(pkey)
            collection.put()
            project.collections_following.remove(ckey)
            project.collections_joined.remove(ckey)
            project.put()

        logging.info('Joined collection %s with project %s' % (cid, pid))    
        self.redirect('/admin/project/%s' % pid)    

    def _addadmin(self):
        """Adds an admin user to a project."""
        pid = self.request.get('project-id', None) # Project id
        uid = self.request.get('admin-user-id', None) # User id
        if not pid or not uid:
            logging.error('Unable to connect uid %s with pid %s' % (uid, pid))
            self.redirect('/home')
            return
        
        # Gets the Project entity for pid and redirects if None:
        project = Project.fromname(pid)
        if not project:
            logging.error('Invalid project id ' + pid)
            self.redirect('/home')
            return

        # Gets the UserModel entity for uid and redirects if None:
        usermodel = UserModel.fromemail(uid)
        if not usermodel:
            logging.error('Invalid user id ' + uid)
            self.redirect('/home')
            return
        
        # Connects the user and the project without introducing duplicates:
        pkey = project.key()
        if pkey not in usermodel.projects:            
            usermodel.projects.append(pkey)        
            usermodel.put()
        ukey = usermodel.key()
        if ukey not in project.admins:
            project.admins.append(ukey)
            project.put()

        logging.info('Connected uid %s to pid %s' % (uid, pid))    
        self.redirect('/admin/project/%s' % pid)    

    def _checkname(self, name):
        pk = db.get(db.Key.from_path('Project',name.strip().lower()))
        return True if pk is None else False

    def _checkurl(self, url):
        if url.strip()=="":
            return False
        url = url.lower().lstrip('http://')
        url = url.lstrip('www.')
        urls = ["http://" + url, "http://www." + url]
        pk = Project.all(keys_only=True).filter('url = ', urls[0]).fetch(1)
        if len(pk) == 0:
            pk = Project.all(keys_only=True).filter('url = ', urls[1]).fetch(1)
        return True if len(pk)==0 else False

    def _validurl(self, url):
        url = url.lower().lstrip('http://')
        return "http://" + url

    def _createproject(self):
        if self.request.get('action', None) == "cancel":
            self.redirect('/home')
            return

        user = users.get_current_user()
        m = md5.new()
        m.update(user.email().strip().lower())
        usermd5 = str(m.hexdigest())

        try:
            self.user = UserModel.all().filter('md5 = ', usermd5).fetch(1)[0]
        except:
            self.user = None

        if not self.user:
            self.redirect('/')
            return

        fullName = self.request.get('project-full-name', None)
        name = self.request.get('project-name', None)
        url = self.request.get('project-url', None)
        desc = self.request.get('project-description', None)
        #icon = self.request.get('project-icon', None)
        icon = self.request.get('project-icon')
        if icon:

            img = files.blobstore.create(mime_type='img/png')
            with files.open(img, 'a') as f:
                f.write(icon)
            files.finalize(img)

            icon = str(files.blobstore.get_blob_key(img))
            logging.error(icon)

        if self._checkurl(url) and self._checkname(name):
            p = Project(
                    key_name = name.strip().lower(),
                    fullName = fullName.strip(),
                    name = name,
                    url = self._validurl(url),
                    about = desc,
                    icon = icon,
                    admins = [self.user.key()],
                    joinDate = datetime.datetime.now(),
                    secret = str(uuid.uuid4())
                    )
            db.put(p)
            self.user.admins.append(p.key())
            self.user.projects.append(p.key())
            db.put(self.user)

            rurl = "/admin/project/%s" % name
            self.redirect(rurl)
            return

        self.redirect('/')

class AdminCollection(BaseHandler):
    def post(self,action):
        self.get(action)

    def get(self,action):
        self.update=False
        if action=='create':
            self._createcollection()
        if action=='add':
            self._editbadge()
        if action=='modify':
            self.update=True
            self._editbadge()

    def _titletaken(self, title):
        """Returns true if a Collection title is already taken."""
        c = db.get(db.Key.from_path('Collection', title))
        return c is not None
        
    def _checktitle(self, collection, title):
        co = db.get(db.Key.from_path('Collection', collection, 'Badge', title))
        return True if co is None else False

    def _editbadge(self):
        try:
            self.user = UserModel.all().filter('md5 = ', self.usermd5).fetch(1)[0]
        except:
            self.user = None

        if not self.user:
            self.redirect('/home')
            return

        title = self.request.get('badge-title', None)
        desc = self.request.get('badge-description', None)

        coll = self.request.get('collection-identifier', None)
        icon = self.request.get('badge-icon')

        coll_key = re.sub(r'[^a-zA-Z0-9-]', '_', coll.strip().lower())
        bkn = re.sub(r'[^a-zA-Z0-9-]', '_', title.strip().lower())

        if self.request.get('action', None) == "cancel":
            self.redirect('/admin/collection/%s' % coll_key)
            return

        if not self.update:
            if not self._checktitle(coll_key, bkn):
                rurl = "/admin/collection/%s" % bkn
                self.redirect(rurl)
                return
        if self._hascollectionauthority(coll_key):
            if self.update:
                bg = db.get(db.Key.from_path('Collection',coll_key,'Badge',bkn))
                logging.error(bg)
                logging.error(bg.title)
            else:
                bg = Badge(
                        parent = db.Key.from_path('Collection',coll_key),
                        key_name = bkn,
                        title = title,
                        collection = db.Key.from_path('Collection',coll_key),
                        )

            if desc and desc.strip() != "":
                bg.about = desc

            if icon:
                img = files.blobstore.create(mime_type='img/png')
                with files.open(img, 'a') as f:
                    f.write(icon)
                files.finalize(img)

                icon = str(files.blobstore.get_blob_key(img))
                bg.icon = str(icon)

            db.put(bg)

        self.redirect('/admin/collection/%s' % coll_key)
        return

    def _createcollection(self):
        if self.request.get('action', None) == "cancel":
            self.redirect('/home')
            return

        try:
            self.user = UserModel.all().filter('md5 = ', self.usermd5).fetch(1)[0]
        except:
            self.user = None

        if not self.user:
            self.redirect('/home')
            return

        title = self.request.get('collection-title', None)
        desc = self.request.get('collection-description', None)
        proj = self.request.get('project-identifier', None)
        
        if not self._titletaken(title) and self._hasprojectauthority(proj):        

            proj_key = db.Key.from_path('Project', proj.strip().lower())

            kn = re.sub(r'[^a-zA-Z0-9-]', '_', title.strip().lower())
            col = Collection(
                        key_name = kn,
                        title = title,
                        about = desc,
                        projects = [proj_key]
                        )
            db.put(col)

            p = Project.get(proj_key)
            p.collections.append(col.key())
            db.put(p)

            rurl = "/admin/collection/%s" % kn
            self.redirect(rurl)
            return

        self.redirect('/project/%s' % proj.strip().lower())

class CollectionProfile(BaseHandler):
    def post(self,cid):
        self.get(cid)

    def get(self,cid):
        self.push_html('public_collection_profile.html')

class CollectionProfileAdmin(BaseHandler):
    def post(self,cid):
        self.get(cid)

    def get(self,cid):
        um = UserModel.all().filter('md5 = ',self.usermd5).fetch(1)
        if len(um)>0:
            um = um[0]
            col = Collection.get_by_key_name(cid.lower().strip())
            a = False
            for p in um.admins:
                if p in col.projects:
                    a = True

            if a:
                self.push_html('admin_collection_profile.html')
                return

        self.redirect('/home')
        return



application = webapp.WSGIApplication([('/', SiteHome),
                                      ('/user/([^/]+)', UserProfile),
                                      ('/home', UserAdmin),
                                      ('/collection/([^/]+)', CollectionProfile),
                                      ('/project/([^/]+)', ProjectProfile),
                                      ('/admin/project/([^/]+)', ProjectProfileAdmin),
                                      ('/admin/collection/([^/]+)', CollectionProfileAdmin),
                                      ('/org/user/([^/]+)', AdminUser),
                                      ('/org/project/([^/]+)', AdminProject),
                                      ('/org/collection/([^/]+)', AdminCollection),
                                      #('/new', AdminProject),
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
