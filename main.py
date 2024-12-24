from PIL import Image
import torch
from transformers import AutoProcessor, AutoModelForCausalLM
import argparse
import os
from twitter import get_verified_tweets, analyze_sentiment
from dotenv import load_dotenv
from grok import get_multiple_opinions  # Add import for celebrity opinions

# Configuration
DAYS_TO_ANALYZE = 1  # Number of days to look back for Twitter analysis

def analyze_memecoin(image_path: str, description: str, coin_name: str) -> dict:
    """
    Analyze a memecoin using Phi-3.5-vision model and Twitter sentiment.
    
    Args:
        image_path (str): Path to the memecoin image
        description (str): Description of the memecoin
        coin_name (str): Name of the coin for Twitter analysis
    
    Returns:
        dict: Analysis results including recommendation and confidence
    """
    # Get Twitter analysis first
    print("Fetching Twitter sentiment...")
    print(f"Getting tweets for the last {DAYS_TO_ANALYZE} days:")
    tweets = []
    for days_ago in range(DAYS_TO_ANALYZE):
        print(f"Fetching tweets from {days_ago} days ago...")
        daily_tweets = get_verified_tweets(coin_name, days_back=days_ago+1, api_key=os.getenv('RAPIDAPI_KEY'))
        tweets.extend(daily_tweets)
    twitter_analysis = analyze_sentiment(tweets)
    
    # Create Twitter summary for the prompt
    twitter_summary = f"\nVerified Twitter Activity in last {DAYS_TO_ANALYZE} days:"
    twitter_summary += f"\n- Total Tweets: {twitter_analysis['total_tweets']}"
    twitter_summary += f"\n- Total Engagement: {twitter_analysis['total_engagement']}"
    
    if twitter_analysis['high_engagement_tweets']:
        twitter_summary += "\n\nTop Engaging Tweets:"
        for i, tweet in enumerate(twitter_analysis['high_engagement_tweets'][:3], 1):
            twitter_summary += f"\n{i}. @{tweet['user']['username']}: {tweet['text'][:200]}..."
    
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
        'full_analysis': response_text,
        'recommendation': recommendation,
        'raw_response': response_text,
        'twitter_analysis': twitter_analysis
    }

def main():
    load_dotenv()  # Load environment variables
    
    parser = argparse.ArgumentParser(description='Analyze a memecoin using vision model and Twitter sentiment')
    parser.add_argument('--image', required=True, help='Path to the memecoin image')
    parser.add_argument('--description', required=True, help='Description of the memecoin')
    parser.add_argument('--coin', required=True, help='Name of the coin for Twitter analysis')
    
    args = parser.parse_args()
    
    try:
        result = analyze_memecoin(args.image, args.description, args.coin)
        
        print("\n=== Memecoin Analysis Results ===")
        print("\nFinal Recommendation:", result['recommendation'])
        print("\nFull Analysis:")
        print(result['full_analysis'])
        
        # Get celebrity opinions
        print("\n=== Celebrity Opinions ===")
        celebrity_opinions = get_multiple_opinions(args.coin, result['full_analysis'])
        for celeb, opinion in celebrity_opinions:
            print(f"\n{celeb}: {opinion}")
        
        # Save complete results
        import json
        from datetime import datetime
        
        output_file = f"{args.coin}_complete_analysis.json"
        with open(output_file, 'w') as f:
            json.dump({
                'coin': args.coin,
                'analysis_date': datetime.now().isoformat(),
                'image_path': args.image,
                'description': args.description,
                'recommendation': result['recommendation'],
                'full_analysis': result['full_analysis'],
                'twitter_analysis': result['twitter_analysis'],
                'celebrity_opinions': [(celeb, opinion) for celeb, opinion in celebrity_opinions]  # Add celebrity opinions to JSON
            }, f, indent=2)
        print(f"\nComplete analysis saved to {output_file}")
        
    except Exception as e:
        print(f"Error during analysis: {str(e)}")

if __name__ == "__main__":
    main()