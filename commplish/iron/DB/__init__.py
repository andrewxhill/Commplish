from google.appengine.ext import db
import os
from aeoid import users


class LoginRecord(db.Model):
  user = users.UserProperty(auto_current_user_add=True, required=True)
  timestamp = db.DateTimeProperty(auto_now_add=True)

class Page(db.Model): #parent as exercise or workout
    """because I don't know if we will expand beyond Exercises and
    Workouts, I'm calling every major submission a 'Page' and then we
    can use the category to determine what it is in order to query a 
    specific stream of page types"""
    summary = db.BlobProperty()
    category = db.CategoryProperty()
class Comment(db.Model): #parent as comment
    summary = db.TextProperty()
    
class UserModel(db.Model):
    brief = db.TextProperty()
    full = db.TextProperty()
    
class ExerciseModel(db.Model):
    content = db.TextProperty()
    
class WorkoutModel(db.Model):
    content = db.TextProperty()

class MuscleModel(db.Model):
    content = db.TextProperty()
    
class MuscleGroup(db.Model):
    name = db.StringProperty()
    description = db.StringProperty()


"""
class MuscleIndex(db.Model):
    name = db.StringProperty()
    description = db.StringProperty()
    relatedMuscles = db.ListProperty(db.Key) #key of related muscles
    muscleGroups = db.ListProperty(db.Key) #key of muscle groups it belongs
    
class UserIndex(db.Model):
    exerciseD =   db.ListProperty(db.Key) #key of upvoted exercises
    exerciseU =   db.ListProperty(db.Key) #key of downvoted exercises
    exerciseStar= db.ListProperty(db.Key) #key of stared exercises
    exerciseOwn = db.ListProperty(db.Key) #key of exercises contributed by user
    exercisePts = db.IntegerProperty(default=0) #the total points the user has gained from exercises contributed
    workoutU =    db.ListProperty(db.Key) #key of upvoted workouts
    workoutD =    db.ListProperty(db.Key) #key of downvoted workouts
    workoutStar = db.ListProperty(db.Key) #key of stared workouts
    workoutOwn =  db.ListProperty(db.Key) #key of workouts contributed by user
    workoutPts =  db.IntegerProperty(default=0) #the total points the user has gained from workouts contributed
    comment   =   db.ListProperty(db.Key) #key of last 5000 comments by user
    commentStar = db.ListProperty(db.Key) #key of stared comments
    commentPts =  db.IntegerProperty(default=0) #the total points the user has gained from comments contributed
    
class ExerciseIndex(db.Model): #parent_key = user?
    title = db.StringProperty()
    description = db.StringProperty()
    upvotes = db.IntegerProperty(default=0)
    downvotes = db.IntegerProperty(default=0)
    stars = db.IntegerProperty(default=0)
    muscle = db.ListProperty(db.Key) #key of muscles targeted
    muscleGroup = db.ListProperty(db.Key) #key of musclegroups targeted
    tags = db.ListProperty(db.Category)
    
class WorkoutIndex(db.Model): #parent_key = user?
    title = db.StringProperty()
    description = db.StringProperty()
    upvotes = db.IntegerProperty(default=0)
    downvotes = db.IntegerProperty(default=0)
    stars = db.IntegerProperty(default=0)
    tags = db.ListProperty(db.Category)
    
class CommentIndex(db.Model): #parent_key = user?
    comment = db.StringProperty()
    author = db.UserProperty()
    date = db.DateTimeProperty()
    where = db.ReferenceProperty()
    stars = db.IntegerProperty(default=0)
"""
