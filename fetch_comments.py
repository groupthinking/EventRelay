import asyncio
import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()


async def fetch_all_comments(video_id: str, api_key: str):
    base_url = "https://www.googleapis.com/youtube/v3/commentThreads"
    params = {
        "part": "snippet",
        "videoId": video_id,
        "key": api_key,
        "maxResults": 100,
        "order": "relevance",
    }

    comments = []
    next_page_token = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            if next_page_token:
                params["pageToken"] = next_page_token

            print(f"Fetching page... Current count: {len(comments)}")
            response = await client.get(base_url, params=params)

            if response.status_code != 200:
                print(f"Error: {response.status_code} - {response.text}")
                break

            data = response.json()
            items = data.get("items", [])

            for item in items:
                # Top level comment
                top_snippet = (
                    item["snippet"]["top_level_comment"]["snippet"]
                    if "top_level_comment" in item["snippet"]
                    else item["snippet"]["topLevelComment"]["snippet"]
                )
                comments.append(
                    {
                        "author": top_snippet["authorDisplayName"],
                        "text": top_snippet["textDisplay"],
                        "like_count": top_snippet["likeCount"],
                        "published_at": top_snippet["publishedAt"],
                        "type": "top_level",
                    }
                )

                # Fetch replies if they exist
                total_reply_count = item["snippet"].get("totalReplyCount", 0)
                if total_reply_count > 0:
                    # If there are only a few replies, they might be in the thread already
                    if "replies" in item:
                        for reply in item["replies"]["comments"]:
                            reply_snippet = reply["snippet"]
                            comments.append(
                                {
                                    "author": reply_snippet["authorDisplayName"],
                                    "text": reply_snippet["textDisplay"],
                                    "like_count": reply_snippet["likeCount"],
                                    "published_at": reply_snippet["publishedAt"],
                                    "type": "reply",
                                }
                            )
                    # If more replies exist than returned in the thread, we might need another call
                    # (But for relevance-ordered threads with default settings, we get some replies)
                    # For a one-off analysis, we'll take what's in the 'replies' field if present.
                    # To be truly thorough for 1.8k, we should call comments.list(parentId=item['id'])
                    # Let's add that logic.
                    elif (
                        total_reply_count > 0
                    ):  # This condition is redundant but kept as per instruction
                        reply_params = {
                            "part": "snippet",
                            "parentId": item["id"],
                            "key": api_key,
                            "maxResults": 100,
                        }
                        reply_response = await client.get(
                            "https://www.googleapis.com/youtube/v3/comments",
                            params=reply_params,
                        )
                        if reply_response.status_code == 200:
                            reply_data = reply_response.json()
                            for reply_item in reply_data.get("items", []):
                                reply_snippet = reply_item["snippet"]
                                comments.append(
                                    {
                                        "author": reply_snippet["authorDisplayName"],
                                        "text": reply_snippet["textDisplay"],
                                        "like_count": reply_snippet["likeCount"],
                                        "published_at": reply_snippet["publishedAt"],
                                        "type": "reply",
                                    }
                                )

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

    return comments


async def main():
    video_id = "WPHtKet27ic"
    api_key = os.getenv("YOUTUBE_API_KEY")

    if not api_key:
        print("Error: YOUTUBE_API_KEY not found in .env")
        return

    print(f"Starting fetch for video: {video_id}")
    comments = await fetch_all_comments(video_id, api_key)

    output_file = f"comments_{video_id}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(comments, f, indent=2, ensure_ascii=False)

    print(f"Successfully fetched {len(comments)} comments.")
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    asyncio.run(main())
