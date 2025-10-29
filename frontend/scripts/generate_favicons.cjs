const fs = require("fs");
const path = require("path");
const sharp = require("sharp");
const pngToIco = require("png-to-ico");

(async () => {
  try {
    const root = path.resolve(__dirname, "..", "public");
    const svgPath = path.join(root, "favicon.svg");
    const svg = fs.readFileSync(svgPath);

    const sizes = [16, 32, 64];
    const pngPaths = [];
    for (const s of sizes) {
      const out = path.join(root, `favicon-${s}.png`);
      await sharp(svg).resize(s, s).png().toFile(out);
      pngPaths.push(out);
      console.log("wrote", out);
    }

    // create favicon.ico from PNGs
    const icoPath = path.join(root, "favicon.ico");
    const toIco =
      typeof pngToIco === "function" ? pngToIco : pngToIco.default || pngToIco;
    const buf = await toIco(pngPaths);
    fs.writeFileSync(icoPath, buf);
    console.log("wrote", icoPath);
  } catch (err) {
    console.error(err);
    process.exit(1);
  }
})();
