#!/usr/bin/env python

# THIS ONLY WORKS WITH MARKDOWN 2.1.0

import markdown
try:
    # Markdown 2.1.0 changed from 2.0.3. We try importing the new version first,
    # but import the 2.0.3 version if it fails
    from markdown.util import etree
except:
    from markdown import etree


class WikiPathExtension(markdown.Extension):
    def __init__(self, configs):
        # set extension defaults
        self.config = {
                        'base_url' : ['/', 'String to append to beginning or URL.'],
                        'end_url' : ['/', 'String to append to end of URL.'],
                        'html_class' : ['wikipath', 'CSS hook. Leave blank for none.']
        }
        
        # Override defaults with user settings
        for key, value in configs :
            # self.config[key][0] = value
            self.setConfig(key, value)
                
                
    def extendMarkdown(self, md, md_globals):
        self.md = md
        
        # append to end of inline patterns
        WIKI_RE =  r'\[(?P<linkTitle>.+?)\]\(wiki:(?P<wikiTitle>[a-zA-Z\d/_-]*)\)'
        wikiPathPattern = WikiPath(WIKI_RE, self.getConfigs())
        wikiPathPattern.md = md
        md.inlinePatterns.add('wikipath', wikiPathPattern, "<reference")

class WikiPath(markdown.inlinepatterns.Pattern):
    def __init__(self, pattern, config):
        markdown.inlinepatterns.Pattern.__init__(self, pattern)
        self.config = config
    
    def handleMatch(self, m) :
        article_title = m.group('wikiTitle')
        if article_title.startswith("/"):
            article_title = article_title[1:]
        
        url = self.config['base_url'] + article_title
        label = m.group('linkTitle')
        a = etree.Element('a')
        a.set('href', url)
        a.text = label
        
        if self.config['html_class']:
            a.set('class', self.config['html_class'])
            
        return a
        
    def _getMeta(self):
        """ Return meta data or config data. """
        base_url = self.config['base_url']
        end_url = self.config['end_url']
        html_class = self.config['html_class']
        if hasattr(self.md, 'Meta'):
            if self.md.Meta.has_key('wiki_base_url'):
                base_url = self.md.Meta['wiki_base_url'][0]
            if self.md.Meta.has_key('wiki_end_url'):
                end_url = self.md.Meta['wiki_end_url'][0]
            if self.md.Meta.has_key('wiki_html_class'):
                html_class = self.md.Meta['wiki_html_class'][0]
        return base_url, end_url, html_class

def makeExtension(configs=None) :
    return WikiPathExtension(configs=configs)

if __name__ == "__main__":
    import doctest
    doctest.testmod()
