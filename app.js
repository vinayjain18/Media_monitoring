const express = require("express");
const scrapeRoutes = require("./routes/scrape.routes");

const app = express();

app.use(express.json()); // Parse JSON requests
app.use("/api/scrape", scrapeRoutes);

app.get("/", (req, res) => {
    res.send("Media Monitoring running!");
});

module.exports = app;
