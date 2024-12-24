from datetime import datetime
import json
from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForCausalLM
import argparse
import os
from twitter import get_verified_tweets, analyze_sentiment
from dotenv import load_dotenv
from grok import get_multiple_opinions
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any

# Configuration
DAYS_TO_ANALYZE = 5  # Number of days to look back for Twitter analysis

def get_tweets_for_day(coin_name: str, days_back: int, api_key: str) -> list:
    """Get tweets for a specific day"""
    return get_verified_tweets(coin_name, days_back=days_back, api_key=api_key)

def get_twitter_analysis(coin_name: str) -> Dict[str, Any]:
    """Get Twitter sentiment analysis in parallel"""
    print("Fetching Twitter sentiment...")
    print(f"Getting tweets for the last {DAYS_TO_ANALYZE} days:")
    
    api_key = os.getenv('RAPIDAPI_KEY')
    tweets = []
    
    with ThreadPoolExecutor(max_workers=DAYS_TO_ANALYZE) as executor:
        future_to_day = {
            executor.submit(get_tweets_for_day, coin_name, days_back + 1, api_key): days_back
            for days_back in range(DAYS_TO_ANALYZE)
        }
        
        for future in as_completed(future_to_day):
            days_back = future_to_day[future]
            try:
                daily_tweets = future.result()
                tweets.extend(daily_tweets)
                print(f"✓ Fetched tweets from {days_back} days ago")
            except Exception as e:
                print(f"× Failed to fetch tweets from {days_back} days ago: {str(e)}")
    
    twitter_analysis = analyze_sentiment(tweets)
    
    # Create Twitter summary for the prompt
    twitter_summary = f"\nVerified Twitter Activity in last {DAYS_TO_ANALYZE} days:"
    twitter_summary += f"\n- Total Tweets: {twitter_analysis['total_tweets']}"
    twitter_summary += f"\n- Total Engagement: {twitter_analysis['total_engagement']}"
    
    if twitter_analysis['high_engagement_tweets']:
        twitter_summary += "\n\nTop Engaging Tweets:"
        for i, tweet in enumerate(twitter_analysis['high_engagement_tweets'][:3], 1):
            twitter_summary += f"\n{i}. @{tweet['user']['username']}: {tweet['text'][:200]}..."
    
    return {
        'analysis': twitter_analysis,
        'summary': twitter_summary
    }

def get_vision_analysis(image_path: str, description: str, twitter_summary: str) -> Dict[str, Any]:
    """Get vision model analysis"""
    print("\nRunning vision analysis...")
    
    # Determine device
    if torch.cuda.is_available():
        device = "cuda"
    elif torch.backends.mps.is_available():
        device = "cpu"  # Using CPU for stability with MPS
    else:
        device = "cpu"
        
    print(f"Using device: {device}")
    
    model_id = "microsoft/Phi-3.5-vision-instruct"
    
    # Initialize model with flash attention
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        device_map=device,
        trust_remote_code=True,
        torch_dtype=torch.float32,
        _attn_implementation='eager'
    )
    
    # Initialize processor
    processor = AutoProcessor.from_pretrained(
        model_id,
        trust_remote_code=True,
        num_crops=4
    )
    
    # Load and prepare the image
    image = Image.open(image_path).convert("RGB")
    
    # Prepare the chat message with Twitter data
    messages = [
        {
            "role": "user",
            "content": f"<|image_1|>\nAnalyze this memecoin image and the following description as a cryptocurrency investment expert.\n\nDescription: {description}\n{twitter_summary}\n\nProvide a detailed analysis considering:\n1. Visual branding and appeal\n2. Twitter engagement and verified user sentiment\n3. Market potential and risks\n\nConclude with a clear INVEST or DO NOT INVEST recommendation and include a confidence score from 0-100%."
        }
    ]
    
    # Create prompt using chat template
    prompt = processor.tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    # Process inputs
    inputs = processor(prompt, [image], return_tensors="pt")
    
    # Move inputs to the same device as model
    inputs = {k: v.to(device) for k, v in inputs.items() if hasattr(v, 'to')}
    
    # Generate response
    generation_args = {
        "max_new_tokens": 1000,
        "temperature": 0.7,
        "do_sample": True,
    }
    
    generate_ids = model.generate(
        **inputs,
        eos_token_id=processor.tokenizer.eos_token_id,
        **generation_args
    )
    
    # Move tensors back to CPU for decoding
    generate_ids = generate_ids.cpu()
    
    # Remove input tokens and decode response
    generate_ids = generate_ids[:, inputs['input_ids'].shape[1]:]
    response_text = processor.batch_decode(
        generate_ids,
        skip_special_tokens=True,
        clean_up_tokenization_spaces=False
    )[0]
    
    # Determine recommendation based on strict keyword matching
    recommendation = 'DO NOT INVEST'
    if 'INVEST' in response_text.upper() and not any(phrase in response_text.upper() for phrase in ['DO NOT INVEST', 'DON\'T INVEST', 'NOT INVEST']):
        recommendation = 'INVEST'
    
    return {
        'recommendation': recommendation,
        'full_analysis': response_text
    }

