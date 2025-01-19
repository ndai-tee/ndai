"""
Example input (copy and paste this into terminal):

echo '{"image": "https://cdn.pixabay.com/photo/2018/10/31/22/42/squirrel-3786845_1280.jpg", "token_name": "squirrelnuts", "pitch": "SquirrelNuts is revolutionizing decentralized storage by utilizing a unique gathering and storing mechanism inspired by natures most efficient data hoarders. Just as squirrels expertly cache their nuts for future use, our protocol enables users to efficiently store and retrieve data across our network, with an innovative scarcity model based on seasonal storage cycles."}' | python3 main.py
"""

import requests
from transformers import AutoModelForCausalLM, AutoProcessor
from PIL import Image
import io
import torch
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
COINGECKO_API_KEY = os.getenv('COINGECKO_API_KEY')
RAPID_API_KEY = os.getenv('RAPID_API_KEY')

def get_device():
    if torch.cuda.is_available():
        return "cuda"
    elif torch.backends.mps.is_available():
        return "cpu"
    return "cpu"

def get_tweets(query):
    url = "https://twitter-api45.p.rapidapi.com/search.php"
    querystring = {"query": query, "search_type": "Top"}
    headers = {
        "x-rapidapi-key": RAPID_API_KEY,
        "x-rapidapi-host": "twitter-api45.p.rapidapi.com"
    }
    
    try:
        response = requests.get(url, headers=headers, params=querystring)
        data = response.json()
        tweets = []
        if data and 'timeline' in data:
            for tweet in data['timeline'][:5]:
                if 'text' in tweet and 'type' in tweet and tweet['type'] == 'tweet':
                    tweets.append(tweet['text'])
        return tweets
    except Exception as e:
        print(f"Error fetching tweets: {e}")
        return []

def download_image(url):
    try:
        response = requests.get(url)
        return Image.open(io.BytesIO(response.content))
    except Exception as e:
        print(f"Error downloading image: {e}")
        return None

def check_token_exists(pitch):
    """
    Check if the token mentioned in the pitch exists on CoinGecko.
    Returns (exists, token_name) tuple.
    """
    try:
        # Extract potential token name from the first sentence of the pitch
        first_sentence = pitch.split('.')[0].lower()
        potential_tokens = [word for word in first_sentence.split() if len(word) > 2]
        
        # Remove common words that might appear in first sentence
        common_words = {'the', 'has', 'with', 'and', 'for', 'that', 'this', 'are', 'new'}
        potential_tokens = [token for token in potential_tokens if token not in common_words]
        
        if not potential_tokens:
            return False, None
        
        # Search for the first potential token name
        url = "https://api.coingecko.com/api/v3/search"
        headers = {
            "accept": "application/json",
            "x-cg-demo-api-key": COINGECKO_API_KEY
        }
        
        for token in potential_tokens[:2]:  # Check first two potential tokens
            params = {"query": token}
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('coins'):
                    return True, token
        
        return False, potential_tokens[0] if potential_tokens else None
    except Exception as e:
        print(f"Error checking token existence: {e}")
        return False, None

