from html.parser import HTMLParser

class MDParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.output = []
        self.in_codeblock = False
        self.link_href = None
    def handle_starttag(self, tag, attrs):
        if tag.startswith('h') and len(tag)==2 and tag[1].isdigit():
            self.output.append('\n' + '#' * int(tag[1]) + ' ')
        elif tag == 'p':
            self.output.append('\n')
        elif tag == 'li':
            self.output.append('- ')
        elif tag == 'pre':
            self.in_codeblock = True
            self.output.append('\n```\n')
        elif tag == 'code':
            if not self.in_codeblock:
                self.output.append('`')
        elif tag == 'strong' or tag == 'b':
            self.output.append('**')
        elif tag == 'em' or tag == 'i':
            self.output.append('*')
        elif tag == 'br':
            self.output.append('  \n')
        elif tag == 'a':
            attrs = dict(attrs)
            self.output.append('[')
            self.link_href = attrs.get('href','')
        elif tag == 'img':
            attrs = dict(attrs)
            src = attrs.get('src','')
            alt = attrs.get('alt','')
            self.output.append(f'![{alt}]({src})')
    def handle_endtag(self, tag):
        if tag.startswith('h') and len(tag)==2 and tag[1].isdigit():
            self.output.append('\n')
        elif tag == 'p':
            self.output.append('\n')
        elif tag == 'li':
            self.output.append('\n')
        elif tag == 'pre':
            self.in_codeblock = False
            self.output.append('\n```\n')
        elif tag == 'code':
            if not self.in_codeblock:
                self.output.append('`')
        elif tag == 'strong' or tag == 'b':
            self.output.append('**')
        elif tag == 'em' or tag == 'i':
            self.output.append('*')
        elif tag == 'a':
            self.output.append(f']({self.link_href})')
            self.link_href = None
    def handle_data(self, data):
        self.output.append(data)
    def get_markdown(self):
        return ''.join(self.output)

if __name__ == '__main__':
    import sys
    with open(sys.argv[1], 'r') as f:
        html = f.read()
    parser = MDParser()
    parser.feed(html)
    md = parser.get_markdown()
    print(md)