def analyze_memecoin(image_path: str, description: str, coin_name: str) -> dict:
    """
    Analyze a memecoin using Phi-3.5-vision model and Twitter sentiment in parallel.
    
    Args:
        image_path (str): Path to the memecoin image
        description (str): Description of the memecoin
        coin_name (str): Name of the coin for Twitter analysis
    
    Returns:
        dict: Analysis results including recommendation and confidence
    """
    with ThreadPoolExecutor(max_workers=2) as executor:
        # Start Twitter analysis
        twitter_future = executor.submit(get_twitter_analysis, coin_name)
        
        try:
            # Wait for Twitter analysis to get summary for vision model
            twitter_result = twitter_future.result()
            
            # Start vision analysis with Twitter summary
            vision_future = executor.submit(get_vision_analysis, image_path, description, twitter_result['summary'])
            vision_result = vision_future.result()
            
            return {
                'recommendation': vision_result['recommendation'],
                'full_analysis': vision_result['full_analysis'],
                'twitter_analysis': twitter_result['analysis']
            }
            
        except Exception as e:
            raise Exception(f"Analysis failed: {str(e)}")

def main():
    load_dotenv()  # Load environment variables
    
    parser = argparse.ArgumentParser(description='Analyze a memecoin using vision model and Twitter sentiment')
    parser.add_argument('--image', required=True, help='Path to the memecoin image')
    parser.add_argument('--description', required=True, help='Description of the memecoin')
    parser.add_argument('--coin', required=True, help='Name of the coin for Twitter analysis')
    
    args = parser.parse_args()
    
    try:
        # Run main analysis
        result = analyze_memecoin(args.image, args.description, args.coin)
        
        print("\n=== Memecoin Analysis Results ===")
        print("\nFinal Recommendation:", result['recommendation'])
        print("\nFull Analysis:")
        print(result['full_analysis'])
        
        # Get celebrity opinions in parallel with saving results
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Start getting celebrity opinions
            opinions_future = executor.submit(get_multiple_opinions, args.coin, result['full_analysis'])
            
            # Prepare results for saving
            output_data = {
                'coin': args.coin,
                'analysis_date': datetime.now().isoformat(),
                'image_path': args.image,
                'description': args.description,
                'recommendation': result['recommendation'],
                'full_analysis': result['full_analysis'],
                'twitter_analysis': result['twitter_analysis']
            }
            
            # Get celebrity opinions result
            celebrity_opinions = opinions_future.result()
            output_data['celebrity_opinions'] = [(celeb, opinion) for celeb, opinion in celebrity_opinions]
            
            # Print celebrity opinions
            print("\n=== Celebrity Opinions ===")
            for celeb, opinion in celebrity_opinions:
                print(f"\n{celeb}: {opinion}")
            
            # Save complete results
            output_file = f"{args.coin}_complete_analysis.json"
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            print(f"\nComplete analysis saved to {output_file}")
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")

if __name__ == "__main__":
    main()