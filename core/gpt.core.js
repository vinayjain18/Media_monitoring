const fs = require("fs");
const path = require("path");
const { openai } = require("../configuration/gpt.config");

async function gptChat(companyName, text) {
  const promptFile = path.join(__dirname, "prompt.txt");
  let systemPrompt = fs.readFileSync(promptFile, "utf8");

  // Add the extra text with the dynamic companyName
  const extraText = `One last thing, Ensure the article is related to the company - ${companyName}, including its operations, products, or significant events. If the article is not related to the ${companyName}, return this JSON format - {"esg_check":"No"}.`;
  systemPrompt += `\n${extraText}`;

  const response = await openai.chat.completions.create({
    model: "gpt-4o-mini",
    messages: [
      { role: "system", content: systemPrompt },
      { role: "user", content: text },
    ],
    temperature: 0.01,
    presence_penalty: 0.5,
  });

  let content = response.choices[0].message.content;
  if (!content) {
    console.error("GPT response is empty");
    return { error: "GPT response is empty" };
  }

  try {
    content = content.replace(/```json/g, "").replace(/```/g, "");
    console.log("Parsing JSON response...");
    const jsonResponse = JSON.parse(content);

    return jsonResponse;
  } catch (error) {
    console.error("Error parsing JSON response:", error);
    return { error: "Failed to parse response as JSON" };
  }
}

module.exports = { gptChat };
