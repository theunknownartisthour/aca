#
# Copyright 2012 Dan Salmonsen
#
# todo - create single page template that works for all site URLS
# todo - active link set by javascript based on page URL
# todo - History.js based navigation
# todo - hide / show relevent content
# scroll / multi-page load
# unique URL for each article
# check user before allowing edit of form.

from protorpc.wsgi import service
import webapp2, os, json
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch, users
from google.appengine.ext import db
from datetime import datetime, timedelta
from dateutil import parser
from random import randint
from re import sub
from lxml import etree, html
from lxml.html import tostring, fragment_fromstring
from pickle import dumps, loads

from authomatic import Authomatic
from authomatic.adapters import Webapp2Adapter
from config import CONFIG

authomatic = Authomatic(config=CONFIG, secret='some random secret string')

class Login(webapp2.RequestHandler):
    
    # The handler must accept GET and POST http methods and
    # Accept any HTTP method and catch the "provider_name" URL variable.
    def any(self, provider_name):
                
        # It all begins with login.
        result = authomatic.login(Webapp2Adapter(self), provider_name)
        
        # Do not write anything to the response if there is no result!
        if result:
            # If there is result, the login procedure is over and we can write to response.
            self.response.write('<a href="..">Home</a>')
            
            if result.error:
                # Login procedure finished with an error.
                self.response.write(u'<h2>Error!: {}</h2>'.format(result.error.message))
            
            elif result.user:
                # Hooray, we have the user!
                
                # OAuth 2.0 and OAuth 1.0a provide only limited user data on login,
                # We need to update the user to get more info.
                if not (result.user.name and result.user.id):
                    result.user.update()
                
                # Welcome the user.
                self.response.write(u'<h1>Hi {}</h1>'.format(result.user.name))
                self.response.write(u'<h2>Your id is: {}</h2>'.format(result.user.id))
                self.response.write(u'<h2>Your email is: {}</h2>'.format(result.user.email))
                
                # Seems like we're done, but there's more we can do...
                
                # If there are credentials (only by AuthorizationProvider),
                # we can _access user's protected resources.
                if result.user.credentials:
                    
                    # Each provider has it's specific API.
                    if result.provider.name == 'fb':
                        self.response.write('Your are logged in with Facebook.<br />')
                        
                        # We will access the user's 5 most recent statuses.
                        url = 'https://graph.facebook.com/{}?fields=feed.limit(5)'
                        url = url.format(result.user.id)
                        
                        # Access user's protected resource.
                        response = result.provider.access(url)
                        
                        if response.status == 200:
                            # Parse response.
                            statuses = response.data.get('feed').get('data')
                            error = response.data.get('error')
                            
                            if error:
                                self.response.write(u'Error!: {}!'.format(error))
                            elif statuses:
                                self.response.write('Your 5 most recent statuses:<br />')
                                for message in statuses:
                                    
                                    text = message.get('message')
                                    date = message.get('created_time')
                                    
                                    self.response.write(u'<h3>{}</h3>'.format(text))
                                    self.response.write(u'Posted on: {}'.format(date))
                        else:
                            self.response.write('Unknown Error!<br />')
                            self.response.write(u'Status: {}'.format(response.status))
                        
                    if result.provider.name == 'tw':
                        self.response.write('Your are logged in with Twitter.<br />')
                        
                        # We will get the user's 5 most recent tweets.
                        url = 'https://api.twitter.com/1.1/statuses/user_timeline.json'
                        
                        # You can pass a dictionary of querystring parameters.
                        response = result.provider.access(url, {'count': 5})
                                                
                        # Parse response.
                        if response.status == 200:
                            if type(response.data) is list:
                                # Twitter returns the tweets as a JSON list.
                                self.response.write('Your 5 most recent tweets:')
                                for tweet in response.data:
                                    text = tweet.get('text')
                                    date = tweet.get('created_at')
                                    
                                    self.response.write(u'<h3>{}</h3>'.format(text.replace(u'\u2013', '[???]')))
                                    self.response.write(u'Tweeted on: {}'.format(date))
                                    
                            elif response.data.get('errors'):
                                self.response.write(u'Error!: {}!'.\
                                                    format(response.data.get('errors')))
                        else:
                            self.response.write('Unknown Error!<br />')
                            self.response.write(u'Status: {}'.format(response.status))

#Use flow object to replace login procedure
#from oauth2client.client import OAuth2WebServerFlow

