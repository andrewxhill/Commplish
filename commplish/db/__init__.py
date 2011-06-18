from google.appengine.ext import db
import os
from aeoid import users
import md5

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
    admins = db.ListProperty(db.Key) # Project keys
    #badges = RefProp from UserBadge

    @classmethod
    def fromemail(cls, email):
        """Returns a UserModel for the given email address or None."""
        m = md5.new()
        m.update(email.strip().lower())
        usermd5 = str(m.hexdigest())
        results = UserModel.all().filter('md5 = ', usermd5).fetch(1)
        if results and len(results) == 1:
            return results[0]
        else:
            return None


class UserBadge(db.Model):
    #parent = db.Badge
    project = db.StringProperty() #key.str of Project that granted the badge
    user = db.ReferenceProperty(UserModel, collection_name="badges")
    recieved = db.DateTimeProperty()

class Collection(db.Model):
    #key_name = title.strip().lower().replace(' ','_')
    title = db.StringProperty()
    about = db.TextProperty()
    has_badges = db.BooleanProperty(default=True)
    has_ranks = db.BooleanProperty(default=False)
    has_points = db.BooleanProperty(default=False)
    projects = db.ListProperty(db.Key)
    #badges = RefProp from Badge

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
    collections = db.ListProperty(db.Key)
    admins = db.ListProperty(db.Key)
    joinDate = db.DateTimeProperty()
    secret = db.StringProperty()
    verified = db.BooleanProperty(default=False)
