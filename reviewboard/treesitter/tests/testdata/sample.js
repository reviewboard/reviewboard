/**
 * Sample JavaScript file for TreeSitter testing.
 */

const fs = require('fs');
const path = require('path');

// Constants
const CONFIG_FILE = 'config.json';
const DEFAULT_TIMEOUT = 5000;

/**
 * Utility class for file operations.
 */
class FileUtil {
    constructor(basePath = '.') {
        this.basePath = basePath;
        this.cache = new Map();
    }

    /**
     * Read a file asynchronously.
     * @param {string} filename - The name of the file to read.
     * @returns {Promise<string>} The file contents.
     */
    async readFile(filename) {
        const fullPath = path.join(this.basePath, filename);

        if (this.cache.has(fullPath)) {
            return this.cache.get(fullPath);
        }

        try {
            const content = await fs.promises.readFile(fullPath, 'utf8');
            this.cache.set(fullPath, content);
            return content;
        } catch (error) {
            throw new Error(`Failed to read file ${filename}: ${error.message}`);
        }
    }

    /**
     * Write a file asynchronously.
     * @param {string} filename - The name of the file to write.
     * @param {string} content - The content to write.
     */
    async writeFile(filename, content) {
        const fullPath = path.join(this.basePath, filename);

        try {
            await fs.promises.writeFile(fullPath, content, 'utf8');
            this.cache.set(fullPath, content);
        } catch (error) {
            throw new Error(`Failed to write file ${filename}: ${error.message}`);
        }
    }

    /**
     * Clear the cache.
     */
    clearCache() {
        this.cache.clear();
    }
}

/**
 * Process an array of numbers.
 * @param {number[]} numbers - Array of numbers to process.
 * @returns {object} Statistics about the numbers.
 */
function processNumbers(numbers) {
    if (!Array.isArray(numbers) || numbers.length === 0) {
        return { sum: 0, average: 0, max: 0, min: 0 };
    }

    const sum = numbers.reduce((acc, num) => acc + num, 0);
    const average = sum / numbers.length;
    const max = Math.max(...numbers);
    const min = Math.min(...numbers);

    return { sum, average, max, min };
}

/**
 * Main function to demonstrate functionality.
 */
async function main() {
    const fileUtil = new FileUtil('./data');
    const numbers = [1, 2, 3, 4, 5, 10, 15, 20];

    try {
        // Process numbers
        const stats = processNumbers(numbers);
        console.log('Number statistics:', stats);

        // Write results to file
        const output = JSON.stringify(stats, null, 2);
        await fileUtil.writeFile('stats.json', output);
        console.log('Results written to stats.json');

        // Read config if it exists
        try {
            const config = await fileUtil.readFile(CONFIG_FILE);
            console.log('Config loaded:', JSON.parse(config));
        } catch (error) {
            console.log('No config file found, using defaults');
        }

    } catch (error) {
        console.error('Error:', error.message);
        process.exit(1);
    }
}

// Export for testing
module.exports = { FileUtil, processNumbers };

// Run if this is the main module
if (require.main === module) {
    main().catch(console.error);
}
