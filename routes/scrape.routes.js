const express = require("express");
const router = express.Router();
const scrapeController = require("../controllers/scrape.controller");

// Route for single company scraping
router.post("/single", scrapeController.scrapeSingleCompany);

// Route for bulk scraping
router.post("/bulk", scrapeController.scrapeBulk);

module.exports = router;
