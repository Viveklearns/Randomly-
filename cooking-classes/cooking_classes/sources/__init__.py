from . import instagram, manual, pages, reddit, web_search

SOURCES = {
    "web_search": web_search.collect,
    "reddit": reddit.collect,
    "instagram": instagram.collect,
    "pages": pages.collect,
    "manual": manual.collect,
}
