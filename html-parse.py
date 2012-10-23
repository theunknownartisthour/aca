

tree = html.parse('About-the-Art-Crime-Archive.html')
text =''.join([etree.tostring(child) for child in tree.xpath('body')[0].iterdescendants()])})
