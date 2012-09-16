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
from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app

class MainPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        if user:
            self.response.headers['Content-Type'] = 'text/plain'
            self.response.out.write('Hello, ' + user.nickname())
        else:
            self.redirect(users.create_login_url(self.request.uri))



        template_values = {
        'random': randint(0, 1),
        }
        path = os.path.join(os.path.dirname(__file__), 'index.html' )
        self.response.out.write(template.render(path, template_values))

class Brian(webapp2.RequestHandler):
    def get(self):
        template_values = {
        }
        url = "https://drive.google.com/uc?export=download&id=0By67lez8igcDd3dUZEhncEo1ODg"
        result = urlfetch.fetch(url)
        if result.status_code == 200:
          path = result.content
          self.response.out.write(template.render(path, template_values))

app = webapp2.WSGIApplication([('/', MainPage),
                               ('/brian', Brian)],
                      debug=True)
