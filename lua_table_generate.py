import mwparserfromhell
import sys
import re

def lua_string(s):
    return u"'" + s.replace(u"\\", u"\\\\").replace(u"'", u"\\'") + "'"

LIST_REGEX = re.compile("^(\:*\*?|)\s*")

TEMPLATE = "User:KleptomaniacViolet/language node"

def parse_list_entry(line, i):
    m = LIST_REGEX.match(line)
    if m is None:
        raise ValueError("Line %d: Can't parse as a list entry" % i)
    rawtext = line[m.end():]
    depth = len(m.group(1))
    return depth, rawtext

def parse_node_template(rawtext, parent_title, i):
    code = mwparserfromhell.parse(rawtext)
    if len(code.filter_templates(recursive = False)) != 1:
        raise ValueError("Too many templates on line %d" % i)
    template = code.filter_templates(recursive = False)[0]
    code.remove(template)
    if code and not code.isspace():
        raise ValueError("Non-template stuff on line %d" % i)
    if template.name.lstrip().rstrip() != TEMPLATE:
        raise ValueError("Wrong template on line %d" % i)
    if not template.has('display'):
        raise ValueError("Need the display param on line %d" % i)
    display = template.get("display").value.strip().lstrip()
    if display.startswith("<nowiki>") and display.endswith("</nowiki>"):
        display = display[len("<nowiki>"):-len("</nowiki>")]
    link = None
    if template.has("link"):
        link = template.get("link").value.strip().lstrip()
    return Node(display, link, parent_title)

class Node(object):

    def __init__(self, display, link, parent_title):
        self.display = display
        self.link = link
        self.parent_title = parent_title
        if link is not None:
            self.title = self.link
        elif parent_title is not None:
            self.title = parent_title + u"/" + display
        else:
            self.title = u"/" + display
        self.children_titles = []

    def dump_lua(self):
        res = ""
        res += u"  [%s] = {\n" % lua_string(self.title)
        res += u"    display = %s,\n" % lua_string(self.display)
        if self.link is not None:
            res += u"    link = %s,\n" % lua_string(self.link)
        if self.parent_title is not None:
            res += u"    parent = %s,\n" % lua_string(self.parent_title)
        res += u"    children = {%s},\n" % ", ".join(map(lua_string, self.children_titles))
        res += u"  },\n"
        
        return res

def parse(lines):
    hierarchies = []
    cur = []
    for i, line in enumerate(lines):
        if not line or line.isspace():
            continue
        depth, node_text = parse_list_entry(line, i)
        if depth > len(cur):
            raise ValueError("Line %d has depth %d but cur has depth %d" % (i, depth, len(cur)))
        if depth < len(cur):
            hierarchies.append(cur)
            cur = cur[:depth]
        if not cur:
            parent_title = None
        else:
            parent_title = cur[-1].title
        node = parse_node_template(node_text, parent_title, i)
        if cur:
            cur[-1].children_titles.append(node.title)
        cur.append(node)
    hierarchies.append(cur)
    return hierarchies

def gen_lua_wrapping(lua):
    res = u""
    res += u"local language_nodes = {\n"
    res += lua
    res += u"""}
return { language_nodes = language_nodes }
"""
    return res

def gen_lua(hierarchies):
    return gen_lua_wrapping("".join(gen_lua_iter(hierarchies)))

def gen_lua_iter(hierarchies):
    for hierarchy in hierarchies:
        for node in hierarchy:
            yield node.dump_lua()

if __name__ == "__main__":
    print gen_lua(parse(sys.stdin)).encode("utf-8")
