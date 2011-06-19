import md5
import os
import re
import logging
import md5

from google.appengine.ext import db
from google.appengine.api import users

class UserModel(db.Model):
    #key_name = nickname
    nickname = db.StringProperty() #Must be distinct
    user = db.UserProperty(required=True)
    md5 = db.StringProperty()
    about = db.TextProperty()
    joinDate = db.DateTimeProperty()
    projects = db.ListProperty(db.Key)
    admins = db.ListProperty(db.Key) # Project keys
    #badges = RefProp from UserBadge
    @classmethod
    def frommd5(cls, usermd5):
        results = UserModel.all().filter('md5 = ', usermd5).fetch(1)
        if results and len(results) == 1:
            return results[0]
        else:
            return None

    @classmethod
    def fromemail(cls, email):
        """Returns a UserModel for the given email address or None."""
        m = md5.new()
        m.update(email.strip().lower())
        usermd5 = str(m.hexdigest())
        return cls.frommd5(usermd5)

class UserBadge(db.Model):
    #parent = db.Badge
    project = db.StringProperty() #key.str of Project that granted the badge
    user = db.ReferenceProperty(UserModel, collection_name="badges")
    count = db.IntegerProperty() #allows user to receive badge multiple times
    recieved = db.DateTimeProperty()

class Collection(db.Model):
    #key_name = title.strip().lower().replace(' ','_')
    title = db.StringProperty()
    about = db.TextProperty()
    has_badges = db.BooleanProperty(default=True)
    has_ranks = db.BooleanProperty(default=False)
    has_points = db.BooleanProperty(default=False)
    projects = db.ListProperty(db.Key) # Projects that own this collection
    projects_joined = db.ListProperty(db.Key) # Projects that have joined this collection
    projects_following = db.ListProperty(db.Key) # Projects that are following this collection
    #badges = RefProp from Badge

    @classmethod
    def getkeyname(cls, title):
        """Returns key_name from title."""
        return re.sub(r'[^a-zA-Z0-9-]', '_', title.strip().lower())

    @classmethod
    def fromtitle(cls, title):
        """Returns a Collection entity for the given title or None."""
        return Collection.get_by_key_name(cls.getkeyname(title))

class Badge(db.Model):
    #key_name = title.strip().lower().replace(' ','_')
    #parent = Collection
    title = db.StringProperty()
    about = db.TextProperty()
    collection = db.ReferenceProperty(Collection, collection_name="badges")
    icon = db.StringProperty()

class Project(db.Model):
    #key_name = name.lower()
    fullName = db.TextProperty()
    name = db.StringProperty()
    url = db.LinkProperty()
    about = db.TextProperty()
    icon = db.StringProperty()
    collections = db.ListProperty(db.Key) # Collections owned by this project
    collections_following = db.ListProperty(db.Key) # Collections this project are following
    collections_joined = db.ListProperty(db.Key) # Collections this project has joined
    admins = db.ListProperty(db.Key)
    joinDate = db.DateTimeProperty()
    secret = db.StringProperty()
    verified = db.BooleanProperty(default=False)
    
    @classmethod
    def fromname(cls, name):
        """Returns a Project entity for the given project name of None."""
        return Project.get_by_key_name(name.strip().lower())
