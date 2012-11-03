from protorpc import messages
from protorpc import message_types
from protorpc import remote
#from google.appengine.api import users
from pickle import dumps, loads
from datetime import datetime

import main

class Comment(messages.Message):
    article_id = messages.IntegerField(1, required=True)
    comment_text = messages.StringField(2)
    comment_id = messages.IntegerField(3)

class Comments(messages.Message):
    comments = messages.MessageField(Comment, 1, repeated=True)

class GetCommentsRequest(messages.Message):
    limit = messages.IntegerField(1, default=10)

class CommentInfo(messages.Message):
    comment_id = messages.IntegerField(1)
    user_url = messages.StringField(2)
    user_activity  = messages.StringField(3)
    nickname  = messages.StringField(4)
    
class ArchiveService(remote.Service):
    # Add the remote decorator to indicate the service methods
    @remote.method(Comment, CommentInfo)
    def post_comment(self, request):
      article = main.Articles(parent=main.archive_key()).get_by_id(request.article_id, parent=main.archive_key())
      nickname = main.users.get_current_user()
      pickled = main.db.Text(dumps([request.comment_text, nickname, datetime.now()]))
      article.comments.append(pickled)
      article.put()
      comment_id = len(article.comments) - 1
      return CommentInfo( comment_id = comment_id,
                          user_url = 'todo',
                          user_activity = 'todo',
                          nickname = str(nickname))
        
    @remote.method(Comment, message_types.VoidMessage)
    def edit_comment(self, request):
      article = main.Articles(parent=main.archive_key()).get_by_id(request.article_id, parent=main.archive_key())
      nickname = main.users.get_current_user()
      pickled = main.db.Text(dumps([request.comment_text, nickname, datetime.now()]))
      article.comments[request.comment_id] = pickled
      article.put()
      return  message_types.VoidMessage()
        
    @remote.method(Comment, message_types.VoidMessage)
    def delete_comment(self, request):
      article = main.Articles(parent=main.archive_key()).get_by_id(request.article_id, parent=main.archive_key())
      pickled = main.db.Text(dumps(['deleted', '', datetime.now()]))
      article.comments[request.comment_id] = pickled
      article.put()
      return  message_types.VoidMessage()

    @remote.method(GetCommentsRequest, Comments)
    def get_comments(self, request):
#      for comment in main.Articles.get_by_id(request.article_id, parent=main.archive_key()).comments
#        loads(comment)
#structure the return
        return "not implemented - incomplete stub"

