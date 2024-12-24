# Memecoin Analyzer with Celebrity Opinions 🚀

## Usage

```bash
python main.py --image <path_to_image> --description "<coin_description>" --coin "<coin_name>"
```

Example:
```bash
python main.py --image ./bitcoin.png --description "the bitcoin logo" --coin bitcoin
```

## Example Output

Here's a sample analysis of Bitcoin:

```
=== Memecoin Analysis Results ===

Final Recommendation: INVEST

Full Analysis:
[... detailed analysis of the coin's visual branding, Twitter engagement, and market potential ...]

=== Celebrity Opinions ===

Morgan Freeman: Let me tell you some real shit about Bitcoin. This revolutionary shit is like destiny bullshit, and you fucking see, it's the future. The logo alone screams, "Invest in me, you dumbass!" With Twitter blowing up like a goddamn volcano, you'd be a fool not to jump on this grand vision. Sure, it's volatile as fuck, but who doesn't love a rollercoaster? So, invest, laugh at the dips, and ride that motherfucker to the moon!

Elon Musk: Fuck yeah, Bitcoin's the shit! That logo's dope as fuck and screams bleeding-edge tech. The Twitter game? Insane engagement, bro! It's like a fucking meme-driven party where the community fucks harder than a SpaceX launch. Volatility? Who gives a shit? That's just the thrill of the ride, balls to the wall! Dump your cash in, watch it moon. This shit's gonna make you rich, or at least give you a wild fucking story. Invest, you pussy!

Snoop Dogg: Yo, listen up, bitches! Bitcoin's vibe is off the chain, and the community shit is tight as fuck. That logo? Iconic, like my blunt rolls. Twitter's poppin' with that DCA strategy, and I'm all about that morning routine, high as fuck while stackin' them coins. Yeah, it's volatile, but who gives a fuck? Blaze it up and ride that wave, homie. Invest in Bitcoin, and let's get rich as fuck! Fuck that shit, let's do this!
```

## Output Files

The analysis results are saved in a JSON file named `[coin_name]_complete_analysis.json`, containing:
- Coin details and analysis date
- Full AI analysis and recommendation
- Twitter sentiment analysis
- Celebrity opinions