providers = {
    'Google'   : 'https://www.google.com/accounts/o8/id',
    'Yahoo'    : 'yahoo.com',
    'MySpace'  : 'myspace.com',
    'AOL'      : 'aol.com',
    'MyOpenID' : 'myopenid.com'
    # add more here
}

#Steps to using oauth2, 	
#authorize_url = FLOW.step1_get_authorize_url()
#self.redirect(authorize_url)
#credentials = flow.step2_exchange(self.request.params)
#storage = StorageByKeyName(Credentials, user.user_id(), 'credentials')
#storage.put(credentials)

#class oAuthenticate():
#	def get(self):
		#Create a static flow object here
#		flow = OAuth2WebServerFlow(client_id='your_client_id',
#			client_secret='your_client_secret',
#			scope='https://...../auth/something',
#			redirect_uri='https://someurlyouown/auth_return')
#		self.redirect(flow.step1_get_authorize_url())

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
#todo - add report abuse.
  path = os.path.join(os.path.dirname(__file__), 'comment-table-template.html' )
  all_comments = '<div class="below-video comments">Comments:<table>'
  template_data.update({'comment_id': len(comments)})
  tree = fragment_fromstring(template.render(path, template_data), create_parent=False)
  all_comments += tostring(tree.xpath('//tfoot')[0])#needs better element addressing
  all_comments += '<tbody id="comment-table-' + str(article_id) + '">'
  comment_id = 0
  for comment in comments:
    nickname = str(loads(str(comment))[1]).split('@',2)[0]
    template_data.update({
        'comment_id': str(comment_id),
        'comment_display': loads(str(comment))[0],
        'nickname': nickname,
        'comment_date': loads(str(comment))[2],
        'time_now': datetime.now()
        })
    tree = fragment_fromstring(template.render(path, template_data), create_parent=False)
    if nickname != '':
      all_comments += tostring(tree.xpath('//tr')[1])
    else:
      all_comments += tostring(tree.xpath('//tr')[2]) #deleted comment tr
    comment_id += 1
    
  #place an empty hidden comment last
  template_data.update({'comment_id': len(comments)})
  tree = fragment_fromstring(template.render(path, template_data), create_parent=False)
  all_comments += tostring(tree.xpath('//tr')[3]) #hidden comment tr
  all_comments += '</tbody></table></div>'
  return all_comments

def format_article(article, all_articles):
    edit_link = ''
    view_status = ''
    if str(users.get_current_user()) == article.author:
      edit_link = '<a class="links" href="/edit-article-form?id=%s">edit</a>' % article.key().id()
      if article.view != 'Publish':
         view_status = '<a class="view-status" href="/edit-article-form?id=%s">not published</a>' % (article.key().id())
    #todo - move to article template file
    all_articles += '<div class="embed">%s</div>' % article.embed
    all_articles += '<div class="title"> <a class="article-link no-ajax" href="/article?id=%s">%s</a> ' % (article.key().id(), article.title)
    all_articles += '<span class="author"> by %s </span>' % article.author.split('@',2)[0]
    all_articles += '<span> %s %s </span></div>' % (view_status, edit_link)
    all_articles += '<div class="below-video article"><pre>%s</pre></div>' % article.content
    all_articles += '<div class="below-video tags">Tags: %s</div>' % article.tags
    all_articles += format_comments(article.comments, article.key().id())
    return all_articles
	
def get_articles(id=None, author=None, limit=None, bookmark=None):
  """Retrieves articles from Archive entity and composes HTML."""
  if not limit:
    limit = 10

  articles = Articles().all().order("-date")

  if author:
    articles = articles.filter('author =', author)

  next = None
  if bookmark:
    articles = articles.filter('date <=', parser.parse(bookmark)).fetch(limit + 1)
  else:
    articles = articles.fetch(limit + 1)
    
  if len(articles) == limit + 1:
    next = str(articles[-1].date)
  articles = articles[:limit]

  all_articles =''
  for article in articles:
    all_articles = format_article(article, all_articles)

  if next:
    all_articles += '<div class="bookmark" data-bookmark="%s" ></div>' % next
  else:
    all_articles += '<div class="bookmark-end">No more articles.</div>'
  return all_articles

class TestPage(webapp2.RequestHandler):
  pass
# test page stub

