#
# Copyright 2012 Dan Salmonsen
#
from protorpc.wsgi import service
import webapp2, os, json
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch, users
from google.appengine.ext import db
from datetime import datetime, timedelta
from random import randint
from re import sub
from lxml import etree, html
from lxml.html import tostring, fragment_fromstring
from pickle import dumps, loads

class Articles(db.Model):
  """Models an individual Archive entry"""
  author = db.StringProperty()
  embed = db.TextProperty()
  title = db.StringProperty()
  content = db.TextProperty()
  tags = db.TextProperty()
  comments = db.ListProperty(db.Text)
  view = db.StringProperty() #Publish, Preview or Retract
  date = db.DateTimeProperty(auto_now_add=True)

def archive_key(Archive_name=None):
  """Constructs a Datastore key for an Archive entity."""
  return db.Key.from_path('Archive', Archive_name or 'test_archive')
  
def innerHTML(file, tag):
  tree = html.parse(file)
  return ''.join([tostring(child) for child in tree.xpath(tag)[0].iterchildren()])

def format_comments(comments=None, article_id=None):
  template_data = {
          'user_activity': '',
          'article_id': article_id,}
  comment_box = ('<form class="comment-form" name="comment-form" action="/comment-on?id=%s" method="post">'
                  '<textarea class="comment-text" name="comment-text" title="add your comment..."></textarea>'
                  '</form>' % article_id)
#todo - build comment tree by replacing and adding.
#todo - add delete comment or report abuse.
  path = os.path.join(os.path.dirname(__file__), 'comment-table-template.html' )
  all_comments = '<div class="below-video tags">Comments:<table><tbody id="comment-table-' + str(article_id) + '">'
  comment_id = 0
  for comment in comments:
    template_data.update({
        'comment_id': str(article_id) + '-' + str(comment_id),
        'comment_display': loads(comment)[0],
        'nickname': loads(comment)[1],
        'comment_date': loads(comment)[2],
        'time_now': datetime.now()
        })
    comment_id += 1
    tree = fragment_fromstring(template.render(path, template_data), create_parent=False)
    all_comments += tostring(tree.xpath('//tr')[0])
  #place an empty hidden comment last
  template_data.update({'comment_id': str(article_id) + '-' + str(comment_id)})
  tree = fragment_fromstring(template.render(path, template_data), create_parent=False)
  all_comments += tostring(tree.xpath('//tr')[1])
  all_comments += '</tbody>'
  all_comments += tostring(tree.xpath('//tfoot')[0]) + '</table></div>'
  return all_comments
  
def get_articles(author=None):
  """Retrieves articles from Archive entity and composes HTML."""
  if author is None:
    articles = db.GqlQuery("SELECT * "
                           "FROM Articles "
                           "WHERE ANCESTOR IS :key "
                           "AND view = 'Publish' "
                           "ORDER BY date DESC LIMIT 20",
                           key=archive_key())
  else:
    articles = db.GqlQuery("SELECT * "
                           "FROM Articles "
                           "WHERE ANCESTOR IS :key "
                           "AND author = :by_author "
                           "ORDER BY date DESC LIMIT 20",
                           key=archive_key(), by_author = author)

  all_articles =''

  for article in articles:
    edit_link = ''
    view_status = ''
    if str(users.get_current_user()) == article.author:
      edit_link = '<a class="links" href="/edit-article-form?id=%s">edit</a>' % article.key().id()
      if article.view != 'Publish':
         view_status = '<a class="view-status" href="/edit-article-form?id=%s">not published</a>' % (article.key().id())
    #todo - move to article template file
    all_articles += '<div class="embed">%s</div>' % article.embed
    all_articles += '<div class="title"> %s ' % article.title
    all_articles += '<span class="author"> by %s </span>' % article.author.split('@',2)[0]
    all_articles += '<span> %s %s </span></div>' % (view_status, edit_link)
    all_articles += '<div class="below-video article"><pre>%s</pre></div>' % article.content
    all_articles += '<div class="below-video tags">Tags: %s</div>' % article.tags
    all_articles += format_comments(article.comments, article.key().id())
  return all_articles

class TestPage(webapp2.RequestHandler):
  pass
# test page stub

class MainPage(webapp2.RequestHandler):
  def get(self):
    template_data = {
            'the_archive': 'class="active"',
            'my_articles': '',
            'publish_article': '',
            'about': '',
            'center_stage': get_articles()
            }
    user = users.get_current_user()
    if user:
      template_data.update({'greeting': ('<div class="signed-in" nickname="%s"> %s <a class="sign-out" href="%s">(sign out)</a></div>' % (user.nickname(), user.nickname(), users.create_logout_url("/")))})
      template_data.update({'nickname': user.nickname()})
    else:
      template_data.update({'greeting': ('<a id="not-signed-in" class="sign-in" href="%s">Sign in or register</a>' % users.create_login_url("/"))})
      template_data.update({'nickname': ''})

    if self.request.path == '/my-articles':
      template_data.update({
        'the_archive': '',
        'my_articles': 'class="active"',
        'publish_article': '',
        'about': '',
        'center_stage': get_articles(template_data['nickname'])})

    if self.request.path == '/about':
      tree = html.parse('About-the-Art-Crime-Archive.html')
      template_data.update({
        'the_archive': '',
        'my_articles': '',
        'publish_article': '',
        'about': 'class="active"',
        'style':  tostring(tree.xpath('//style')[0]),
        'center_stage': innerHTML('About-the-Art-Crime-Archive.html', 'body')})

    path = os.path.join(os.path.dirname(__file__), 'index.html' )
    self.response.headers['X-XSS-Protection'] = '0' #prevents blank embed after post
    self.response.out.write(template.render(path, template_data))

class PublishArticleForm(webapp2.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if user:
      greeting = "<span class=\"signed-in\"> %s</span>" % user.nickname()
      template_values = {
              'greeting': greeting,
              'user': user.nickname(),
              }
    else:
      return self.redirect(users.create_login_url("/publish-article-form"))
      
    self.response.out.write('<html><body><p>Article will be published by: %s</p>' % greeting)
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
    article.content = self.request.get('content')
    article.tags = self.request.get('tags')
    article.view = self.request.get('view')
    article.put()
    if article.view == 'Preview' or article.view == 'Retract':
      return self.redirect('/my-articles')
    return self.redirect('/')

class Comment(webapp2.RequestHandler):
  def post(self):
    if self.request.get('id') is not '':
      article_id = int(self.request.get('id'))
      article = Articles(parent=archive_key()).get_by_id(article_id, parent=archive_key())
    else:
      article = Articles(parent=archive_key())

    pickled = db.Text(dumps([self.request.get('comment-text'), users.get_current_user(), datetime.now()]))
    article.comments.append(pickled)
    article.put()
    return self.redirect('/')

class EditArticleForm(webapp2.RequestHandler):
  def get(self):
    article_id = int(self.request.get('id'))
    article = Articles(parent=archive_key()).get_by_id(article_id, parent=archive_key())
    
    user = users.get_current_user()
    if not user:
      return self.redirect(users.create_login_url("/"))

    self.response.out.write('<html><body><p>Article will be published by: %s</p>' % user.nickname().split('@',2)[0])
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
                               ('/my-articles', MainPage), 
                               ('/about', MainPage),                               
                               ('/publish-article-form', PublishArticleForm),
                               ('/edit-article-form', EditArticleForm),
                               ('/publish-it', PublishArticle),
                               ('/comment-on', Comment)],
                                debug=True)
