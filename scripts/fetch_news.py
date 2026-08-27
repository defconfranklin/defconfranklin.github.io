#!/usr/bin/env python3
# TKT-245: adapted from jas-authcheck.py's _fetch_press_articles() (the same
# feed that runs on jas.waterwatchcenter.org's landing page). This site is a
# pure static GitHub Pages site with no server-side component, so instead of
# fetching the RSS feed per-request, a scheduled GitHub Actions workflow runs
# this script periodically and commits its JSON output (news.json) back to
# the repo -- the page then does a plain same-origin fetch() of that file at
# load time, with zero runtime dependency on Google News being reachable.
#
# Deliberately stdlib-only (urllib, xml.etree.ElementTree, email.utils) so
# the Actions workflow needs no pip install step.
import email.utils
import json
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

PRESS_QUERY = (
    '(water utility OR water system OR wastewater OR "drinking water") '
    '(cyberattack OR ransomware OR breach OR hack OR "cyber attack")'
)


def fetch_articles():
    url = "https://news.google.com/rss/search?q={}&hl=en-US&gl=US&ceid=US:en".format(
        urllib.parse.quote(PRESS_QUERY)
    )
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; defconfranklin-news/1.0)"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = resp.read()
    root = ET.fromstring(data)
    articles = []
    for item in root.iter("item"):
        title_el = item.find("title")
        link_el = item.find("link")
        pubdate_el = item.find("pubDate")
        if title_el is None or link_el is None or pubdate_el is None:
            continue
        try:
            pub_ts = email.utils.parsedate_to_datetime(pubdate_el.text).timestamp()
        except Exception:
            continue
        title = (title_el.text or "").strip()
        source_el = item.find("source")
        source = (source_el.text or "").strip() if source_el is not None else ""
        if source and title.endswith(" - " + source):
            title = title[: -(len(source) + 3)]
        if " - " in source:
            source = source.split(" - ", 1)[0]
        elif not source and " - " in title:
            title, source = title.rsplit(" - ", 1)
        articles.append({
            "title": title.strip(),
            "source": source.strip(),
            "link": (link_el.text or "").strip(),
            "pub_ts": pub_ts,
        })
    articles.sort(key=lambda a: a["pub_ts"], reverse=True)
    return articles[:8]


def main():
    try:
        articles = fetch_articles()
    except Exception as e:
        print("fetch failed: {}".format(e), file=sys.stderr)
        sys.exit(1)
    if not articles:
        print("fetch returned zero articles -- treating as a failure, not overwriting news.json", file=sys.stderr)
        sys.exit(1)
    out = {"generated_at": time.time(), "articles": articles}
    with open("news.json", "w") as f:
        json.dump(out, f, indent=2)
    print("wrote {} articles to news.json".format(len(articles)))


if __name__ == "__main__":
    main()
