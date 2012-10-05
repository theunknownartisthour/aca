#
# Copyright 2012 Dan Salmonsen
#
import webapp2, os, json
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.ext import db
from random import randint
from re import sub

class Articles(db.Model):
  """Models an individual Archive entry"""
  author = db.StringProperty()
  embed = db.TextProperty()
  title = db.StringProperty()
  content = db.TextProperty()
  tags = db.TextProperty(str)
  view = db.StringProperty() #Publish, Preview or Retract
  date = db.DateTimeProperty(auto_now_add=True)

def archive_key(Archive_name=None):
  """Constructs a Datastore key for an Archive entity."""
  return db.Key.from_path('Archive', Archive_name or 'test_archive')

def get_articles():
  """Retrieves articles from Archive entity and composes HTML."""
  articles = db.GqlQuery("SELECT * "
                          "FROM Articles "
                          "WHERE ANCESTOR IS :1 "
                          "ORDER BY date DESC LIMIT 10",
                          archive_key())


  all_articles =''

  for article in articles:
    edit_link = ''
    view_status = ''
    if str(users.get_current_user()) == article.author:
      edit_link = '<a href="\edit-article-form?id=%s">edit</a>' % article.key().id()
      if article.view != 'Publish':
         view_status = '<a class="view-status" href="\edit-article-form?id=%s">not published</a>' % (article.key().id())
      
    all_articles += '%s' % article.embed
    all_articles += '<div class="below-video title">'
    all_articles += '<h3>%s by %s %s %s</h3>' % (article.title, article.author, 
                                                 edit_link, view_status)
    all_articles += '%s</div>' % article.content
    all_articles += '<div class="below-video tags">Tags: %s</div>' % article.tags
    
  return all_articles

class MainPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            greeting = ("<div class=\"signed-in\"> %s <a class=\"sign-out\" href=\"%s\">(sign out)</a></div>" %
                        (user.nickname(), users.create_logout_url("/")))
            template_values = {
                    'random': randint(0, 1),
                    'greeting': greeting,
                    'user': user.nickname(),
                    'articles': get_articles()
                    }
        else:
            greeting = ("<a class=\"sign-in\" href=\"%s\">Sign in or register</a>" %
                        users.create_login_url("/"))
            template_values = {
                    'random': randint(0, 1),
                    'greeting': greeting,
                    }

        path = os.path.join(os.path.dirname(__file__), 'index.html' )
        self.response.out.write(template.render(path, template_values))

class PublishArticleForm(webapp2.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if user:
        greeting = ("<div class=\"signed-in\"> %s <a class=\"sign-out\" href=\"%s\">(sign out)</a></div>" %
                    (user.nickname(), users.create_logout_url("/")))
        template_values = {
                'greeting': greeting,
                'user': user.nickname(),
                }
    else:
        greeting = ("<a class=\"sign-in\" href=\"%s\">Sign in or register</a>" %
                    users.create_login_url("/"))
        template_values = {
                'random': randint(0, 1),
                'greeting': greeting,
                }
    self.response.out.write('<html><body>Article will be posted by: %s' % greeting)
    self.response.out.write("""
          <form action="/publish-it" method="post">
            <div>Embed-code<br /><textarea name="embed-code" rows="6" cols="80"></textarea></div>
            <div><input type="hidden"></div>
            <div>Title<br /><textarea name="title" rows="1" cols="80"></textarea></div>
            <div><input type="hidden"></div>
            <div>Article body<br /><textarea name="content" rows="12" cols="80"></textarea></div>
            <div>Tags<br /><textarea name="tags" rows="1" cols="80"></textarea></div>
            <div><input type="submit" name="view" value="Preview"></div>
          </form>
          """)


class PublishArticle(webapp2.RequestHandler):
  def post(self):

    if self.request.get('id') is not '':
      article_id = int(self.request.get('id'))
      article = Articles(parent=archive_key()).get_by_id(article_id, parent=archive_key())
    else:
      article = Articles(parent=archive_key())

    article.author = users.get_current_user().nickname()
    article.embed = self.request.get('embed-code')
    article.title = self.request.get('title')
    article.content = '<pre class="article">' + self.request.get('content') + '</pre>'
    article.tags = self.request.get('tags')
    article.view = self.request.get('view')
    article.put()
    self.redirect('/')

class EditArticleForm(webapp2.RequestHandler):
  def get(self):
    article_id = int(self.request.get('id'))
    user = users.get_current_user()
    article = Articles(parent=archive_key()).get_by_id(article_id, parent=archive_key())
    
    if user:
        greeting = ("<div class=\"signed-in\"> %s <a class=\"sign-out\" href=\"%s\">(sign out)</a></div>" %
                    (user.nickname(), users.create_logout_url("/")))
        template_values = {
                'greeting': greeting,
                'user': user.nickname(),
                }
    else:
        greeting = ("<a class=\"sign-in\" href=\"%s\">Sign in or register</a>" %
                    users.create_login_url("/"))
        template_values = {
                'random': randint(0, 1),
                'greeting': greeting,
                }
    self.response.out.write('<html><body>Article will be posted by: %s' % greeting)
    self.response.out.write("""
          <form action="/publish-it?id=%s" method="post">
            <div>Embed<br /><textarea name="embed-code" rows="6" cols="80">%s</textarea></div>
            <div><input type="hidden"></div>
            <div>Title<br /><textarea name="title" rows="1" cols="80">%s</textarea></div>
            <div><input type="hidden"></div>
            <div>Article body<br /><textarea name="content" rows="12" cols="80">%s</textarea></div>
            <div>Tags<br /><textarea name="tags" rows="1" cols="80">%s</textarea></div>
            <div><input type="submit" name="view" value="Preview">
            <input type="submit" name="view" value="Retract">
            <input type="submit" name="view" value="Publish"></div>
          </form>
          """ % (article_id, article.embed, article.title, 
                 sub('<[^>]*>', '', article.content), article.tags))

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/publish-article-form', PublishArticleForm),
                               ('/edit-article-form', EditArticleForm),
                               ('/publish-it', PublishArticle)],
                                debug=True)
