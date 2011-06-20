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


class OrganizeHandler(webapp.RequestHandler):
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
    def _hasprojectauthority(self):
        if self.project.key() in self.usermodel.admins:
            return True
        else:
            return False

    def _hascollectionauthority(self):
        a = False
        for p in self.usermodel.admins:
            if p in self.collection.projects:
                a = True
        return a
        
    def toid(self,title):
        return re.sub(r'[^a-zA-Z0-9-]', '_', title.strip().lower())
    
    def _validurl(self, url):
        url = url.lower().lstrip('http://')
        return "http://" + url

class AdminUser(OrganizeHandler):
    def post(self,action):
        self.get(action)

    def get(self,action):
        if self.request.get('action', None) == "cancel":
            self.redirect('/home')
            return
        if action=='create':
            self._createuser()
        if action=='request-invite':
            self._requestinvite()

    def _createuser(self):
        nickname = self.request.get('nickname', None)
        if self.user is not None and self.usermodel is None:
            u = UserModel(
                    key_name = self.toid(nickname),
                    nickname = nickname,
                    user = self.user,
                    md5 = str(self.usermd5),
                    about = self.request.get('about', None),
                    joinDate = datetime.datetime.now()
                    )
            db.put(u)

        self.redirect('/home')
        
    def _requestinvite(self):
        if self.user is not None and self.usermodel is not None:
            c = CommplishInvites(
                    parent = self.usermodel,
                    user = self.user,
                    about = self.request.get('invite-description', None)
                )
            db.put(c)
            self.usermodel.limit = 0
            db.put(self.usermodel)
            
            
        self.redirect('/home')

