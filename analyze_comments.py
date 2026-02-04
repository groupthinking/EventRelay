import json
from collections import Counter
import re


def analyze_comments(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        comments = json.load(f)

    total = len(comments)
    top_liked = sorted(comments, key=lambda x: x["like_count"], reverse=True)[:10]

    # Simple keyword clusters
    themes = {
        "Ask Button Missing/Confusion": [
            "ask button",
            "where",
            "how to turn on",
            "not seeing",
            "can't see",
            "missing",
        ],
        "Feature Requests": [
            "folders",
            "subscription",
            "playlist",
            "search bar",
            "update",
        ],
        "YouTube Music": ["music app", "yt music", "youtube music"],
        "Positive Feedback": ["cool", "great", "sick", "love", "good"],
        "Negative/Sarcastic": ["fail", "ridiculous", "lmao", "😂", "bruh"],
    }

    theme_counts = Counter()
    for c in comments:
        text = c["text"].lower()
        for theme, keywords in themes.items():
            if any(k in text for k in keywords):
                theme_counts[theme] += 1

    return {
        "total_comments": total,
        "top_liked": top_liked,
        "theme_counts": dict(theme_counts),
        "avg_likes": sum(c["like_count"] for c in comments) / total if total > 0 else 0,
    }


if __name__ == "__main__":
    results = analyze_comments("comments_WPHtKet27ic.json")
    print(json.dumps(results, indent=2))
