require('dotenv').config();
const { RateLimit } = require('async-sema');
const fs = require('fs');
const path = require('path');

const MAX_COINS = 10;
const DAYS = 30;
const MAX_RETRIES = 3;
const DATA_FILE = 'memecoin_data.json';
const BACKUP_DIR = 'backups';

// Create rate limiter: 10 requests per minute = 1 request per 6 seconds
const limiter = RateLimit(10, { timeUnit: 60000 });

const API_KEY = process.env.COINGECKO_API_KEY;
const headers = {
    'X-Cg-Api-Key': API_KEY,
    'Content-Type': 'application/json'
};

// Helper function to delay execution
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));

// Helper function to load existing data
function loadExistingData() {
    try {
        if (fs.existsSync(DATA_FILE)) {
            const data = JSON.parse(fs.readFileSync(DATA_FILE, 'utf8'));
            console.log(`Loaded existing data for ${Object.keys(data).length} coins`);
            return data;
        }
    } catch (error) {
        console.error('Error loading existing data:', error);
    }
    return {};
}

// Helper function to save data
function saveData(data) {
    try {
        // Save main data file
        fs.writeFileSync(DATA_FILE, JSON.stringify(data, null, 2));

        // Create backup directory if it doesn't exist
        if (!fs.existsSync(BACKUP_DIR)) {
            fs.mkdirSync(BACKUP_DIR);
        }

        // Create timestamped backup
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        fs.writeFileSync(
            path.join(BACKUP_DIR, `memecoin_data_${timestamp}.json`),
            JSON.stringify(data, null, 2)
        );
    } catch (error) {
        console.error('Error saving data:', error);
    }
}

// Helper function to check if coin needs update
function needsUpdate(existingData, coin) {
    if (!existingData[coin.id]) {
        return true;
    }

    const existing = existingData[coin.id];
    
    // Check if any key metrics have changed
    if (existing.market_cap_rank !== coin.market_cap_rank ||
        existing.current_price !== coin.current_price ||
        existing.market_cap !== coin.market_cap) {
        return true;
    }

    // Check if we have historical prices for the specified number of days
    if (!existing.historical_prices || 
        !existing.historical_prices.length || 
        !existing.days || 
        existing.days !== DAYS) {
        return true;
    }

    // Check if the most recent price is from today
    const lastPriceDate = new Date(existing.historical_prices[existing.historical_prices.length - 1].date);
    const today = new Date();
    return lastPriceDate.toDateString() !== today.toDateString();
}

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

// Helper function to check if we need to refresh the coin list
function needsListRefresh(existingData) {
    if (Object.keys(existingData).length === 0) {
        return true;
    }

    // Check if any coin was updated in the last hour
    const oneHourAgo = new Date(Date.now() - 60 * 60 * 1000);
    return !Object.values(existingData).some(coin => 
        new Date(coin.last_updated) > oneHourAgo
    );
}

async function getAllMemecoinPrices() {
    console.log('Loading existing data...');
    const existingData = loadExistingData();
    let memecoins = [];
    
    if (needsListRefresh(existingData)) {
        console.log(`Fetching top ${MAX_COINS} memecoins...`);
        memecoins = await getTopCoins();
        
        if (!memecoins) {
            console.error('Failed to fetch memecoins list');
            return;
        }
        console.log(`Found ${memecoins.length} memecoins\n`);
    } else {
        console.log('Using existing coin list from last update');
        // Convert existing data to format matching CoinGecko API response
        memecoins = Object.entries(existingData).map(([id, data]) => ({
            id,
            name: data.name,
            symbol: data.symbol,
            market_cap_rank: data.market_cap_rank,
            current_price: data.current_price,
            market_cap: data.market_cap
        }));
        console.log(`Found ${memecoins.length} existing memecoins\n`);
    }

    let updatedCount = 0;
    let skippedCount = 0;

    for (const coin of memecoins) {
        console.log(`Processing: ${coin.name} (${coin.symbol.toUpperCase()})`);
        
        if (!needsUpdate(existingData, coin)) {
            console.log(`Skipping ${coin.name} - already up to date`);
            skippedCount++;
            continue;
        }

        existingData[coin.id] = {
            name: coin.name,
            symbol: coin.symbol.toUpperCase(),
            market_cap_rank: coin.market_cap_rank,
            current_price: coin.current_price,
            market_cap: coin.market_cap,
            days: DAYS,
            last_updated: new Date().toISOString(),
            historical_prices: []
        };
        
        const prices = await getHistoricalPrices(coin.id);
        if (prices) {
            existingData[coin.id].historical_prices = prices.map(([timestamp, price]) => ({
                date: new Date(timestamp).toISOString().split('T')[0],
                price: price
            }));
            updatedCount++;
            // Save after each successful update
            saveData(existingData);
            console.log(`Updated and saved data for ${coin.name}`);
        }
        
        // Add a small delay between processing each coin
        await delay(2000);
    }

    console.log('\nData collection complete!');
    console.log('Summary:');
    console.log(`Total memecoins found: ${memecoins.length}`);
    console.log(`Coins updated: ${updatedCount}`);
    console.log(`Coins skipped (up to date): ${skippedCount}`);
    console.log(`Total coins in dataset: ${Object.keys(existingData).length}`);
}

// Execute the main function
getAllMemecoinPrices().catch(error => {
    console.error('Main execution error:', error);
});