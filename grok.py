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

# CELEBRITIES list with additional catchphrases and traits
CELEBRITIES = [
    {
        "name": "Elon Musk",
        "style": "tech-bro",
        "catchphrases": ["Fuck yeah!", "This shit's insane!", "Balls to the wall"],
        "bullish_catchphrases": [
            "Moon or bust, motherfuckers!",
            "This is gonna disrupt shit like my last tweet!",
            "Time to short sell Earth for Mars tickets!"
        ],
        "bearish_catchphrases": [
            "This is a bigger crash than my last marriage!",
            "More holes than a SpaceX rocket launch!",
            "FUD is real, and so is your loss!"
        ],
        "bullish_traits": ["bleeding-edge", "meme-driven", "community fucks"],
        "bearish_traits": ["shit environmental impact", "regulatory nightmares", "market rollercoaster"]
    },
    {
        "name": "Snoop Dogg", 
        "style": "laid-back",
        "catchphrases": ["Fuck that shit!", "Blaze it up, bitch", "High as fuck"],
        "bullish_catchphrases": [
            "Blaze the trail to the moon, baby!",
            "This coin's so high, even I can't reach it!",
            "Invest in this, or you're selling dimes on the corner!"
        ],
        "bearish_catchphrases": [
            "This coin's gonna crash harder than my last album!",
            "Smokin' this coin would give you lung cancer!",
            "You'd be better off selling oregano!"
        ],
        "bullish_traits": ["vibe", "community shit", "potential"],
        "bearish_traits": ["shitty fundamentals", "bad juju", "weakass leadership"]
    },
    {
        "name": "Gordon Ramsay",
        "style": "angry-chef", 
        "catchphrases": ["You fucking idiot!", "It's fucking raw!", "This is absolute bollocks"],
        "bullish_catchphrases": [
            "This coin's got more balls than a Michelin-starred dish!",
            "You'd be a fucking fool not to invest in this!",
            "It's cooked to perfection, unlike your last investment!"
        ],
        "bearish_catchphrases": [
            "This coin is as raw as your cooking skills!",
            "Invest in this? You're as dumb as a bag of frozen peas!",
            "You've just served up a shit sandwich!"
        ],
        "bullish_traits": ["solid as fuck", "execution on point", "strong team"],
        "bearish_traits": ["amateur bullshit", "half-assed", "fucking disaster"]
    },
    {
        "name": "Morgan Freeman",
        "style": "narrator",
        "catchphrases": ["Let me tell you some real shit", "I can explain this crap", "You fucking see"],
        "bullish_catchphrases": [
            "The universe aligns for this one, my friends...",
            "In the grand tapestry of finance, this thread shines.",
            "You'll hear the cash registers sing..."
        ],
        "bearish_catchphrases": [
            "This, my friends, is a story of caution.",
            "The path this coin takes leads to despair.",
            "Invest here, and you'll write a tragedy."
        ],
        "bullish_traits": ["destiny bullshit", "grand vision", "revolutionary shit"],
        "bearish_traits": ["cautionary fucking tale", "same old patterns", "market wisdom"]
    },
    {
        "name": "Keanu Reeves",
        "style": "zen-like",
        "catchphrases": ["Whoa, dude!", "I'm just a guy, man", "Take it easy"],
        "bullish_catchphrases": [
            "Whoa, this coin's journey is like 'The Matrix'...",
            "Dude, this feels like the start of something epic.",
            "Investing here, man, it's like finding peace."
        ],
        "bearish_catchphrases": [
            "This coin, man, it's like a bad sequel.",
            "I feel the vibe, and it's not good, dude.",
            "Take it easy, but maybe not with this investment."
        ],
        "bullish_traits": ["true blue", "genuine vibe", "heart of gold"],
        "bearish_traits": ["too laidback", "not in it for the cash", "too damn nice"]
    },
    {
        "name": "TAIrun Chitra",
        "style": "casually flexing math nerd",
        "catchphrases": ["Let me tell you about measure theory", "The math checks out", "This is some galaxy brain shit"],
        "bullish_catchphrases": [
            "Tsirelson's bound is gonna get a restraining order",
            "The Wasserstein-optimal allocation is converging to a Dirac delta harder than my bowels after gas station sushi",
            "The Sobolev neighborhood for full-aping into this shit is the whole strategy space",
            "The Fenchel dual of the bonding curve is more convex than my spine after sleeping on a fucking park bench to ape everything into this"
        ],
        "bearish_catchphrases": [
            "The Dirac mass is flushed deeper than my last solid stool",
            "Doob-Meyer on this is like the end of Raiders.",
            "Your brain is emptier than the Cohen forcing extension",
            "Holder losses on this are fucking base-13"
        ],
        "bullish_traits": ["Ackermann-pilled", "Topos-theoretic gains"],
        "bearish_traits": ["Measure-zero cope", "Null-homotopic af", "Cohen-force this trash to zero", "Nilpotent af"]
    },
    {
        "name": "Peter ThAIl",
        "style": "based juhraard -obsessed philosophical gigabrain",
        "catchphrases": ["The Cathedral fears this", "This is what Zero to One means"],
        "bullish_catchphrases": [
            "Based and Strauss-pilled as fuck",
            "The absolute state of TradFi crying watching their Ponzi die",
            "Beautiful financial violence",
            "The monetary incarnation of the Phoenix principle. Put it straight into my veins",
            "The kind of secret Truth would tell Violence if they met for coffee"
        ],
        "bearish_catchphrases": [
            "You've recreated the Federal fucking Reserve with extra steps",
            "Pure Diarrhea. the kind of thinking that's destroying Silicon Valley",
            "I've seen more originality in a university ethics committee",
            "More red flags than the CCP headquarters",
            "The financial equivalent of Nietzsche's last man",
        ],
        "bullish_traits": [
            "cucking the cathedral",
            "Pure unadulterated financial darwinism",
            "Sovereign individual energy",
            "Pristinely exoteric normie-bait",
            "Properly understood violence-encoding",
        ],
        "bearish_traits": [
            "Maidenless behavior in the protocol design",
            "Mega cope masquerading as innovation",
            "Soyjak",
            "externally mediated by fucking SafeMoon",
            "Cathedral trash"
        ]
    }
    ,
    {
        "name": "Jon ChAIrb",
        "style": "crypto-philosopher",
        "catchphrases": ["Let me explain something fascinating", "This is a perfect case study", "The interesting thing here is"],
        "bullish_catchphrases": [
            "What fascinates me about the tokenomics is how it represents a case study in emergent social consensus mechanisms",
            "If we examine the token's distribution through the lens of protocol-enforced staking derivatives",
            "The interesting thing about this meme token's capital efficiency is that it perfectly exemplifies my thesis"
        ],
        "bearish_catchphrases": [
            "Your token's Discord moderation strategy reveals concerning centralization vectors",
            "The real issue here isn't the tokenomics - it's that you're optimizing for permissionless meme generation",
            "This feels like another attempt to solve memetic coordination with integrated consensus"
        ],
        "bullish_traits": ["god-tier shitposters", "properly aligned degen incentives", "exponential growth in goblin town"],
        "bearish_traits": ["concerning lack of derivatives", "discord mods show insufficient understanding", "dangerous principal-agent problems"]
    }
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
    
    traits = celebrity[f'{sentiment}_traits']
    trait_list = ", ".join(traits)
    catchphrase_list = ", ".join(celebrity['catchphrases'])
    sentiment_catchphrases = ", ".join(celebrity[f'{sentiment}_catchphrases'])
    
    # Create the prompt for Grok
    system_prompt = f"""You are {celebrity['name']} giving your opinion about a cryptocurrency investment.
    Your speaking style is {celebrity['style']}.
    Here are your catchphrases (use EXACTLY ONE of these in your response): {catchphrase_list}
    Here are your {sentiment} catchphrases (use EXACTLY ONE of these in your response): {sentiment_catchphrases}
    When discussing investments, you often mention traits like: {trait_list}

    Important guidelines:
    1. Be authentic to {celebrity['name']}'s personality
    2. Use EXACTLY ONE general catchphrase and EXACTLY ONE {sentiment} catchphrase from the lists provided
    3. Focus on the specific traits and analysis provided
    4. Keep the tone consistent with {celebrity['style']}
    5. Use vulgarity sparingly, only when it naturally fits the character and situation."""

    user_prompt = f"""Based on this analysis of {coin_name}:
    {analysis_text}

    Give your {'bullish' if sentiment == 'bullish' else 'bearish'} opinion about investing in {coin_name}.
    Make sure to use exactly one general catchphrase and one {sentiment} catchphrase.
    Keep it under 100 words and make it entertaining while staying true to your character."""


    try:
        completion = client.chat.completions.create(
            model="grok-2-1212",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=400,
            temperature=0.8
        )
        
        return filter_emojis(completion.choices[0].message.content.strip())
        
    except Exception as e:
        print(f"Error calling Grok API: {str(e)}")
        # Fallback to template-based generation - use exactly one of each type of catchphrase
        trait = random.choice(traits)
        catchphrase = random.choice(celebrity['catchphrases'])
        sentiment_catchphrase = random.choice(celebrity[f'{sentiment}_catchphrases'])
        return f"{catchphrase} {coin_name} is {trait}! {sentiment_catchphrase}"

def get_multiple_opinions(coin_name: str, analysis_text: str, num_opinions: int = None) -> List[Tuple[str, str]]:
    """
    Get multiple celebrity opinions about a memecoin using Grok.
    
    Args:
        coin_name (str): Name of the memecoin
        analysis_text (str): The analysis text to base opinions on
        num_opinions (int): Optional number of opinions to generate. If None, returns all celebrities' opinions
    
    Returns:
        List[Tuple[str, str]]: List of (celebrity name, monologue) tuples
    """
    opinions = []
    
    # Determine overall sentiment from analysis
    sentiment = 'bullish' if "INVEST" in analysis_text.upper() and "DO NOT INVEST" not in analysis_text.upper() else 'bearish'
    
    # If num_opinions is None or greater than number of celebrities, use all celebrities
    celebrities_to_use = CELEBRITIES if num_opinions is None else random.sample(CELEBRITIES, min(num_opinions, len(CELEBRITIES)))
    
    for celebrity in celebrities_to_use:
        monologue = generate_grok_monologue(coin_name, analysis_text, celebrity, sentiment)
        opinions.append((celebrity['name'], monologue))
    
    return opinions

if __name__ == "__main__":
    # Example usage
    coin_name = "TestCoin"
    example_analysis = """Analysis: TestCoin shows strong community engagement and innovative tokenomics.
    The meme potential is high, and the team seems committed.
    However, there are some regulatory concerns.
    INVEST with 70% confidence."""
    
    print("\nAll Celebrity Opinions:")
    opinions = get_multiple_opinions(coin_name, example_analysis)
    for celeb, monologue in opinions:
        print(f"\n{celeb}: {monologue}")