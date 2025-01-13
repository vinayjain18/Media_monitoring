const scrapingService = require("../services/scraping.services");
const databaseService = require("../services/database.services");

// Controller for single company scraping
const scrapeSingleCompany = async (req, res) => {
  try {
    const { companyName, companyID, keyword } = req.body;

    // Step 1: Scrape data
    const scrapedData = await scrapingService.scrapeSingle(
      companyName,
      keyword
    );

    if (!scrapedData || scrapedData.length === 0) {
      return res.status(404).json({
        success: false,
        message: "No data found for the given company and keyword.",
      });
    }
    console.log("Scrapping of data is done");

    const saveResult = await databaseService.saveToDatabase(
      companyName,
      companyID,
      scrapedData
    );

    if (!saveResult.success) {
      throw new Error(saveResult.message);
    }

    // Step 3: Respond with success
    res.status(200).json({
      success: true,
      message: "Data scraped and saved successfully",
      data: scrapedData,
    });
  } catch (error) {
    console.error("Error in scrapeSingleCompany:", error.message);
    res.status(500).json({
      success: false,
      message: "An error occurred",
      error: error.message,
    });
  }
};

// Controller for bulk scraping
const scrapeBulk = async (req, res) => {
  try {
    console.log("Request body", req.body);
    const { companyName, companyId, industry } = req.body;
    console.log("scraping for company", companyId);

    const result = await scrapingService.scrapeBulk(companyName, industry);
    const scrapedData = result.data;

    const saveResult = await databaseService.saveToDatabase(
      companyName,
      companyId,
      scrapedData
    );

    if (!saveResult.success) {
      throw new Error(saveResult.message);
    }

    // Step 3: Respond with success
    res.status(200).json({
      success: true,
      message: "Data scraped and saved successfully",
      data: scrapedData,
    });
  } catch (error) {
    console.error(error);
    res.status(500).json({ success: false, message: error.message });
  }
};

module.exports = {
  scrapeSingleCompany,
  scrapeBulk,
};
