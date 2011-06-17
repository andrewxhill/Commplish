"""
Copyright (C)  2011 Aaron Steele, Andrew Hill, Sander Pick
"""
import cgi
import logging
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template
from aeoid import users
from aeoid import middleware
from iron.DB import *
import simplejson
import pickle
import md5
import os

EXAMPLE_EXERCISES = {
    0: {
        "type": "workout",
        "key": "f34f33jFE",
        "title": "Basic Upper Arm",
        "experienceCategory": "All",
        "targetCategory": "Building",
        "equipment": ["dumbbell","barbell",],
        "description": "A two exercise workout for strengthening the upper arm",
        "instructions": "Perform this workout 2-3 times per week. Target weights with which you can 3 sets of 5-7 reps with accurate motions for each exercise. Step up your weights when you can consistently perform 8-10 reps in each set.",
        "muscles": ["Biceps Brachii","Triceps Brachii",],
        "muscleGroups": ["Upper Arm",],
        "tags": ["arms","upper arm",],
        "comments": 3,
        "starred": 14,
        "upvotes": 23,
        "downvotes": 3,
        "timestamp": "2011-03-06 16:38:56.196422",
        "submitter": {"nickname": "Andrew Hill",
                      "email": "andrewxhill@gmail.com",
                      "avatar": "http://www.gravatar.com/avatar/35f4d000a88cdbcf6392dfb206ebd5e2",
                      "id": 1234,
                     },
        "exercises":{1: {"title": "Dumbbell Curl",
                         "experienceCategory": "All",
                         "targetCategory": "General Fitness",
                         "key": "aFe34Fes",
                         "equipment": ["dumbbell",],
                         "description": "The commmon curl to target the bicep",
                         "muscles": ["Biceps Brachii",],
                         "muscleGroups": ["Upper Arm",],
                         "methodSubmitter": {"nickname": "Andrew Hill",
                                             "email": "andrewxhill@gmail.com",
                                             "avatar": "http://www.gravatar.com/avatar/35f4d000a88cdbcf6392dfb206ebd5e2",
                                             "id": 1234,
                                            },
                         "workoutInstructions": "3 sets of 5-7 reps",
                        },
                     2: {"title": "Barbell Triceps Extension",
                         "experienceCategory": "All",
                         "targetCategory": "General Fitness",
                         "key": "kIeieF83k",
                         "equipment": ["barbell",],
                         "description": "Two handed overhead extension to target triceps",
                         "muscles": ["Triceps Brachii",],
                         "muscleGroups": ["Upper Arm",],
                         "methodSubmitter": {"nickname": "Sander Pick",
                                             "email": "sanderpick@gmail.com",
                                             "avatar": "http://www.gravatar.com/avatar/ac38ba214848deb3184905444d9dc9f3",
                                             "id": 1234,
                                            },
                         "workoutInstructions": "3 sets of 5-7 reps",
                        },
                    },
    },
    1: {
        "type": "exercise",
        "key": "aFe34Fes",
        "title": "Dumbbell Curl",
        "experienceCategory": "All",
        "targetCategory": "General Fitness",
        "equipment": ["dumbbell",],
        "description": "The commmon curl to target the bicep",
        "muscles": ["Biceps Brachii",],
        "muscleGroups": ["Upper Arm",],
        "workouts": 12,
        "methods": 5,
        "comments": 23,
        "starred": 214,
        "timestamp": "2011-03-06 12:38:56.196422",
        "submitter": {"nickname": "Andrew Hill",
                      "email": "andrewxhill@gmail.com",
                      "avatar": "http://www.gravatar.com/avatar/35f4d000a88cdbcf6392dfb206ebd5e2",
                      "id": 1234,
                     },
        "topMethod": {"submitter": {"nickname": "Andrew Hill",
                                    "email": "andrewxhill@gmail.com",
                                    "avatar": "http://www.gravatar.com/avatar/35f4d000a88cdbcf6392dfb206ebd5e2",
                                    "id": 1234,
                                   },
                      "timestamp": "2011-03-06 12:48:56.196422",
                      "description": {"before": "Position two dumbbells to sides, palms facing in, arms straight.",
                                      "during": "With elbows to sides, raise one dumbbell and rotate forearm until forearm is vertical and palm faces shoulder. Lower to original position and repeat with opposite arm. Continue to alternate between sides.",
                                      "after": "Let arm rest in a relaxed position for 20-40 seconds",
                                      "extra": "Biceps may be exercised alternating (as described), simultaneous, or in simultaneous-alternating fashion. When elbow is fully flexed, it can travel forward slightly allowing forearms to be no more than vertical. This additional movement allows for relative release of tension in muscles between repetitions.",
                                     },
                      "upvotes": 16,
                      "downvotes":  3,
                      "starred": 14,
                     },
        "tags": ["arms","bicep","curl",],
    },
    2: {
        "type": "exercise",
        "title": "Barbell Triceps Extension",
        "experienceCategory": "All",
        "targetCategory": "General Fitness",
        "key": "kIeieF83k",
        "equipment": ["barbell",],
        "description": "Two handed overhead extension to target triceps",
        "muscles": ["Triceps Brachii",],
        "muscleGroups": ["Upper Arm",],
        "workouts": 8,
        "methods": 2,
        "comments": 5,
        "starred": 194,
        "timestamp": "2011-03-06 10:38:56.196422",
        "submitter": {"nickname": "Aaron Steele",
                      "email": "eightysteele@gmail.com",
                      "avatar": "http://www.gravatar.com/avatar/adf45959890c5de375f36e638dd159b9",
                      "id": 1234,
                     },
        "topMethod": {"submitter": {"nickname": "Sander Pick",
                                    "email": "sanderpick@gmail.com",
                                    "avatar": "http://www.gravatar.com/avatar/ac38ba214848deb3184905444d9dc9f3",
                                    "id": 1234,
                                   },
                      "timestamp": "2011-03-06 10:48:56.196422",
                      "description": {"before": "Position barbell overhead with narrow overhand grip.",
                                      "during": "Lower forearm behind upper arm with elbows remaining overhead. Extend forearm overhead. Lower and repeat.",
                                      "after": "Let arm rest in a relaxed position for 20-40 seconds",
                                      "extra": "Let barbell pull arm back to maintain full shoulder flexion. Exercise may be performed standing or on seat with or without back support.",
                                     },
                      "upvotes": 26,
                      "downvotes":  4,
                      "starred": 1,
                     },
        "tags": ["arms","triceps","extension",],
    },}
    
