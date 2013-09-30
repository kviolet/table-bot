import pywikibot
import sqlite3
from lua_table_generate import parse, gen_lua_iter, gen_lua_wrapping, lua_string

site = pywikibot.Site("en", "wikipedia")

#Schema:
#  CREATE TABLE last_good (title STRING PRIMARY KEY, revid INTEGER NOT NULL, contents STRING NOT NULL, cookie STRING NOT NULL, lua_page_count INTEGER NOT NULL);
conn = sqlite3.connect("pages.db")

PREFIX = "KleptomaniacViolet/Language families data/"
DATA_PREFIX = "Sandbox/KleptomaniacViolet/Language families/Data/"
DRY_RUN = True

#Convention for dry running: slashes in the page title are replaced with %, % is replaced by %%.
def dry_run_file(title):
    return title.replace("%", "%%").replace("/", "%")

cookie_page = pywikibot.Page(site, DATA_PREFIX + "Cookie", ns = 828)

def remove_prefix(s):
    return s[len(PREFIX):]

all_stripped_titles = set()
hierarchies = []
for page in site.allpages(prefix = PREFIX,
                          namespace = 2,
                          content = True):
    contents = page.get()
    title = page.title(withNamespace = False)
    all_stripped_titles.add(remove_prefix(title))
    revid = page.latestRevision()
    res = conn.execute("SELECT revid, cookie, lua_page_count FROM last_good WHERE title = ?", (title,)).fetchone()
    if res is None:
        new_cookie = "alpha"
    else:
        cookie = res[1]
        if cookie == "alpha":
            new_cookie = "beta"
        else:
            new_cookie = "alpha"
        if int(res[0]) == revid:
            continue
    try:
        hs = parse(contents.split("\n"))
    except ValueError as e:
        print "Parsing", page.title(), "failed:", e.message
        print "Trying to go with the last revision we successfully got..."
        res = conn.execute("SELECT contents FROM last_good WHERE title = ?", (title,)).fetchone()
        if res is None:
            print "No previous good revision. Skipping."
            continue
        (contents,) = res
        hs = parse(contents.split("\n"))
    hierarchies.append((remove_prefix(title), revid, contents, new_cookie, hs))

def chunk(i):
    buf = u""
    for v in i:
        if len(v) + len(buf) > 100000 and buf:
            yield buf
        buf += v
    if buf:
        yield buf

for stripped_title, revid, contents, new_cookie, hs in hierarchies:
    for n, lua in enumerate(map(gen_lua_wrapping, chunk(gen_lua_iter(hs)))):
        title = "%s%s/%s/%d" % (DATA_PREFIX, stripped_title, new_cookie, n)
        if not DRY_RUN:
            page = pywikibot.Page(site, title, ns = 828)
            page.text = lua
            page.save(comment = "Updating language family tables")
        else:
            with open("generated/%s" % dry_run_file(title), "w") as f:
                f.write(lua.encode("utf-8"))
    conn.execute("INSERT OR IGNORE INTO last_good (title, revid, contents, cookie, lua_page_count) VALUES (?, ?, ?, ?, ?)", (stripped_title, revid, contents, new_cookie, n))
    conn.commit()

cookies = []
for title in all_stripped_titles:
    res = conn.execute("SELECT cookie, lua_page_count FROM last_good WHERE title = ?", (title,)).fetchone()
    if res is None:
        continue
    pagetitle = "Module:%s%s/%s/" % (DATA_PREFIX, stripped_title, new_cookie)
    cookies.append('{ title = %s, cookie = "%s", max_page = %d }' % (lua_string(pagetitle), res[0], int(res[1])))

if not DRY_RUN:
    cookie_page.text = 'return { %s }' % ", ".join(cookies)
    cookie_page.save(comment = "Switching to the updated tables")
else:
    with open("generated/%s" % dry_run_file(cookie_page.title(withNamespace = False)), "w") as f:
        f.write(('return { %s }' % ", ".join(cookies)).encode("utf-8"))
