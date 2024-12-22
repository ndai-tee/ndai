const fs = require('fs');
require('dotenv').config();

// Read memecoin data
const memecoinData = JSON.parse(fs.readFileSync('memecoin_data.json', 'utf8'));

// RapidAPI configuration from environment variables
const rapidApiKey = process.env.RAPID_API_KEY;
const rapidApiHost = process.env.RAPID_API_HOST;

if (!rapidApiKey || !rapidApiHost) {
    console.error('Error: RAPID_API_KEY and RAPID_API_HOST must be set in .env file');
    process.exit(1);
}

// Rate limiting configuration
const INITIAL_RETRY_DELAY = 1000; // 1 second
const MAX_RETRY_DELAY = 32000; // 32 seconds
const MAX_RETRIES = 5;

async function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function fetchWithRetry(url, options, retryCount = 0) {
    try {
        const response = await fetch(url, options);
        
        // Check if we hit the rate limit
        if (response.status === 429) {
            if (retryCount >= MAX_RETRIES) {
                throw new Error('Max retries reached for rate limit');
            }

            // Calculate delay with exponential backoff
            const delay = Math.min(INITIAL_RETRY_DELAY * Math.pow(2, retryCount), MAX_RETRY_DELAY);
            console.log(`Rate limit hit. Waiting ${delay/1000} seconds before retry ${retryCount + 1}/${MAX_RETRIES}`);
            
            await sleep(delay);
            return fetchWithRetry(url, options, retryCount + 1);
        }

        // Check for other error status codes
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.text();
        return JSON.parse(result);
    } catch (error) {
        if (error.message.includes('rate limit') || error.message.includes('429')) {
            if (retryCount >= MAX_RETRIES) {
                throw new Error('Max retries reached for rate limit');
            }
            const delay = Math.min(INITIAL_RETRY_DELAY * Math.pow(2, retryCount), MAX_RETRY_DELAY);
            console.log(`Error with rate limit. Waiting ${delay/1000} seconds before retry ${retryCount + 1}/${MAX_RETRIES}`);
            
            await sleep(delay);
            return fetchWithRetry(url, options, retryCount + 1);
        }
        throw error;
    }
}

async function fetchTweetsForMemecoin(coinName) {
    const url = `https://twitter-api45.p.rapidapi.com/search.php?query=${encodeURIComponent(coinName)}&search_type=Top`;
    const options = {
        method: 'GET',
        headers: {
            'x-rapidapi-key': rapidApiKey,
            'x-rapidapi-host': rapidApiHost
        }
    };

    try {
        return await fetchWithRetry(url, options);
    } catch (error) {
        console.error(`Error fetching tweets for ${coinName}:`, error.message);
        return null;
    }
}

async function main() {
    const results = {};

    // Process each memecoin
    for (const [coinKey, coinData] of Object.entries(memecoinData)) {
        console.log(`Fetching tweets for ${coinData.name}...`);
        
        // Always wait between requests to prevent hitting rate limits
        if (Object.keys(results).length > 0) {
            await sleep(INITIAL_RETRY_DELAY);
        }

        const tweets = await fetchTweetsForMemecoin(coinData.name);
        results[coinKey] = tweets;
        
        // Log progress
        console.log(`Completed ${Object.keys(results).length}/${Object.keys(memecoinData).length} coins`);
    }

    // Save results to a new file
    fs.writeFileSync('memecoin_tweets.json', JSON.stringify(results, null, 2));
    console.log('Finished fetching tweets. Results saved to memecoin_tweets.json');
}

main().catch(console.error); 