import fs from "node:fs";
import path from "node:path";

function assert(cond, msg) {
  if (!cond) throw new Error(msg);
}

const file = path.join(process.cwd(), "vercel.json");
if (fs.existsSync(file)) {
  const raw = fs.readFileSync(file, "utf8");
  const json = JSON.parse(raw);
  
  assert(json && typeof json === "object", "vercel.json must be object");
  assert(json.version === 2, "vercel.json must set version=2");
  assert(
    json.env && 
    typeof json.env.NEXT_PUBLIC_API_URL === "string" && 
    json.env.NEXT_PUBLIC_API_URL.length > 0,
    "env.NEXT_PUBLIC_API_URL must be non-empty"
  );
  
  console.log("✓ vercel.json ok");
} else {
  console.log("(i) vercel.json not present — ok");
} 