class AdminProject(OrganizeHandler):
    def post(self,action):
        self.get(action)

    def get(self,action):
        """all requests require a valid user"""
        if not self.usermodel:
            self.redirect('/')
            return
            
        if action=='create':
            self._createproject()
            
        else:
            """Handles a collection action by joining, following, or dropping a collection."""
            self.pid = self.request.get('project-id', None) # Project id
            self.cid = self.request.get('collection-id', None) # Collection id
            self.uid = self.request.get('admin-user-id', None) # User id
            
            """if from a 'cancel' request, send them away"""
            if self.request.get('action', None) == "cancel":
                self.redirect('/home')
                return
            
            if action == 'get-secret':
                self.secret('get')
                return
            elif action == 'reset-secret':
                self.secret('reset')
                return
            
            if action == 'add-admin':
                self._addadmin()
            else:
                if not self.pid or not self.cid:
                    logging.error('Unable to join collection %s to project %s' % (self.cid, self.pid))
                    self.redirect('/home')
                    return
                elif action == 'join-collection':
                    self._handlecollection('join')
                elif action == 'follow-collection':
                    self._handlecollection('follow')
                elif action == 'drop-collection':
                    self._handlecollection('drop')
                
    def secret(self, action):
        self.project = Project.fromname(self.pid)
        # Verify that usermodel is admin of project
        if not self._hasprojectauthority():
            logging.error('Not authorized on project id ' + self.pid)
            self.redirect('/home')
        if action=='get':
            out = {'secret': self.project.secret}
            self.response.out.write(
                simplejson.dumps(out)
            )
            return
        elif action=='reset':
            #TODO reset secret
            pass
        
    def _handlecollection(self, action):
        self.project = Project.fromname(self.pid)
        self.collection = Collection.fromtitle(self.cid)
        
        # Verify that usermodel is admin of project
        if not self._hasprojectauthority():
            logging.error('Not authorized on project id ' + self.pid)
            self.redirect('/home')
            
        # Gets the Project entity for pid and redirects if None:
        if not self.project:
            logging.error('Invalid project id ' + self.pid)
            self.redirect('/home')
            return

        # Gets the Collection entity for cid and redirects if None:
        if not self.collection:
            logging.error('Invalid collection %s' % self.cid)
            self.redirect('/home')
            return
        
        pkey = self.project.key()
        ckey = self.collection.key()

        # Updates Collection and Project entities based on action:
        if action == 'join':
            if pkey not in self.collection.projects_joined:            
                self.collection.projects_joined.append(pkey)        
                self.collection.put()
            if ckey not in self.project.collections_joined:
                self.project.collections_joined.append(ckey)
                self.project.put()
        elif action == 'follow':
            """projects don't need to follow project's they have joined"""
            if pkey not in self.collection.projects_joined:
                if pkey not in self.collection.projects_following:
                    self.collection.projects_following.append(pkey)
                    self.collection.put()
                if ckey not in self.project.collections_following:
                    self.project.collections_following.append(ckey)
                    self.project.put()
        elif action == 'drop':
            self.collection.projects.remove(pkey)
            self.collection.projects_following.remove(pkey)
            self.collection.projects_joined.remove(pkey)
            self.collection.put()
            self.project.collections.remove(ckey)
            self.project.collections_following.remove(ckey)
            self.project.collections_joined.remove(ckey)
            self.project.put()

        logging.info('Joined collection %s with project %s' % (self.cid, self.pid))    
        self.redirect('/admin/project/%s' % self.pid)    

    def _addadmin(self):
        """Adds an admin user to a project."""
        # Gets the Project entity for pid and redirects if None:
        self.project = Project.fromname(self.pid)
        
        
        if not self.project:
            logging.error('Invalid project id ' + self.pid)
            self.redirect('/home')
            return
            
        # Verify that usermodel is admin of project
        if not self._hasprojectauthority():
            logging.error('Not authorized on project id ' + self.pid)
            self.redirect('/home')
            
        # Gets the UserModel entity for uid and redirects if None:
        self.newadmin = UserModel.get_by_key_name(self.toid(self.uid))
        if not self.newadmin:
            logging.error('Invalid user id ' + self.uid)
            self.redirect('/home')
            return
        
        # Connects the user and the project without introducing duplicates:
        pkey = self.project.key()
        if pkey not in self.newadmin.projects:            
            self.newadmin.projects.append(pkey)        
            self.newadmin.put()
        ukey = self.newadmin.key()
        if ukey not in self.project.admins:
            self.project.admins.append(ukey)
            self.project.put()

        logging.info('Connected uid %s to pid %s' % (self.uid, self.pid))    
        self.redirect('/admin/project/%s' % self.pid)    

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

    def _createproject(self):
        if self.usermodel.limit <= len(self.usermodel.admins):
            self.redirect('/home')
            return
        else:
            fullName = self.request.get('project-full-name', None)
            name = self.request.get('project-name', None)
            url = self.request.get('project-url', None)
            desc = self.request.get('project-description', None)
            icon = self.request.get('project-icon')
            """create a blobstore entity for the icon"""
            if icon:
                img = files.blobstore.create(mime_type='img/png')
                with files.open(img, 'a') as f:
                    f.write(icon)
                files.finalize(img)
                icon = str(files.blobstore.get_blob_key(img))
                
            """verify that the url and name are unique"""
            if self._checkurl(url) and self._checkname(name):
                p = Project(
                        key_name = self.toid(name),
                        fullName = fullName.strip(),
                        name = name,
                        url = self._validurl(url),
                        about = desc,
                        icon = icon,
                        admins = [self.usermodel.key()],
                        joinDate = datetime.datetime.now(),
                        secret = str(uuid.uuid4())
                        )
                db.put(p)
                self.usermodel.admins.append(p.key())
                self.usermodel.projects.append(p.key())
                db.put(self.usermodel)

                rurl = "/admin/project/%s" % name
                self.redirect(rurl)
                return
            else:
                self.redirect('/home')
                return

