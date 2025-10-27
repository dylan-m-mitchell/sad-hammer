const fs = require("fs");
const path = require("path");
const pngToIco = require("png-to-ico");

async function run() {
  try {
    const root = path.resolve(__dirname, "..", "public");
    const png = path.join(root, "hammer_15119182.png");
    if (!fs.existsSync(png)) {
      console.error("PNG not found at", png);
      process.exit(1);
    }

    // create multi-size PNGs (16,32,48) from the provided PNG using sharp if available
    const sharpPath = path.join(__dirname, "..", "node_modules", "sharp");
    let pngs = [png];
    if (fs.existsSync(sharpPath)) {
      const sharp = require("sharp");
      const sizes = [16, 32, 48];
      pngs = [];
      for (const s of sizes) {
        const out = path.join(root, `hammer-${s}.png`);
        await sharp(png).resize(s, s).png().toFile(out);
        pngs.push(out);
        console.log("wrote", out);
      }
    }

    const icoPath = path.join(root, "favicon.ico");
    const buf = await pngToIco(pngs);
    fs.writeFileSync(icoPath, buf);
    console.log("wrote", icoPath);
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
}

run();
