const mysql = require("mysql2/promise");
const dbConfig = require("../configuration/database.config");
const pool = mysql.createPool(dbConfig);

async function validateRecord(record, index) {
  const requiredFields = [
    "sentiment",
    "summary",
    "categories",
    "incidents",
    "date",
    "link",
    "phrase",
    "themes",
    "country",
  ];

  const missingFields = requiredFields.filter((field) => !record[field]);

  if (missingFields.length > 0) {
    return {
      isValid: false,
      error: `Missing required fields: ${missingFields.join(", ")} in record ${
        index + 1
      }`,
    };
  }

  return { isValid: true };
}

async function saveToDatabase(companyName, companyId = "C000000001", records) {
  let connection;

  console.log(
    "Starting database operation with",
    Array.isArray(records) ? records.length : 1,
    "records",
    "for company",
    companyId
  );
  let successCount = 0;
  let errorCount = 0;
  let errorDetails = [];

  // Convert single record to array for consistent processing
  const recordsArray = Array.isArray(records) ? records : [records];

  try {
    connection = await pool.getConnection();
    console.log("Database connection established");
    await connection.beginTransaction();
    console.log("Transaction started");

    for (let i = 0; i < recordsArray.length; i++) {
      const record = recordsArray[i];
      try {
        console.log(`Processing record ${i + 1}/${recordsArray.length}`);

        // Validate record fields
        // const validation = await validateRecord(record, i);
        // if (!validation.isValid) {
        //   throw new Error(validation.error);
        // }

        // Extract fields from the record using the new format
        const sentiment = record.sentiment;
        const summary = record.summary;
        const category = record.categories;
        const incidents = record.incidents;
        const publishedDate = record.date;
        const link = record.link;
        const keywordsPhrases = record.phrase;
        const themes = Array.isArray(record.themes)
          ? JSON.stringify(record.themes)
          : (record.themes);
        const country = record.country;

        // Check if country exists
        console.log(`Processing country: ${country}`);
        const [countryRows] = await connection.execute(
          "SELECT id FROM d_countries WHERE LOWER(country) = LOWER(?)",
          [country]
        );

        let countryId;
        if (countryRows.length === 0) {
          console.log(`Creating new country entry for: ${country}`);
          const [result] = await connection.execute(
            "INSERT INTO d_countries (country) VALUES (?)",
            [country.charAt(0).toUpperCase() + country.slice(1).toLowerCase()]
          );
          countryId = result.insertId;
          console.log(`Created new country with ID: ${countryId}`);
        } else {
          countryId = countryRows[0].id;
          console.log(`Found existing country ID: ${countryId}`);
        }

        // Insert main record
        console.log("Inserting main record into d_media_monitor_details");
        const [mediaResult] = await connection.execute(
          `INSERT INTO d_media_monitor_details 
           (company_id, Sentiment, Summary, Category, 
            Incident, Published_dt, link, Keywords_phrases, Themes, 
            country, proc_ts) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          [
            companyId,
            sentiment,
            summary,
            category,
            incidents,
            publishedDate,
            link,
            keywordsPhrases,
            themes,
            country,
            new Date().toISOString().slice(0, 19).replace("T", " "),
          ]
        );

        const incidentId = mediaResult.insertId;
        console.log(`Created media monitor record with ID: ${incidentId}`);

        // Process categories
        console.log("Processing categories");
        const categoryMap = {
          Environmental: 1,
          Social: 2,
          Governance: 3,
        };

        const categoryId = categoryMap[category];
        if (categoryId) {
          console.log(
            `Inserting theme relationship with category ID: ${categoryId}`
          );
          await connection.execute(
            "INSERT INTO d_incidents_themes (incident_id, theme_id) VALUES (?, ?)",
            [incidentId, categoryId]
          );
        }

        // Insert incident-country relationship
        console.log("Creating incident-country relationship");
        await connection.execute(
          "INSERT INTO d_incidents_countries (incident_id, country_id) VALUES (?, ?)",
          [incidentId, countryId]
        );

        await connection.commit();
        console.log(`Successfully processed and committed record ${i + 1}`);
        successCount++;
      } catch (recordError) {
        errorCount++;
        errorDetails.push({
          record: i + 1,
          error: recordError.message,
          data: record,
        });
        console.error(`Error processing record ${i + 1}:`, recordError.message);

        // Rollback the current record's transaction
        await connection.rollback();

        // Continue with the next record
        continue;
      }

      // Start a new transaction for the next record
      await connection.beginTransaction();
    }

    // Final status report
    const summary = {
      success: successCount > 0,
      message:
        successCount > 0
          ? "Database operation completed"
          : "All records failed",
      details: {
        totalRecords: recordsArray.length,
        successfulRecords: successCount,
        failedRecords: errorCount,
        errors: errorDetails,
      },
    };

    console.log("Operation Summary:", JSON.stringify(summary, null, 2));
    return summary;
  } catch (error) {
    if (connection) {
      console.log("Error occurred, rolling back transaction");
      await connection.rollback();
      console.log("Rollback completed");
    }

    const errorSummary = {
      success: false,
      message: error.message,
      details: {
        totalRecords: recordsArray.length,
        successfulRecords: successCount,
        failedRecords: errorCount,
        errors: errorDetails,
      },
    };

    console.error("Operation Failed:", JSON.stringify(errorSummary, null, 2));
    return errorSummary;
  } finally {
    if (connection) {
      connection.release();
      console.log("Database connection released");
    }
  }
}

module.exports = { saveToDatabase };