class AdminCollection(OrganizeHandler):
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
        if action == 'invite':
            self._invite()
        if action == 'accept-invite':
            self._acceptinvite()
            
    def _acceptinvite(self):
        self.pid = self.request.get('pid', None)
        self.cid = self.request.get('cid', None)
        token = self.request.get('token', None)
        if not self.pid or not self.cid or not token:
            logging.error('Unable to accept invitation')
            self.response.out.write('Sorry, invalid request parameters')
            return

        self.project = Project.fromname(self.pid)
        self.adminuser = UserModel.frommd5(token)
        self.collection = Collection.fromtitle(self.cid)
        if not self.project or not self.adminuser or not self.collection:
            logging.error('Unable to accept invitation')
            self.response.out.write('Sorry, invalid request state')
            return

        if self.adminuser.key() not in self.project.admins:
            logging.error('Unable to accept invitation')
            self.response.out.write('Sorry, invalid request admin')
            return
        
        ckey = self.collection.key()
        if ckey not in self.project.collections:
            self.project.collections.append(ckey)
            self.project.put()
        pkey = self.project.key()
        if pkey not in self.collection.projects:
            self.collection.projects.append(pkey)
            self.collection.put()

        self.response.out.write(
            'Thanks %s! Your project %s is now connected to the %s badge collection!' % \
                (adminuser.nickname, project.fullName, collection.title))
                                    
    def _invite(self):
        """Invites a project admin to join a collection."""
        pid = self.request.get('invited-project-id', None)
        cid = self.request.get('collection-id', None)
        if not pid or not cid:
            logging.error('Unable to invite project to collection')
            self.redirect('/home')
            return
        
        project = Project.fromname(pid)
        if not project:
            logging.error('Project for %s does not exits' % pid)
            self.redirect('/home')
            return
        
        collection = Collection.fromtitle(cid)
        if not collection:
            logging.error('Collection for %s does not exist' % cid)
            self.redirect('/home')
            return
                
        # Note this just grabs the first admin but there may be many:
        adminuser = db.get(project.admins[0])
        token = adminuser.md5
        user_address = adminuser.user.email()
        params = urllib.urlencode({'cid':cid, 'pid': pid, 'token': token})
        accept_url = '%s/org/collection/accept-invite?%s' % (self.request.host_url, params)
        logging.info('Confirmation URL: %s' % accept_url)
        sender_address = "Commplish App <invites@appid.appspotmail.com>"
        subject = "You've been invited to join a badge collection!"
        body = """
To accept this invite please click this link:

%s
""" % accept_url

        mail.send_mail(sender_address, user_address, subject, body)
        
    def _titletaken(self, title):
        """Returns true if a Collection title is already taken."""
        c = db.get(db.Key.from_path('Collection', title))
        return c is not None
        
    def _checktitle(self, collection, title):
        co = db.get(db.Key.from_path('Collection', collection, 'Badge', title))
        return True if co is None else False

    def _editbadge(self):
        if not self.user:
            self.redirect('/home')
            return

        title = self.request.get('badge-title', None)
        desc = self.request.get('badge-description', None)

        self.cid = self.toid(self.request.get('collection-identifier', None))
        icon = self.request.get('badge-icon')
        icon_key = self.request.get('badge-icon-key')
        logging.error(icon_key)
        logging.error(icon_key)
        logging.error(icon_key)
        logging.error(icon_key)
        logging.error(icon_key)
        logging.error(icon_key)
        logging.error(icon_key)
        logging.error(icon_key)
        logging.error(icon_key)
        logging.error(icon_key)
        logging.error(icon_key)
        logging.error(icon_key)
        logging.error(icon_key)
        bkn = re.sub(r'[^a-zA-Z0-9-]', '_', title.strip().lower())

        if self.request.get('action', None) == "cancel":
            self.redirect('/admin/collection/%s' % self.cid)
            return
        
        self.collection = db.get(db.Key.from_path('Collection',self.cid))
        if not self.update:
            if not self._checktitle(self.cid, bkn):
                rurl = "/admin/collection/%s" % self.cid
                self.redirect(rurl)
                return
        if self._hascollectionauthority():
            if self.update:
                bg = db.get(db.Key.from_path('Collection',self.cid,'Badge',bkn))

            else:
                bg = Badge(
                        parent = self.collection,
                        key_name = bkn,
                        title = title,
                        collection = self.collection,
                        )

            if desc and desc.strip() != "":
                bg.about = desc

            if icon_key:
                bg.icon = icon_key.strip()
            elif icon:
                img = files.blobstore.create(mime_type='img/png')
                with files.open(img, 'a') as f:
                    f.write(icon)
                files.finalize(img)

                icon = str(files.blobstore.get_blob_key(img))
                bg.icon = str(icon)
                

            db.put(bg)

        self.redirect('/admin/collection/%s' % self.cid)
        return

    def _createcollection(self):
        if self.request.get('action', None) == "cancel":
            self.redirect('/home')
            return
            
        if not self.user:
            self.redirect('/home')
            return

        title = self.request.get('collection-title', None)
        desc = self.request.get('collection-description', None)
        self.pid = self.toid(self.request.get('project-identifier', None))
        
        self.project = db.get(db.Key.from_path('Project', self.pid))
        if not self._titletaken(title) and self._hasprojectauthority():
            
            kn = self.toid(title)
            col = Collection(
                        key_name = kn,
                        title = title,
                        about = desc,
                        projects = [self.project.key()]
                        )
            db.put(col)
            
            self.project.collections.append(col.key())
            db.put(self.project)

            rurl = "/admin/collection/%s" % kn
            self.redirect(rurl)
            return

        self.redirect('/project/%s' % self.pid)





application = webapp.WSGIApplication([('/org/user/([^/]+)', AdminUser),
                                      ('/org/project/([^/]+)', AdminProject),
                                      ('/org/collection/([^/]+)', AdminCollection),
                                      
                                     ],
                                     debug=True)

def main():
    util.run_wsgi_app(application)

if __name__ == "__main__":
    main()
