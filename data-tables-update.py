import pywikibot
import sqlite3
import unicodecsv as csv
from cStringIO import StringIO
from lua_table_generate import parse, gen_lua_iter, gen_lua_wrapping, lua_string

#Schema:
#  CREATE TABLE last_attempted (title STRING PRIMARY KEY, revid INTEGER NOT NULL);
conn = sqlite3.connect("pages.db")

PREFIX = "KleptomaniacViolet/Language families data/"
PREFIX_NS = 2
COOKIE_PAGE = "KleptomaniacViolet/Language families cookies"
COOKIE_NS = 2
DATA_PREFIX = "Sandbox/KleptomaniacViolet/Language families/Data"
DATA_PREFIX_NS = 828
DRY_RUN = True
USERNAME = None

site = pywikibot.Site("en", "wikipedia", user = USERNAME)

#Convention for dry running: slashes in the page title are replaced with %, % is replaced by %%.
def dry_run_file(title):
    return title.replace("%", "%%").replace("/", "%")

table_list_page = pywikibot.Page(site, DATA_PREFIX, ns = DATA_PREFIX_NS)

old_cookies = {}
cookie_page = pywikibot.Page(site, COOKIE_PAGE, ns = COOKIE_NS)
try:
    cookie_data = cookie_page.get()
except pywikibot.NoPage:
    pass
else:
    if cookie_data == "LOCKED":
        raise ValueError("Some other instance is mid-update.")
    try:
        old_cookies = dict((t, (cookie, int(count), int(revid))) for t, cookie, count, revid in csv.reader(cookie_data.encode("utf-8").split("\n"), encoding="utf-8"))
    except:
        if cookie_data and not cookie_data.isspace():
            print "Uh-oh, can't parse the cookie page. Did someone manually edit it? Consider reverting."
            raise
    if not DRY_RUN:
        cookie_page.text = "LOCKED"
        cookie_page.save(comment = "SCRIPT data-tables-update: Claiming the lock.")

def remove_prefix(s):
    return s[len(PREFIX):]

all_stripped_titles = {}
hierarchies = []
for page in site.allpages(prefix = PREFIX,
                          namespace = PREFIX_NS,
                          content = True):
    contents = page.get()
    stripped_title = remove_prefix(page.title(withNamespace = False))
    revid = page.latestRevision()
    if stripped_title not in old_cookies:
        new_cookie = "alpha"
    else:
        if old_cookies[stripped_title][0] == "alpha":
            new_cookie = "beta"
        else:
            new_cookie = "alpha"
        if int(old_cookies[stripped_title][2]) == revid:
            continue
    if not DRY_RUN:
        conn.execute("INSERT OR REPLACE INTO last_attempted (title, revid) VALUES (?, ?)", (stripped_title, revid))
        conn.commit()
    try:
        hs = parse(contents.split("\n"))
    except ValueError as e:
        print "Parsing", page.title(), "failed:", e.message
        print "Trying to go with the last revision someone successfully got..."
        if stripped_title not in old_cookies:
            print "No previous good revision. Skipping it entirely from consideration."
        else:
            all_stripped_titles[stripped_title] = old_cookies[stripped_title]
        continue
    hierarchies.append((stripped_title, revid, contents, new_cookie, hs))

def chunk(i):
    buf = u""
    for v in i:
        if len(v.encode("utf-8")) + len(buf.encode("utf-8")) > 1000000 and buf:
            yield buf
            buf = ""
        buf += v
    if buf:
        yield buf

for stripped_title, revid, contents, new_cookie, hs in hierarchies:
    for n, lua in enumerate(map(gen_lua_wrapping, chunk(gen_lua_iter(hs)))):
        title = "%s/%s/%s/%d" % (DATA_PREFIX, stripped_title, new_cookie, n)
        if not DRY_RUN:
            page = pywikibot.Page(site, title, ns = DATA_PREFIX_NS)
            page.text = lua
            page.save(comment = "SCRIPT data-tables-update: Updating language family tables")
        else:
            with open("generated/%s" % dry_run_file(title), "w") as f:
                f.write(lua.encode("utf-8"))
    all_stripped_titles[stripped_title] = (new_cookie, n, revid)

pages = []
for stripped_title in all_stripped_titles:
    (new_cookie, count, revid) = all_stripped_titles[stripped_title]
    for n in range(0, count + 1):
        pagetitle = "Module:%s/%s/%s/%d" % (DATA_PREFIX, stripped_title, new_cookie, count)
        pages.append(lua_string(pagetitle))

text = 'return { %s }' % ", ".join(pages)
if not DRY_RUN:
    table_list_page.text = text
    table_list_page.save(comment = "SCRIPT data-tables-update: Switching to the updated tables")
else:
    with open("generated/%s" % dry_run_file(table_list_page.title(withNamespace = False)), "w") as f:
        f.write(text.encode("utf-8"))

f = StringIO()
w = csv.writer(f, encoding = "utf-8")
for stripped_title, (new_cookie, count, revid) in all_stripped_titles.items():
    w.writerow((stripped_title, new_cookie, str(count), str(revid)))
text = f.getvalue().decode("utf-8")

if not DRY_RUN:    
    cookie_page.text = text
    cookie_page.save(comment = "SCRIPT data-tables-update: Updating and unlocking the cookie list")
else:
    with open("generated/%s" % dry_run_file(cookie_page.title(withNamespace = False)), "w") as f:
        f.write(text.encode("utf-8"))
