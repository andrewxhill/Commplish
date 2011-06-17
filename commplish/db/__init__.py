from google.appengine.ext import db
import os
from aeoid import users


class LoginRecord(db.Model):
    user = users.UserProperty(auto_current_user_add=True, required=True)
    timestamp = db.DateTimeProperty(auto_now_add=True)
    
class UserModel(db.Model):
    #key_name = nickname
    nickname = db.StringProperty() #Must be distinct
    user = users.UserProperty(required=True)
    md5 = db.StringProperty()
    about = db.TextProperty()
    joinDate = db.DateTimeProperty()
    projects = db.ListProperty(db.Key)
    admins = db.ListProperty(db.Key)
    #badges = RefProp from UserBadge

class UserBadge(db.Model):
    #parent = db.Badge
    project = db.StringProperty() #key.str of Project that granted the badge
    user = db.ReferenceProperty(UserModel, collection_name="badges")
    recieved = db.DateTimeProperty()
   
class Collection(db.Model):
    title = db.StringProperty()
    about = db.TextProperty()
    has_badges = db.BooleanProperty(default=True)
    has_ranks = db.BooleanProperty(default=False)
    has_points = db.BooleanProperty(default=False)
    projects = db.ListProperty(db.Key)
    #badges = RefProp from Badge
    
class Badge(db.Model):
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
    collections = db.ListProperty(db.Key)
    admins = db.ListProperty(db.Key)
    joinDate = db.DateTimeProperty()
    secret = db.StringProperty()
    verified = db.BooleanProperty(default=False)
