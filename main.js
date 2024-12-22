require('dotenv').config();
const { RateLimit } = require('async-sema');

const MAX_COINS = 10;
const DAYS = 30;
const MAX_RETRIES = 3;

// Create rate limiter: 10 requests per minute = 1 request per 6 seconds
const limiter = RateLimit(10, { timeUnit: 60000 });

const API_KEY = process.env.COINGECKO_API_KEY;
const headers = {
    'X-Cg-Api-Key': API_KEY,
    'Content-Type': 'application/json'
};

// Helper function to delay execution
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

// Helper function to implement exponential backoff
async function fetchWithRetry(url, options, retryCount = 0) {
    try {
        await limiter();
        const response = await fetch(url, options);
        
        if (response.status === 429 && retryCount < MAX_RETRIES) {
            const waitTime = Math.pow(2, retryCount) * 10000; // exponential backoff: 10s, 20s, 40s
            console.log(`Rate limited. Waiting ${waitTime/1000} seconds before retry ${retryCount + 1}/${MAX_RETRIES}...`);
            await delay(waitTime);
            return fetchWithRetry(url, options, retryCount + 1);
        }
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`HTTP error! status: ${response.status}, message: ${errorText}`);
        }
        
        return response;
    } catch (error) {
        if (retryCount < MAX_RETRIES && error.message.includes('429')) {
            const waitTime = Math.pow(2, retryCount) * 10000;
            console.log(`Error occurred. Waiting ${waitTime/1000} seconds before retry ${retryCount + 1}/${MAX_RETRIES}...`);
            await delay(waitTime);
            return fetchWithRetry(url, options, retryCount + 1);
        }
        throw error;
    }
}

async function getTopCoins() {
    try {
        const response = await fetchWithRetry(
            'https://api.coingecko.com/api/v3/coins/markets?' + new URLSearchParams({
                vs_currency: 'usd',
                order: 'market_cap_desc',
                per_page: MAX_COINS,
                page: 1,
                sparkline: false,
                category: 'meme-token'
            }),
            { method: 'GET', headers }
        );
        
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching top coins:', error);
        return null;
    }
}

async function getHistoricalPrices(coinId) {
    try {
        const response = await fetchWithRetry(
            'https://api.coingecko.com/api/v3/coins/' + coinId + '/market_chart?' + new URLSearchParams({
                vs_currency: 'usd',
                days: DAYS,
                interval: 'daily'
            }),
            { method: 'GET', headers }
        );
        
        const data = await response.json();
        return data.prices;
    } catch (error) {
        console.error(`Error fetching data for ${coinId}:`, error);
        return null;
    }
}

async function getAllMemecoinPrices() {
    console.log(`Fetching top ${MAX_COINS} memecoins...`);
    const memecoins = await getTopCoins();
    
    if (!memecoins) {
        console.error('Failed to fetch memecoins list');
        return;
    }

    console.log(`Found ${memecoins.length} memecoins\n`);

    const memecoinData = {};

    for (const coin of memecoins) {
        console.log(`Processing: ${coin.name} (${coin.symbol.toUpperCase()})`);
        
        memecoinData[coin.id] = {
            name: coin.name,
            symbol: coin.symbol.toUpperCase(),
            market_cap_rank: coin.market_cap_rank,
            current_price: coin.current_price,
            market_cap: coin.market_cap,
            historical_prices: []
        };
        
        const prices = await getHistoricalPrices(coin.id);
        if (prices) {
            memecoinData[coin.id].historical_prices = prices.map(([timestamp, price]) => ({
                date: new Date(timestamp).toISOString().split('T')[0],
                price: price
            }));
        }
        
        // Add a small delay between processing each coin
        await delay(2000);
    }

    const fs = require('fs');
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    fs.writeFileSync(
        `memecoin_data_${timestamp}.json`,
        JSON.stringify(memecoinData, null, 2)
    );

    console.log('\nData collection complete! Results saved to file.');
    console.log('Summary:');
    console.log(`Total memecoins processed: ${Object.keys(memecoinData).length}`);
}

// Execute the main function
getAllMemecoinPrices().catch(error => {
    console.error('Main execution error:', error);
});