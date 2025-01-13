// const puppeteer = require("puppeteer");
const axios = require("axios");
const { gptChat } = require("./gpt.core");
const cheerio = require("cheerio");
const puppeteer = require("puppeteer-extra");
const StealthPlugin = require("puppeteer-extra-plugin-stealth");
puppeteer.use(StealthPlugin());

const pLimit = require("p-limit").default;

/**
 * Scrape Yahoo News search results for a given company and keyword
 */
async function scrapeYahooNews(companyName, keyword) {
  let browser = null;
  try {
    browser = await puppeteer.launch({
      headless: true,
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-extensions",
        "--start-maximized",
        "--disable-blink-features=AutomationControlled",
      ],
    });
    const page = await browser.newPage();

    // Randomize User-Agent
    const userAgents = [
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Safari/605.1.15",
      // Add more User-Agent strings here
    ];
    const userAgent = userAgents[Math.floor(Math.random() * userAgents.length)];
    await page.setUserAgent(userAgent);

    // Set viewport
    await page.setViewport({ width: 1280, height: 800 });
    
    // Set longer timeout and enable request interception
    page.setDefaultNavigationTimeout(30000); // Increased timeout to 60 seconds
    await page.setRequestInterception(true);

    // Optimize page loading
    page.on("request", (request) => {
      if (["image", "stylesheet", "font"].includes(request.resourceType())) {
        request.abort();
      } else {
        request.continue();
      }
    });

    // const words = companyName.split(" ");
    // const initials = words.map(w => w[0]).join(". ");
    // const dynamicQuery = [
    //     `"${companyName}"`,          // Full name
    //     ...words.map(w => `"${w}"`),  // Each word
    //     `"${initials}"`,         // Abbreviated initials
    // ].join(" OR ");

    const keywordParts = keyword.split(" ");
    const keywordQuery = keywordParts.join(" OR ");

    await page.goto("https://search.yahoo.com/", { waitUntil: "networkidle0" });
    // await page.goto("https://www.google.com/", { waitUntil: "networkidle0" });
    await page.type("#yschsp", `"${companyName}" AND (${keywordQuery}) negative news`);
    // await page.type("#APjFqb", `${companyName} ${keyword}`);
    await page.keyboard.press("Enter");
    await new Promise(r => setTimeout(r, 5000))
    // Wait for either selector with timeout handling
    try {
      await page.waitForSelector(".algo-sr", { timeout: 10000 });
      // await page.waitForSelector(".yuRUbf", { timeout: 10000 }); // Increased timeout to 20 seconds
    } catch (error) {
      console.warn(
        "Primary selector not found, moving to next one..."
      );
      // try {
      //   await page.waitForSelector(".searchCenterMiddle", { timeout: 10000 }); // Increased timeout to 10 seconds
      // } catch (error) {
      //   console.error("Alternative selector also not found.");
      //   return []; // Return an empty array if both selectors fail
      // }
    }

    const links = await page.evaluate(() => {
      const anchors = document.querySelectorAll(
        ".algo-sr a, .searchCenterMiddle a"
      );
      // const anchors = document.querySelectorAll(
      //   ".yuRUbf a, .searchCenterMiddle a"
      // );
      return Array.from(anchors)
        .map((anchor) => anchor.href)
        // .filter((href) => href && !href.includes("yahoo.com/search"));
    });

    if (links.length === 0) {
      console.log("No valid links found on the page");
    }

    return links.slice(0, 5);
  } catch (error) {
    console.error(`Error scraping Yahoo News: ${error.message}`);
    return []; // Return an empty array in case of an error
  } finally {
    if (browser) await browser.close();
  }
}
/**
 * Fetch page content using axios with browser-like headers and timeout
 */
async function fetchPageContent(link) {
  try {
    const response = await axios.get(link, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        Accept:
          "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
      },
    });
    return response.data;
  } catch (error) {
    console.error(`Failed to fetch content for ${link}: ${error.message}`);
    return null;
  }
}
/**
 * Fetch content using Puppeteer with improved error handling
 */
async function fetchContentWithPuppeteer(link) {
  try {
    console.log(`Pupetter scraping the link now: ${link}`);
    const browser = await puppeteer.launch({
      headless: true,
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-extensions",
        "--start-maximized",
        "--disable-blink-features=AutomationControlled",
      ],
    });
    const page = await browser.newPage();
    const customUA =
      "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36";
    await page.setUserAgent(customUA);
    await page.goto(link, { timeout: 15000 });
    const content = await page.evaluate(() => document.body.textContent);
    await browser.close();
    return content;
  } catch (error) {
    console.error(
      `Puppeteer failed to fetch content for ${link}: ${error.message}`
    );
    return null;
  }
}
/**
 * Fetch content using Cheerio with improved error handling
 */
async function fetchContentWithCheerio(link) {
  try {
    const response = await axios.get(link);
    const $ = cheerio.load(response.data);

    $("script").remove();
    $("style").remove();

    // Extract text from body, removing extra whitespace
    const content = $("body")
      .text() // Get text content
      .replace(/\s+/g, " ") // Replace multiple spaces with single space
      .replace(/\n+/g, "\n") // Replace multiple newlines with single newline
      .trim(); // Remove leading/trailing whitespace

    return content;
  } catch (error) {
    console.error(
      `Cheerio failed to fetch content for ${link}: ${error.message}`
    );
    return null;
  }
}
/**
 * Process scraped links with improved error handling and validation
 */
async function scrapeLinks(companyName, links, searchQuery, concurrency = 6) {
  const limit = pLimit(concurrency);
  const results = [];

  const tasks = links.map((link) =>
    limit(async () => {
      try {
        // Attempt to fetch page content with Puppeteer
        let pageContent = await fetchContentWithCheerio(link);

        if (!pageContent) {
          console.warn(
            `Fetching with Cherio failed for ${link}, switching with Puppeteer...`
          );
          pageContent = await fetchContentWithPuppeteer(link);
        }

        if (!pageContent) throw new Error("Content fetch failed");

        // Pass the content to GPT for processing
        let output = await gptChat(companyName, pageContent);
        output.link = link;
        output.phrase = searchQuery;

        // Add output to results
        console.log(output);
        if (output.categories && output.categories.length > 0) {
          results.push({ ...output });
        } else {
          console.warn(
            `No categories found for link: ${link}. Skipping this link...`
          );
        }
      } catch (error) {
        console.error(
          `Failed to process link: ${link}. Error: ${error.message}`
        );
        results.push({ link, error: error.message });
      }
    })
  );

  // Wait for all tasks to complete
  await Promise.all(tasks);

  return results;
}
module.exports = { scrapeYahooNews, scrapeLinks };
