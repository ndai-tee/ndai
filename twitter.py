import requests
from datetime import datetime, timedelta
import json
import os
from dotenv import load_dotenv
import time

def get_tweets_for_date_range(coin_name: str, start_date: datetime, end_date: datetime, api_key: str) -> list:
    url = "https://twitter-api45.p.rapidapi.com/search.php"
    
    query = f"{coin_name} until:{end_date.strftime('%Y-%m-%d')} since:{start_date.strftime('%Y-%m-%d')}"
    
    querystring = {"query":query,"search_type":"Top"}
    
    headers = {
        "x-rapidapi-key": "b82ca58dfbmsh11a9804d841eab1p139a4ejsnf106db66e95e",
        "x-rapidapi-host": "twitter-api45.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        response.raise_for_status()
        
        data = response.json()
        
        processed_tweets = []
        
        if data.get('status') == 'ok' and 'timeline' in data:
            for tweet in data['timeline']:
                if tweet.get('type') == 'tweet':
                    user_info = tweet.get('user_info', {})
                    processed_tweet = {
                        'text': tweet.get('text', ''),
                        'created_at': tweet.get('created_at', ''),
                        'user': {
                            'name': user_info.get('name', 'Unknown'),
                            'username': user_info.get('screen_name', 'unknown'),
                            'followers': user_info.get('followers_count', 0),
                            'verified': user_info.get('verified', False),
                            'is_blue_verified': False
                        },
                        'engagement': {
                            'retweets': int(tweet.get('retweets', 0)),
                            'likes': int(tweet.get('favorites', 0)),
                            'replies': int(tweet.get('replies', 0)),
                            'views': int(tweet.get('views', '0').replace(',', '')),
                            'quotes': int(tweet.get('quotes', 0)),
                            'bookmarks': int(tweet.get('bookmarks', 0))
                        },
                        'media': tweet.get('media', {}),
                        'tweet_id': tweet.get('tweet_id', ''),
                        'conversation_id': tweet.get('conversation_id', ''),
                        'lang': tweet.get('lang', '')
                    }
                    
                    entities = tweet.get('entities', {})
                    if entities.get('media'):
                        for media in entities['media']:
                            if media.get('additional_media_info', {}).get('source_user', {}).get('user_results', {}).get('result', {}).get('is_blue_verified'):
                                processed_tweet['user']['is_blue_verified'] = True
                                break
                    
                    processed_tweets.append(processed_tweet)
        
        return processed_tweets
    except Exception as e:
        return []

def get_verified_tweets(coin_name: str, days_back: int = 60, api_key: str = None) -> list:
    if not api_key:
        return []
    
    processed_tweets = []
    end_date = datetime.now()
    
    for day in range(days_back):
        current_end = end_date - timedelta(days=day)
        current_start = current_end - timedelta(days=1)
        
        try:
            daily_tweets = get_tweets_for_date_range(coin_name, current_start, current_end, api_key)
            
            verified_tweets = [
                tweet for tweet in daily_tweets
                if tweet['user']['is_blue_verified']
            ]
            
            for tweet in verified_tweets:
                try:
                    tweet_date = datetime.strptime(tweet['created_at'], '%a %b %d %H:%M:%S +0000 %Y')
                except ValueError:
                    try:
                        tweet_date = datetime.strptime(tweet['created_at'], '%Y-%m-%dT%H:%M:%S.%fZ')
                    except ValueError:
                        tweet_date = current_start
                
                tweet['date'] = tweet_date.strftime('%Y-%m-%d')
                processed_tweets.append(tweet)
            
        except Exception as e:
            continue
        
        time.sleep(2)
    
    processed_tweets.sort(
        key=lambda x: x['engagement']['retweets'] + x['engagement']['likes'] + x['engagement']['views'],
        reverse=True
    )
    
    return processed_tweets

def analyze_sentiment(tweets: list) -> dict:
    if not tweets:
        return {
            'total_tweets': 0,
            'total_engagement': 0,
            'high_engagement_tweets': [],
            'daily_stats': {},
            'summary': "No verified tweets found for analysis."
        }
    
    total_engagement = sum(
        tweet['engagement']['retweets'] + 
        tweet['engagement']['likes'] + 
        tweet['engagement']['quotes'] + 
        tweet['engagement']['bookmarks']
        for tweet in tweets
    )
    
    daily_stats = {}
    for tweet in tweets:
        date = tweet['date']
        if date not in daily_stats:
            daily_stats[date] = {
                'tweets': 0,
                'engagement': 0,
                'views': 0,
                'replies': 0
            }
        
        daily_stats[date]['tweets'] += 1
        daily_stats[date]['engagement'] += (
            tweet['engagement']['retweets'] + 
            tweet['engagement']['likes'] + 
            tweet['engagement']['quotes'] + 
            tweet['engagement']['bookmarks']
        )
        daily_stats[date]['views'] += tweet['engagement']['views']
        daily_stats[date]['replies'] += tweet['engagement']['replies']
    
    sorted_tweets = sorted(
        tweets,
        key=lambda x: (
            x['engagement']['retweets'] + 
            x['engagement']['likes'] + 
            x['engagement']['quotes'] + 
            x['engagement']['bookmarks']
        ),
        reverse=True
    )
    
    high_engagement_tweets = sorted_tweets[:5]
    
    return {
        'total_tweets': len(tweets),
        'total_engagement': total_engagement,
        'high_engagement_tweets': high_engagement_tweets,
        'daily_stats': daily_stats,
        'summary': f"Found {len(tweets)} verified tweets with total engagement of {total_engagement} across {len(daily_stats)} days."
    }

def main():
    load_dotenv()
    
    import argparse
    parser = argparse.ArgumentParser(description='Analyze Twitter sentiment for a memecoin')
    parser.add_argument('--coin', required=True, help='Name of the memecoin to analyze')
    parser.add_argument('--days', type=int, default=60, help='Number of days to look back')
    
    args = parser.parse_args()
    
    try:
        tweets = get_verified_tweets(args.coin, args.days, os.getenv('RAPIDAPI_KEY'))
        
        analysis = analyze_sentiment(tweets)
        
        print("\n=== Twitter Analysis Results ===")
        print(f"\nSummary: {analysis['summary']}")
        
        if analysis['daily_stats']:
            print("\nDaily Statistics:")
            for date, stats in sorted(analysis['daily_stats'].items(), reverse=True):
                print(f"\n{date}:")
                print(f"  Tweets: {stats['tweets']}")
                print(f"  Total Engagement: {stats['engagement']:,}")
                print(f"  Views: {stats['views']:,}")
                print(f"  Replies: {stats['replies']:,}")
                print(f"  Engagement Details:")
                avg_quotes = sum(tweet['engagement']['quotes'] for tweet in tweets if tweet['date'] == date) / stats['tweets'] if stats['tweets'] > 0 else 0
                avg_bookmarks = sum(tweet['engagement']['bookmarks'] for tweet in tweets if tweet['date'] == date) / stats['tweets'] if stats['tweets'] > 0 else 0
                print(f"    Average Quotes: {avg_quotes:.2f}")
                print(f"    Average Bookmarks: {avg_bookmarks:.2f}")
        
        if analysis['high_engagement_tweets']:
            print("\nTop Engaging Tweets:")
            for i, tweet in enumerate(analysis['high_engagement_tweets'], 1):
                print(f"\n{i}. @{tweet['user']['username']} ({tweet['user']['followers']:,} followers) on {tweet['date']}")
                print(f"Text: {tweet['text']}")
                print(f"Engagement: {tweet['engagement']['retweets']:,} RTs, {tweet['engagement']['likes']:,} likes, "
                      f"{tweet['engagement']['views']:,} views, {tweet['engagement']['quotes']:,} quotes, "
                      f"{tweet['engagement']['bookmarks']:,} bookmarks")
                if tweet.get('media'):
                    if 'video' in tweet['media']:
                        print("Media: Video included")
                    if 'photo' in tweet['media']:
                        print(f"Media: {len(tweet['media']['photo'])} photos included")
        
        output_file = f"{args.coin}_twitter_analysis.json"
        with open(output_file, 'w') as f:
            json.dump({
                'coin': args.coin,
                'analysis_date': datetime.now().isoformat(),
                'analysis': analysis,
                'all_tweets': tweets
            }, f, indent=2)
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")

if __name__ == "__main__":
    main()