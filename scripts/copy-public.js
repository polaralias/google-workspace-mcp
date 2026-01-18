const fs = require("fs/promises");
const path = require("path");

async function main() {
  const srcDir = path.join(__dirname, "..", "src", "public");
  const destDir = path.join(__dirname, "..", "dist", "public");

  await fs.mkdir(destDir, { recursive: true });
  await fs.cp(srcDir, destDir, { recursive: true });
}

main().catch((err) => {
  console.error("Failed to copy public assets", err);
  process.exit(1);
});
