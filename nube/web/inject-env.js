const fs = require("fs");
const path = require("path");
const url = process.env.SUPABASE_URL || "";
const anonKey = process.env.SUPABASE_ANON_KEY || "";
const dest = path.join(__dirname, "config.js");
fs.writeFileSync(
  dest,
  `window.CLUB_BURGER_NUBE = { url: ${JSON.stringify(url)}, anonKey: ${JSON.stringify(anonKey)} };\n`
);
console.log("config.js listo");