def analyze_content(input_data):
    """
    Analyzes the sentiment based on provided image, pitch, and token name.
    First checks if the token already exists on CoinGecko.
    """
    try:
        if not isinstance(input_data, dict) or 'image' not in input_data or 'pitch' not in input_data or 'token_name' not in input_data:
            raise ValueError("Input must be a dictionary with 'image', 'pitch', and 'token_name' keys")

        # Check if token exists on CoinGecko
        url = "https://api.coingecko.com/api/v3/search"
        headers = {
            "accept": "application/json",
            "x-cg-demo-api-key": COINGECKO_API_KEY
        }
        params = {"query": input_data['token_name']}
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('coins'):
                return {
                    'sentiment': 'REJECTED',
                    'reason': f"Token '{input_data['token_name']}' already exists on CoinGecko",
                    'pitch': input_data['pitch']
                }

        device = get_device()
        model_id = "microsoft/Phi-3.5-vision-instruct"
        model = AutoModelForCausalLM.from_pretrained(
            model_id,
            device_map=device,
            trust_remote_code=True,
            torch_dtype=torch.float32,
            _attn_implementation='eager'
        )
        processor = AutoProcessor.from_pretrained(
            model_id,
            trust_remote_code=True,
            num_crops=16
        )
        
        # Download image
        image = download_image(input_data['image'])
        if image is None:
            raise Exception("Failed to download image")
        
        # Get image description
        messages = [
            {"role": "user", "content": f"<|image_1|>\nDescribe this image in one sentence:"}
        ]
        prompt = processor.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = processor(prompt, [image], return_tensors="pt")
        if device != "cpu":
            inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            desc_ids = model.generate(
                **inputs,
                max_new_tokens=50,
                temperature=0.7,
                do_sample=True,
                eos_token_id=processor.tokenizer.eos_token_id,
            )
        
        desc_ids = desc_ids[:, inputs['input_ids'].shape[1]:]
        image_description = processor.batch_decode(
            desc_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True
        )[0].strip()
        
        # Use token name for tweet search instead of first 3 words
        recent_tweets = get_tweets(input_data['token_name'])
        tweets_text = "\n".join([f"Recent Tweet: {tweet}" for tweet in recent_tweets])
        
        # Analyze everything together
        messages = [
            {"role": "user", "content": f"<|image_1|>\nBased on the following information, first verify if the image matches the pitch. If they don't match, respond with 'REJECT'. If they match, respond with either 'BULLISH' or 'BEARISH' for the overall market sentiment:\n\nPitch: {input_data['pitch']}\n\nImage description: {image_description}\n\nRecent Tweets:\n{tweets_text}"}
        ]
        
        prompt = processor.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = processor(prompt, [image], return_tensors="pt")
        if device != "cpu":
            inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            generate_ids = model.generate(
                **inputs,
                max_new_tokens=10,
                temperature=0.7,
                do_sample=True,
                eos_token_id=processor.tokenizer.eos_token_id,
            )
        
        generate_ids = generate_ids[:, inputs['input_ids'].shape[1]:]
        response = processor.batch_decode(
            generate_ids,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True
        )[0].strip().lower()
        
        if 'reject' in response:
            return {
                'sentiment': 'REJECTED',
                'reason': 'Image content does not match the pitch',
                'pitch': input_data['pitch'],
                'image_description': image_description,
                'recent_tweets': recent_tweets
            }
        
        return {
            'sentiment': 'bullish' if 'bull' in response else 'bearish',
            'pitch': input_data['pitch'],
            'image_description': image_description,
            'recent_tweets': recent_tweets
        }
        
    except Exception as e:
        print(f"Error in analysis: {e}")
        return None

def main():
    try:
        # Read JSON input from stdin
        input_json = json.loads(input())
        
        # Validate required fields
        required_fields = ['image', 'token_name', 'pitch']
        if not all(field in input_json for field in required_fields):
            raise ValueError("Input JSON must contain 'image', 'token_name', and 'pitch' fields")
        
        result = analyze_content(input_json)
        if result:
            # Convert result to JSON output
            output = {
                'sentiment': result['sentiment'],
                'image_description': result.get('image_description', ''),
                'recent_tweets': result.get('recent_tweets', [])
            }
            if result['sentiment'] == 'REJECTED':
                output['reason'] = result['reason']
            
            # Print JSON output
            print(json.dumps(output))
        else:
            print(json.dumps({'error': 'Analysis failed'}))
            
    except json.JSONDecodeError:
        print(json.dumps({'error': 'Invalid JSON input'}))
    except Exception as e:
        print(json.dumps({'error': str(e)}))

if __name__ == "__main__":
    main()
