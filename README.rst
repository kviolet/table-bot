This is a Wikipedia sort-of-bot for maintaining a central store of language classification data for use in articles.

(NB: the page names used are currently in userspace/sandboxes while I shake down any kinks left in it.)

Operation
=========

0. Install the pywikibot framework (specifically, the core branch), unicodecsv and mwparserfromhell.

1. Create the operations database. The schema is in a comment in ``data-tables-update.py``.

2. a. If you're doing dry-runs, create a ``generated`` directory.
   b. If you're not doing dry-runs, change ``DRY_RUN`` to ``False`` in ``data-tables-update.py``.

3. ``python data-tables-update.py``.

4. Marvel!

Relevant pages and their purpose
================================

* ``User:KleptomaniacViolet/Language families data/`` *:subpage*: the canonical language family trees. Example page: [[User:KleptomaniacViolet/Language families data/Dravidian languages]]. These are a tree-based format using lists and templates to structure the data while staying human-friendly. All subpages will be gone over by the bot. Note that large trees can be broken across multiple pages, so long as the common node is an article and it's at the root of the 'child' tree and it's a leaf of the 'parent'. This is the only page which should normally be human-edited.

* ``User:KleptomaniacViolet/Language families cookies``: a control page to synchronise multiple instances of the script. While an instance is actively updating pages, it's replaced with the text 'LOCKED'. When it finishes, the body is replaced with CSV data detailing whether the 'alpha' or 'beta' set of generated Lua subpages for each canonical tree's subpage is live, which is then read by the next instance of the script. This is necessary to preserve atomicity: the bot updates the set which is not live and then switches over with one edit.

* ``Module:Sandbox/KleptomaniacViolet/Language families/Data/``*:subpage*``/`` *:cookie* ``/`` *:count*: the generated Lua tables of node data. Example page: [[Module:Sandbox/KleptomaniacViolet/Language families/Data/Dravidian languages/alpha/0]]. The bot will deconstruct the canonical trees into (parent node, child node) relations, but a naive implementation of this may exceed the 2MB page size limit. Therefore, they are split into chunks, indexed by the last element of the page name, the *count*. The *cookie* is 'alpha' or 'beta'. The unique part of the source subpage's title is preserved in the object subpages' titles so that changes have good locality and do not needlessly cause the entire multi-megabyte node table complex to be reuploaded every time a single input page changes.

* ``Module:Sandbox/KleptomaniacViolet/Language families/Data``: a list of which Lua data modules are currently live

Miscellaneous notes
===================

Most of the complexity in this code comes from running off-wiki (in particular, the need to maintain atomicity and the chunking). In principle it should be possible to do the heavy lifting of parsing the canonical trees in a Lua module (there aren't that many of them, and it should be fast if enough corners are cut), but writing Lua is much more of an unknown for me than Python, so I have stuck to what I know. If anyone wants to have a go, the main thing will be porting ``lua_table_generate.py`` to Lua itself. A separate list of subpages to go over will have to be maintained, but that has other advantages anyway.

Error recovery & troubleshooting
================================

If the script doesn't complete it's operation and unlock the cookie page, infoboxes will be unaffected because of the atomicity guarantee. In order: roll back the data page (if it's been written already this run, otherwise leave it) then the cookie page to the previous version and try again. (Doing it in the other order may lead to article infoboxes looking weird.)

If parsing the cookie page fails, chances are that someone has manually edited it and interfered with the bot's process. Revert that edit and try again. If the problem is that the script itself has generated a bad cookie page, either roll the data and the cookies page back to the previous checkpoint (as above, but this may lead to infobox weirdness if there has been a failed run since the last successful one), or blank/delete the cookie page (note that this may lead to temporary article infobox disruption during the next run).

For both the above cases, a way to guarantee that there'll be no weirdness in infoboxes is to systematically revert each page it's edited to a known good version (going in reverse order, again). Manually lock the cookie page while you do that by replacing its text with 'LOCKED' until you apply the final revert, which will be to the cookie page itself.

If changes to one of the trees isn't getting reflected in infoboxes, double-check that the script is parsing it fine, and purge the article and the infobox template.
