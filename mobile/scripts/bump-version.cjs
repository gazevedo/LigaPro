const fs = require('node:fs');
function bumpVersion(version) {
  for (const field of ['major', 'minor', 'patch', 'revision']) {
    if (!Number.isSafeInteger(version[field]) || version[field] < 0) throw new Error(`Invalid version field: ${field}`);
  }
  if (!Number.isSafeInteger(version.revision + 1)) throw new Error('Version revision exceeds supported range');
  return { ...version, revision: version.revision + 1 };
}
if (require.main === module) {
  const filename = require.resolve('../version.json');
  const version = bumpVersion(JSON.parse(fs.readFileSync(filename, 'utf8')));
  fs.writeFileSync(filename, JSON.stringify(version, null, 2) + '\n');
  console.log(`v${version.major}.${version.minor}.${version.patch}.${version.revision}`);
}
module.exports = { bumpVersion };
