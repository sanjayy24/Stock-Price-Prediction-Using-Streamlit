# backend/news_sentiment.py
import feedparser
from urllib.parse import quote_plus
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

def fetch_google_news_rss(query: str, limit: int = 10):
    q = quote_plus(query)
    url = f"https://news.google.com/rss/search?q={q}"
    feed = feedparser.parse(url)

    items = []
    for e in (feed.entries or [])[:limit]:
        items.append({
            "title": getattr(e, "title", ""),
            "link": getattr(e, "link", ""),
            "published": getattr(e, "published", ""),
        })
    return items


def sentiment_from_headlines(items):
    """
    Returns: label, avg_compound, per_item_scores, counts
    label is based on MAJORITY VOTE (better than avg-only)
    """
    if not items:
        return "Neutral", 0.0, [], {"positive": 0, "negative": 0, "neutral": 0}

    pos = neg = neu = 0
    scores = []
    per_item = []

    for it in items:
        raw_title = (it.get("title") or "").strip()

        # ✅ Clean source suffix: ".... - Times of India"
        title = raw_title.split(" - ")[0].strip()

        comp = _analyzer.polarity_scores(title)["compound"]
        scores.append(comp)

        if comp > 0.05:
            pos += 1
        elif comp < -0.05:
            neg += 1
        else:
            neu += 1

        per_item.append({
            "title": title,
            "link": it.get("link", ""),
            "published": it.get("published", ""),
            "compound": comp
        })

    avg = sum(scores) / len(scores)

    # ✅ Majority vote label
    if pos > neg and pos >= neu:
        label = "Positive"
    elif neg > pos and neg >= neu:
        label = "Negative"
    else:
        label = "Neutral"

    return label, avg, per_item, {"positive": pos, "negative": neg, "neutral": neu}
