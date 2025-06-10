import requests
import os
from dotenv import load_dotenv

load_dotenv()


def get_user_tweets_by_date_range(username, start_date, end_date, api_key):
    """
    指定ユーザーの指定期間のツイートを取得

    Args:
        username: Twitterユーザー名（@なし）
        start_date: 開始日時 (YYYY-MM-DD_HH:MM:SS)
        end_date: 終了日時 (YYYY-MM-DD_HH:MM:SS)
        api_key: TwitterAPI.ioのAPIキー
    """

    url = "https://api.twitterapi.io/twitter/tweet/advanced_search"
    headers = {"X-API-Key": api_key}

    # クエリ構築
    query = f"from:{username} since:{start_date}_UTC until:{end_date}_UTC"

    params = {
        "query": query,
        "type": "Latest",  # または "Top"
        "cursor": ""
    }

    all_tweets = []

    while True:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            tweets = data.get("tweets", [])
            all_tweets.extend(tweets)

            # 次のページがあるかチェック
            if data.get("has_next_page", False):
                params["cursor"] = data.get("next_cursor", "")
            else:
                break
        else:
            print(f"Error: {response.status_code}, {response.text}")
            break

    return all_tweets

def main():
    username = "elonmusk"
    start_date = "2025-06-01_00:00:00"
    end_date = "2025-06-10_23:59:59"

    tweets = get_user_tweets_by_date_range(username, start_date, end_date, os.getenv('X_API_KEY'))
    print(tweets)

if __name__ == "__main__":
    main()