class MainPage(webapp2.RequestHandler):
  def get(self):
    style = ''
    user = users.get_current_user()
    if user:
      greeting = ('<div class="signed-in" nickname="%s"> %s <a class="sign-out" href="%s">(sign out)</a></div>' % (user.nickname(), user.nickname(), users.create_logout_url("/")))
      nickname = user.nickname()
    else:
      greeting = 'Sign in with: <a id="not-signed-in" class="sign-in" href="/auth">Login</a>'
      #for name, uri in providers.items():
        #greeting += ('<a id="not-signed-in" class="sign-in" href="%s"> %s</a>' % (users.create_login_url(federated_identity=uri), name))
		#greeting = ('<a id="not-signed-in" class="sign-in" href="%s">Sign in or register</a>' % users.create_login_url("/"))
      nickname = ''

    content = 'No content for this URL'
    content_id =  self.request.path[1:]

    if self.request.get('bookmark'):
      content_id += '-next'
     
    if self.request.path == '/':
      return self.redirect('/the-archive')
      
    if self.request.path == '/article':
      content = format_article(Articles().get_by_id(int(self.request.get('id')), parent=archive_key()), '')
	
    if self.request.path[:12] == '/the-archive':
      for id in open('archive-list.txt', 'r').read().split():
	    content += format_article(Articles().get_by_id(id, parent=archive_key()), '')
                             
    if self.request.path[:12] == '/recent':
      content = get_articles(limit = self.request.get('limit'),
                             bookmark = self.request.get('bookmark'))
                             
    elif self.request.path == '/test':
	  content = ''
    elif self.request.path[:12] == '/my-articles':
      if user:
        content = get_articles(author = user.nickname(),
                               limit = self.request.get('limit'),
                               bookmark = self.request.get('bookmark'))
      else:
        if 'X-Requested-With' in self.request.headers:
          return self.error(500)
        else:
          return self.redirect(users.create_login_url("/my-articles"))
        
    elif self.request.path == '/about':
      tree = html.parse('About-the-Art-Crime-Archive.html')
      style = tostring(tree.xpath('//style')[0])
      content = innerHTML('About-the-Art-Crime-Archive.html', 'body')
	  
    elif self.request.path == '/auth':
      content = innerHTML('loginforms.html', 'body')
  
    template_data = {
            'content_id': content_id,
            'content': content,
            'nickname': nickname,
            'greeting': greeting,
            'style': style,
            }

    path = os.path.join(os.path.dirname(__file__), 'index.html' )
    self.response.headers['X-XSS-Protection'] = '0' #prevents blank embed after post
    self.response.out.write(template.render(path, template_data))

class CreateArticleForm(webapp2.RequestHandler):
  def get(self):
    user = users.get_current_user()
    if user:
      greeting = "<span class=\"signed-in\"> %s</span>" % user.nickname()
      template_values = {
              'greeting': greeting,
              'user': user.nickname(),
              }
    else:
      if 'X-Requested-With' in self.request.headers:
        return self.error(500)
      else:
        return self.redirect(users.create_login_url("/create-article"))
      
    self.response.out.write("""
          <div id="%s" class="center-stage">
          <form action="/publish-it" method="post">
            <div>Embed-code<br /><textarea name="embed-code" rows="6" cols="auto"  class="boxsizingBorder"></textarea></div>
            <div><input type="hidden"></div>
            <div>Title<br /><textarea name="title" rows="1" cols="80"></textarea></div>
            <div><input type="hidden"></div>
            <div>Article body<br /><textarea name="content" rows="12" cols="80"></textarea></div>
            <div>Tags<br /><textarea name="tags" rows="1" cols="80"></textarea></div>
            <div><input type="submit" name="view" value="Preview"></div>
          </form>
          </div>
          """ % self.request.path[1:])


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

class EditArticleForm(webapp2.RequestHandler):
  def get(self):
    article_id = int(self.request.get('id'))
    article = Articles(parent=archive_key()).get_by_id(article_id, parent=archive_key())
    
    user = users.get_current_user()
    if not user:
      return self.redirect(users.create_login_url("/"))

    self.response.out.write("""
        <div id="%s-id-%s" class="center-stage">
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
        </div>  
          """ % (self.request.path[1:], article_id, article_id, article.embed, article.title, 
                 sub('<[^>]*>', '', article.content), article.tags))

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/article', MainPage), 
                               ('/the-archive', MainPage), 
                               ('/the-archive-next', MainPage), 
                               ('/recent', MainPage), 
                               ('/recent-next', MainPage), 
                               ('/my-articles', MainPage), 
                               ('/my-articles-next', MainPage), 
                               ('/about', MainPage), 
                               ('/create-article', CreateArticleForm),
                               ('/edit-article-form', EditArticleForm),
                               ('/test', MainPage),
							   ('/auth', MainPage),
                               ('/publish-it', PublishArticle),
							   webapp2.Route(r'/login/<:.*>', Login, handler_method='any')],
                                debug=True)
