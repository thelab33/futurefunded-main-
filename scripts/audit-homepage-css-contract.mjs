import fs from "node:fs";

const cssPath = "apps/web/app/static/css/ff.css";
const templatePath = "apps/web/app/templates/platform/index.html";

const css = fs.readFileSync(cssPath, "utf8");
const template = fs.existsSync(templatePath) ? fs.readFileSync(templatePath, "utf8") : "";

const requiredCss = [".ff-platformHero", ".ff-homeHero", ".ff-platformCard", ".ff-button"];

const missingCss = requiredCss.filter((token) => !css.includes(token));

if (missingCss.length) {
  throw new Error(`Homepage CSS contract failed. Missing CSS tokens: ${missingCss.join(", ")}`);
}

if (!template.includes("data-ff-page") && !template.includes("platform")) {
  throw new Error("Homepage CSS contract failed. Platform template markers were not found.");
}

console.log("✅ Homepage CSS contract audit passed.");
