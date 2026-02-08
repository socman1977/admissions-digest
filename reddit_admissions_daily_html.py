# -*- coding: utf-8 -*-
import os
import re
import time
from datetime import datetime, timedelta, timezone

import feedparser
import requests
from dotenv import load_dotenv

load_dotenv()

# -------------------------
# CONFIG: Subreddits (RSS)
# -------------------------
SUBREDDIT_RSS = [
    "https://www.reddit.com/r/ApplyingToCollege/.rss",
    "https://www.reddit.com/r/collegeadmissions/.rss",
    "https://www.reddit.com/r/SAT/.rss",
    "https://www.reddit.com/r/Scholarships/.rss",
    "https://www.reddit.com/r/UTAdmissions/.rss",
    "https://www.reddit.com/r/UTAustin/.rss",
    "https://www.reddit.com/r/aggies/.rss",
    "https://www.reddit.com/r/TAMUAdmissions/.rss",
]

# -------------------------
# CONFIG: Keywords (Damon schools focus)
# -------------------------
KEYWORDS = [
    "mit", "massachusetts institute of technology",
    "princeton",
    "stanford",    "harvard",
    "stanford university",
    "brown",
    "dartmouth",
    "johns hopkins", "jhu",

    "rice",
    "upenn", "penn", "university of pennsylvania",
    "ut austin", "utexas", "cockrell", "caee", "ut admissions",
    "texas a&m", "tamu", "aggies", "etam",

    "decision", "release", "portal", "status", "deferred", "deferral",
    "waitlist", "wl", "likely letter",
    "interview", "alumni interview",
    "midyear", "mid-year", "mid year report",
    "css", "fafsa", "idoc", "financial aid", "scholarship",
    "supplement", "supplements", "why us", "essay", "personal statement",

    "civil engineering", "architectural engineering", "architecture engineering",
    "economics", "econ", "b.s. economics",
]

MAX_POSTS = 50
HOURS_LOOKBACK = 24

REPORT_FILE = "index.html"
TITLE = "College Admissions Reddit Daily Digest (Damon schools)"

def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())

def html_strip(s: str) -> str:
    return normalize(re.sub(r"<.*?>", "", s or ""))

def contains_keywords(text: str) -> bool:
    t = (text or "").lower()
    return any(k in t for k in KEYWORDS)

def fetch_rss_posts():
    cutoff = datetime.now(timezone.utc) - timedelta(hours=HOURS_LOOKBACK)
    posts = []
    headers = {"User-Agent": "admissions-digest/1.0 (RSS reader)"}

    for url in SUBREDDIT_RSS:
        try:
            resp = requests.get(url, headers=headers, timeout=20)
            resp.raise_for_status()
            feed = feedparser.parse(resp.text)
        except Exception:
            continue

        for e in getattr(feed, "entries", []):
            if not hasattr(e, "published_parsed"):
                continue
            published = datetime.fromtimestamp(time.mktime(e.published_parsed), tz=timezone.utc)
            if published < cutoff:
                continue

            title = normalize(getattr(e, "title", ""))
            link = getattr(e, "link", "")
            summary = html_strip(getattr(e, "summary", ""))[:1200]

            blob = f"{title}\n{summary}"
            if not contains_keywords(blob):
                continue

            posts.append({
                "published": published,
                "title": title,
                "link": link,
                "summary": summary,
            })

    posts.sort(key=lambda x: x["published"], reverse=True)
    return posts[:MAX_POSTS]

def classify_school(text: str) -> str:
    t = text.lower()
    if "mit" in t or "massachusetts institute of technology" in t:
        return "MIT"
    if "princeton" in t:
        return "Princeton"
    if "stanford" in t:
        return "Stanford"
    if "harvard" in t:
        return "Harvard"
    if "brown" in t:
        return "Brown"
    if "dartmouth" in t:
        return "Dartmouth"
    if "johns hopkins" in t or "jhu" in t:
        return "Johns Hopkins"
    if "rice" in t:
        return "Rice"
    if "upenn" in t or "penn" in t or "university of pennsylvania" in t:
        return "UPenn"
    if "ut austin" in t or "utexas" in t or "cockrell" in t or "ut admissions" in t:
        return "UT Austin"
    if "texas a&m" in t or "tamu" in t or "aggies" in t or "etam" in t:
        return "Texas A&M"
    return "General"

def classify_topic(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ["decision", "release", "portal", "status", "deferred", "waitlist", "likely"]):
        return "Decisions/Portal"
    if any(k in t for k in ["interview", "alumni"]):
        return "Interview"
    if any(k in t for k in ["fafsa", "css", "idoc", "financial aid", "scholarship"]):
        return "Financial Aid"
    if any(k in t for k in ["essay", "supplement", "why us", "personal statement"]):
        return "Essays/Supplements"
    if any(k in t for k in ["civil engineering", "architectural engineering", "economics", "econ"]):
        return "Majors"
    return "Other"

