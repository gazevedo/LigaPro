const fs = require('node:fs');
function bumpVersion(version, kind = 'patch') {
  for (const field of ['major', 'minor', 'patch', 'revision']) {
    if (!Number.isSafeInteger(version[field]) || version[field] < 0) throw new Error(`Invalid version field: ${field}`);
  }
  const field = kind === 'hotfix' ? 'revision' : kind;
  if (!['major', 'minor', 'patch', 'revision'].includes(field) || kind === 'revision') throw new Error(`Invalid version update: ${kind}`);
  if (!Number.isSafeInteger(version[field] + 1)) throw new Error('Version exceeds supported range');
  const next = { ...version, [field]: version[field] + 1 };
  if (kind !== 'hotfix') next.revision = 1;
  if (kind === 'major') next.minor = 0;
  if (kind === 'major' || kind === 'minor') next.patch = 0;
  return next;
}
if (require.main === module) {
  const filename = require.resolve('../version.json');
  const version = bumpVersion(JSON.parse(fs.readFileSync(filename, 'utf8')), process.argv[2] ?? 'patch');
  fs.writeFileSync(filename, JSON.stringify(version, null, 2) + '\n');
  console.log(`v${version.major}.${version.minor}.${version.patch}.${version.revision}`);
}
module.exports = { bumpVersion };
