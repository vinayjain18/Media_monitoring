const { scrapeYahooNews, scrapeLinks } = require("../core/scrape.core");
const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const scrapeSingle = async (companyName, keyword) => {
  const links = await scrapeYahooNews(companyName, keyword);
  const content = await scrapeLinks(links);
  return content;
};

const scrapeBulk = async (companyName, industry) => {
  const industryKeywords = {
    Retail: require("../keywords/retail_keywords.json"),
    Automotive: require("../keywords/automotive_keywords.json"),
    Consumer_Goods: require("../keywords/consumer_keywords.json"),
    Healthcare: require("../keywords/healthcare_keywords.json"),
    Hospitality: require("../keywords/hospitality_keywords.json"),
    Real_Estate: require("../keywords/real_estate_keywords.json"),
    Telecom: require("../keywords/telecom_keywords.json"),
    Transport: require("../keywords/transport_keywords.json"),
    Metals: require("../keywords/metals_keywords.json"),
    Aerospace: require("../keywords/aerospace_keywords.json"),
    Banking: require("../keywords/banking_keywords.json"),
    Energy: require("../keywords/energy_keywords.json"),
    Fashion: require("../keywords/fashion_keywords.json"),
    Food: require("../keywords/food_keywords.json"),
    Government: require("../keywords/government_keywords.json"),
    Manufacturing: require("../keywords/manufacturing_keywords.json"),
    Media: require("../keywords/media_keywords.json"),
    Technology: require("../keywords/technology_keywords.json"),
    Default: require("../keywords/news_search_keywords.json"),
  };

  const keywords = industryKeywords[industry] || industryKeywords.Default;

  const results = [];
  const chunks = [];
  let allContent = []; // Array to store all scraped content

  // Split keywords into chunks of 3 for processing
  for (let i = 0; i < keywords.length; i += 3) {
    const chunk = keywords.slice(i, i + 3);
    chunks.push(chunk);
  }

  // Iterate over each chunk of keywords
  for (const chunk of chunks) {
    const chunkResults = await Promise.all(
      chunk.map(async (searchQuery) => {
        await delay(1000);
        const newsLinkList = await scrapeYahooNews(companyName, searchQuery);

        // If there are valid links, process them and fetch content
        if (Array.isArray(newsLinkList) && newsLinkList.length > 0) {
          const content = await scrapeLinks(
            companyName,
            newsLinkList.slice(0, 5),
            searchQuery
          ); // Scrape up to 5 links

          // If content is successfully scraped, add it to allContent
          if (content && content.length > 0) {
            allContent.push(...content); // Spread to ensure content is added correctly
          }

          return {
            companyName,
            keyword: searchQuery,
            status:
              content && content.length > 0
                ? "Data added successfully"
                : "Error occurred",
          };
        }

        // If no links found, return the status
        return {
          companyName,
          keyword: searchQuery,
          status: "No sources found",
        };
      })
    );

    results.push(...chunkResults); // Collect all chunk results
  }

  // Return both status information and scraped content as a list of JSON objects
  return {
    success: results.some(
      (result) => result.status === "Data added successfully"
    ),
    statusDetails: results,
    data: allContent,
  };
};

module.exports = {
  scrapeSingle,
  scrapeBulk,
};
