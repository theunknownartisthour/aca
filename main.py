#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2, os, json
from google.appengine.ext.webapp import template
from google.appengine.api import urlfetch
from random import randint
from google.appengine.api import users
from google.appengine.ext import db

class Archive(db.Model):
  """Models an individual Archive entry"""
  author = db.StringProperty()
  embed = db.TextProperty()
  title = db.StringProperty()
  content = db.TextProperty()
  tags = db.ListProperty(str)
  date = db.DateTimeProperty(auto_now_add=True)

def articles_key(Archive_name=None):
  """Constructs a Datastore key for an Archive entity."""
  return db.Key.from_path('Articles', Archive_name or 'default_archive')

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
        self.response.out.write('</body></html>')

class PostArticleForm(webapp2.RequestHandler):
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
          <form action="/post-it?%s" method="post">
            <div>Embed<br /><textarea onfocus="this.value=''" name="embed-code" rows="6" cols="80">Paste Youtube video embed code here</textarea></div>
            <div><input type="hidden"></div>
            <div>Title<br /><textarea onfocus="this.value=''" name="title" rows="1" cols="80">Enter the title...</textarea></div>
            <div><input type="hidden"></div>
            <div>Article body<br /><textarea onfocus="this.value=''" name="content" rows="12" cols="80">Write or paste your article here...</textarea></div>
            <div><input type="submit" value="Post Article"></div>
          </form>
          <a href="/">home</a>
          """)

#move this into main page
    articles = db.GqlQuery("SELECT * "
                            "FROM Archive "
                            "WHERE ANCESTOR IS :1 "
                            "ORDER BY date DESC LIMIT 10",
                            articles_key())

    for article in articles:
      self.response.out.write(
        '<div>%s</div>' % article.embed)
      self.response.out.write(
        '<div>%s by %s</div>' % (article.title, article.author))
      self.response.out.write(
        '<div>%s</div>' % article.content)
    self.response.out.write('</body></html>')
    

class PostArticle(webapp2.RequestHandler):
  def post(self):
    # We set the same parent key on the 'Archive' to ensure each greeting is in
    # the same entity group. Queries across the single entity group will be
    # consistent. However, the write rate to a single entity group should
    # be limited to ~1/second.
    articles = Archive(parent=articles_key())

    if users.get_current_user():
      articles.author = users.get_current_user().nickname()

    articles.embed = self.request.get('embed-code')
    articles.title = self.request.get('title')
    articles.content = self.request.get('content')
    articles.put()
    self.redirect('/')

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/post-article-form', PostArticleForm),
                               ('/post-it', PostArticle)],
                                debug=True)
