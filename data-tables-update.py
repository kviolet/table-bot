import pywikibot
from lua_table_generate import parse, gen_lua_iter, gen_lua_wrapping

site = pywikibot.Site("en", "wikipedia")

hierarchies = []
for page in site.allpages(prefix = "KleptomaniacViolet/Language families data/",
                          namespace = 2,
                          content = True):
    contents = page.get()
    try:
        hs = parse(contents.split("\n"))
    except ValueError as e:
        print "Parsing", page.title(), "failed:", e.message
        continue
    hierarchies.extend(hs)

def chunk(i):
    buf = u""
    for v in i:
        if len(v) + len(buf) > 100000 and buf:
            yield buf
        buf += v
    if buf:
        yield buf

DATA_PREFIX = "Sandbox/KleptomaniacViolet/Language families/Data/"
COOKIE_REGEX = re.compile("^return \{ cookie = \"(\w+)\", max_page = \d+ \}$")

cookie_page = pywikibot.Page(site, DATA_PREFIX + "Cookie", namespace = 828)

match = COOKIE_REGEX.search(cookie_page.get())
if match is None:
    raise ValueError("Can't parse the cookie page.")
cookie = match.group(1)
if cookie == "alpha":
    new_cookie = "beta"
else:
    new_cookie = "alpha"

for n, lua in enumerate(map(gen_lua_wrapping, chunk(gen_lua_iter(hierarchies)))):
    page = pywikibot.Page(site, "%s/%s/%d" % (DATA_PREFIX, new_cookie, n), namespace = 828)
    page.text = lua
    page.save(comment = "Updating language family tables")

cookie_page.text = 'return { cookie = "%s", max_page = %d }' % (new_cookie, n)
cookie_page.save(comment = "Switching to the updated tables")