def build_html_section(posts):
    school_order = [
        "MIT", "Harvard", "Princeton", "Stanford",
        "Brown", "Dartmouth", "Johns Hopkins",
        "Rice", "UPenn", "UT Austin", "Texas A&M", "General"
    ]

    # Bucket by school then topic
    buckets = {}
    for p in posts:
        text = f"{p['title']} {p['summary']}"
        school = classify_school(text)
        topic = classify_topic(text)
        buckets.setdefault(school, {}).setdefault(topic, []).append(p)

    today = datetime.now().strftime("%Y-%m-%d")
    now_local = datetime.now().strftime("%Y-%m-%d %H:%M")

    def esc(s: str) -> str:
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    parts = []
    parts.append(f"<section class='day'>")
    parts.append(f"<h2>{today} <span class='meta'>(generated {now_local})</span></h2>")
    parts.append(f"<p class='meta'>Lookback: last {HOURS_LOOKBACK} hours · Posts matched: {len(posts)} (max {MAX_POSTS})</p>")

    if not posts:
        parts.append("<p>No matching posts in the last 24 hours.</p>")
        parts.append("</section>")
        return "\n".join(parts)

    # Quick highlights (top 5)
    parts.append("<h3>Today’s quick highlights (Top 5)</h3><ol>")
    for p in posts[:5]:
        parts.append(f"<li><a href='{esc(p['link'])}' target='_blank' rel='noopener'>{esc(p['title'])}</a></li>")
    parts.append("</ol>")

    # Detailed buckets
    topic_order = ["Decisions/Portal", "Interview", "Financial Aid", "Essays/Supplements", "Majors", "Other"]

    for school in school_order:
        if school not in buckets:
            continue
        parts.append(f"<h3>{school}</h3>")
        for topic in topic_order:
            items = buckets[school].get(topic, [])
            if not items:
                continue
            parts.append(f"<h4>{topic} <span class='count'>({len(items)})</span></h4>")
            parts.append("<ul>")
            for p in items[:12]:
                dt = p["published"].astimezone().strftime("%m/%d %H:%M")
                parts.append(
                    f"<li>"
                    f"<a href='{esc(p['link'])}' target='_blank' rel='noopener'>{esc(p['title'])}</a>"
                    f"<span class='meta'> · {dt}</span>"
                    f"<div class='snippet'>{esc(p['summary'][:280])}</div>"
                    f"</li>"
                )
            parts.append("</ul>")

    # Action checklist
    parts.append("<h3>Action checklist (parents & student)</h3>")
    parts.append("<ul>")
    parts.append("<li>Check applicant portals & email (including Spam/Promotions) for each school.</li>")
    parts.append("<li>If interviews are scheduled: prepare 2–3 stories + 60-sec “Why major/Why school” and send thank-you after.</li>")
    parts.append("<li>Verify FAFSA/CSS/IDOC completeness; fix missing documents.</li>")
    parts.append("<li>If you have a meaningful update (rank/award/project): draft a short 150–200 word update (only where allowed).</li>")
    parts.append("<li>Treat Reddit timing/rumors as anecdotal; cross-check with official school communications.</li>")
    parts.append("</ul>")

    parts.append("</section>")
    return "\n".join(parts)

def load_or_init_report():
    if os.path.exists(REPORT_FILE):
        with open(REPORT_FILE, "r", encoding="utf-8") as f:
            return f.read()

    # Initial HTML skeleton
    skeleton = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>{TITLE}</title>
<style>
  body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, Arial, sans-serif; margin: 24px; line-height: 1.4; }}
  header {{ margin-bottom: 18px; }}
  .meta {{ color: #666; font-size: 0.9em; }}
  .day {{ border-top: 1px solid #ddd; padding-top: 16px; margin-top: 18px; }}
  h1 {{ margin: 0; }}
  h2 {{ margin: 0 0 8px 0; }}
  h3 {{ margin-top: 16px; }}
  h4 {{ margin: 10px 0 6px 0; }}
  ul {{ margin-top: 6px; }}
  li {{ margin-bottom: 10px; }}
  .snippet {{ margin-top: 4px; color: #333; font-size: 0.95em; }}
  .count {{ color: #666; font-weight: normal; }}
  a {{ text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<header>
  <h1>{TITLE}</h1>
  <p class="meta">Auto-generated daily from Reddit RSS feeds. Focus: MIT/Princeton/Stanford/Rice/UPenn/UT Austin/Texas A&amp;M.</p>
</header>

<main id="content">
</main>

</body>
</html>
"""
    return skeleton

def insert_today_section(html, today_section):
    # Insert new section at top of <main id="content">
    marker = '<main id="content">'
    idx = html.find(marker)
    if idx == -1:
        return html + "\n" + today_section

    insert_pos = idx + len(marker)
    return html[:insert_pos] + "\n" + today_section + "\n" + html[insert_pos:]

def main():
    posts = fetch_rss_posts()
    today_section = build_html_section(posts)

    html = load_or_init_report()

    # Prevent duplicate same-day insertion: if today's heading exists, replace it.
    today = datetime.now().strftime("%Y-%m-%d")
    pattern = re.compile(rf"<section class='day'>.*?<h2>{re.escape(today)}.*?</section>", re.DOTALL)
    if pattern.search(html):
        html = pattern.sub(today_section, html)
    else:
        html = insert_today_section(html, today_section)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"OK - updated {REPORT_FILE} with {len(posts)} posts.")

if __name__ == "__main__":
    main()

