import random
from typing import Tuple, List
import os
from openai import OpenAI
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()
XAI_API_KEY = os.getenv('XAI_API_KEY')

# Initialize xAI client
client = OpenAI(
    api_key=XAI_API_KEY,
    base_url="https://api.x.ai/v1",
)

CELEBRITIES = [
    {
        "name": "Elon Musk",
        "style": "tech-bro",
        "catchphrases": ["Fuck yeah!", "This shit's insane!", "Balls to the wall"],
        "bullish_traits": ["bleeding-edge", "meme-driven", "community fucks"],
        "bearish_traits": ["shit environmental impact", "regulatory nightmares", "market rollercoaster"]
    },
    {
        "name": "Snoop Dogg", 
        "style": "laid-back",
        "catchphrases": ["Fuck that shit!", "Blaze it up, bitch", "High as fuck"],
        "bullish_traits": ["vibe", "community shit", "potential"],
        "bearish_traits": ["shitty fundamentals", "bad juju", "weakass leadership"]
    },
    {
        "name": "Gordon Ramsay",
        "style": "angry-chef", 
        "catchphrases": ["You fucking idiot!", "It's fucking raw!", "This is absolute bollocks"],
        "bullish_traits": ["solid as fuck", "execution on point", "strong team"],
        "bearish_traits": ["amateur bullshit", "half-assed", "fucking disaster"]
    },
    {
        "name": "Morgan Freeman",
        "style": "narrator",
        "catchphrases": ["Let me tell you some real shit", "I can explain this crap", "You fucking see"],
        "bullish_traits": ["destiny bullshit", "grand vision", "revolutionary shit"],
        "bearish_traits": ["cautionary fucking tale", "same old patterns", "market wisdom"]
    },
]

def filter_emojis(text: str) -> str:
    """Remove emojis from text using regex"""
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
        u"\U00002702-\U000027B0"
        u"\U000024C2-\U0001F251"
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub('', text)

def generate_grok_monologue(coin_name: str, analysis_text: str, celebrity: dict, sentiment: str = None) -> str:
    """
    Generate a monologue using Grok model based on analysis and celebrity style.
    
    Args:
        coin_name (str): Name of the memecoin
        analysis_text (str): The analysis text to base the opinion on
        celebrity (dict): Celebrity information
        sentiment (str): Optional 'bullish' or 'bearish' sentiment. If None, determined from analysis
    
    Returns:
        str: Generated monologue
    """
    if not XAI_API_KEY:
        raise ValueError("XAI_API_KEY not found in environment variables")
    
    # Determine sentiment from analysis if not provided
    if sentiment is None:
        sentiment = 'bullish' if "INVEST" in analysis_text.upper() and "DO NOT INVEST" not in analysis_text.upper() else 'bearish'
    
    traits = celebrity['bullish_traits'] if sentiment == 'bullish' else celebrity['bearish_traits']
    trait_list = ", ".join(traits)
    catchphrase_list = ", ".join(celebrity['catchphrases'])
    
    # Create the prompt for Grok
    system_prompt = f"""You are {celebrity['name']} giving your vulgar, unfiltered opinion about a cryptocurrency investment.
Your speaking style is {celebrity['style']}.
You commonly use phrases like: {catchphrase_list}
You should mention traits like: {trait_list}

Be authentic to {celebrity['name']}'s personality and don't hold back on the profanity."""

    user_prompt = f"""Based on this analysis of {coin_name}:
{analysis_text}

Give your {'fucking positive' if sentiment == 'bullish' else 'fucking negative'} opinion about investing in {coin_name}.
Keep it under 100 words and make it funny as fuck."""

    try:
        completion = client.chat.completions.create(
            model="grok-2-1212",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=200,
            temperature=0.8
        )
        
        return filter_emojis(completion.choices[0].message.content.strip())
        
    except Exception as e:
        print(f"Error calling Grok API: {str(e)}")
        # Fallback to template-based generation
        catchphrase = random.choice(celebrity['catchphrases'])
        trait = random.choice(traits)
        
        return {
            "bullish": f"{catchphrase}! {coin_name} is {trait} - fuck yeah! Let's make some goddamn money!",
            "bearish": f"{catchphrase}! {coin_name}'s {trait} is bullshit! Don't waste your fucking time on it!"
        }[sentiment]

def get_multiple_opinions(coin_name: str, analysis_text: str, num_opinions: int = 3) -> List[Tuple[str, str]]:
    """
    Get multiple celebrity opinions about a memecoin using Grok.
    
    Args:
        coin_name (str): Name of the memecoin
        analysis_text (str): The analysis text to base opinions on
        num_opinions (int): Number of opinions to generate
    
    Returns:
        List[Tuple[str, str]]: List of (celebrity name, monologue) tuples
    """
    used_celebrities = set()
    opinions = []
    
    # Determine overall sentiment from analysis
    sentiment = 'bullish' if "INVEST" in analysis_text.upper() and "DO NOT INVEST" not in analysis_text.upper() else 'bearish'
    
    while len(opinions) < min(num_opinions, len(CELEBRITIES)):
        celebrity = random.choice(CELEBRITIES)
        if celebrity['name'] not in used_celebrities:
            monologue = generate_grok_monologue(coin_name, analysis_text, celebrity, sentiment)
            opinions.append((celebrity['name'], monologue))
            used_celebrities.add(celebrity['name'])
    
    return opinions

if __name__ == "__main__":
    # Example usage
    coin_name = "TestCoin"
    example_analysis = """Analysis: TestCoin shows strong community engagement and innovative tokenomics.
    The meme potential is high, and the team seems committed.
    However, there are some regulatory concerns.
    INVEST with 70% confidence."""
    
    print("\nSingle Celebrity Opinion:")
    celebrity = random.choice(CELEBRITIES)
    monologue = generate_grok_monologue(coin_name, example_analysis, celebrity)
    print(f"{celebrity['name']}: {monologue}")
    
    print("\nMultiple Celebrity Opinions:")
    opinions = get_multiple_opinions(coin_name, example_analysis)
    for celeb, monologue in opinions:
        print(f"\n{celeb}: {monologue}")