class UserProfile():
    def __init__(self):
        self.user = users.get_current_user()
        m = md5.new()
        m.update(self.user.email().strip().lower())
        self.user.md5 = str(m.hexdigest())
        self.key = db.Key.from_path('UserModel',str(self.user.user_id()))
        self.model = UserModel.get(self.key)
        if self.model is None:
            """if the user isn't in the UserModel table, create a new entry"""
            self.model = UserModel(key=self.key)
    def brief(self):
        if self.model.brief is None:
            """if no user brief profile exists, create an empty one to start"""
            out = {"icon":"http://www.gravatar.com/avatar/%s" % self.user.md5,
                    "email": self.user.email(),
                    "nickname": self.user.nickname(),
                    "id": str(self.user.user_id()),
                    "workouts": {"starred": [],
                                 "owned": [],
                                 "recent": [],},
                    "execises": {"starred": [],
                                 "owned": [],
                                 "recent": [],},
                    "comments": {"starred": [],
                                 "owned": [],
                                 "recent": [],},
                    "badges": [],
                    "score": 0,
                   }
            self.model.brief = db.Blob(pickle.dumps(out))
            self.model.put()
        return pickle.loads(str(self.model.brief))
            
    def full(self):
        if self.model.full is None:
            pass
        return self.model.full
        
class UserInfo(webapp.RequestHandler):
  def get(self):
      self.post()
  def post(self):
    out = None
    if users.get_current_user():
        fullprofile = False if not self.request.params.get('profile', False) else True
        self.response.headers['Content-Type'] = 'application/json'
        out = UserProfile().brief()
    else:
        cont = self.request.params.get('continue', "/") 
        out = {'login_url': users.create_login_url(cont)}
    self.response.out.write(simplejson.dumps(out))

class SiteActivity(webapp.RequestHandler):
    """given either /api/activity/posts or /api/activity/comments this
    will give back a stream of the most recent submissions. Default 
    number returned in the array is 10."""
    def get(self,method):
        self.post(method)
    def post(self,method):
        out = []
        n = self.request.params.get('length') 
        try:
            n = int(n)
        except:
            n = 10
        logging.error('hi')
        if method=="posts":
            out = [i for i in Page.all().fetch(n)]
            out = EXAMPLE_EXERCISES
        elif method=="comments":
            out = [i for i in Comment.all().fetch(n)]
        self.response.out.write(simplejson.dumps(out))
      
      
class AddNewPost(webapp.RequestHandler):
    """Accepts a new Exercise or Workout"""
    def post(self,type):
        if type=="exercise":
            pass
            
            
      
      
application = webapp.WSGIApplication([('/api/user', UserInfo),
                                      ('/api/activity/([^/]+)', SiteActivity),
                                      ('/api/post/([^/]+)', AddNewPost),
                                     ],      
                                     debug=False)
application = middleware.AeoidMiddleware(application)

def main():
  util.run_wsgi_app(application)

if __name__ == "__main__":
  main()
