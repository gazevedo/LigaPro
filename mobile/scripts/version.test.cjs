const { test } = require('node:test');
const assert = require('node:assert/strict');
const { bumpVersion } = require('./bump-version.cjs');
test('normal updates increment patch in a three-part version', () => {
  assert.deepEqual(bumpVersion({ major: 1, minor: 0, patch: 31 }), { major: 1, minor: 0, patch: 32 });
});
test('minor and major updates reset lower release fields', () => {
  const current = { major: 1, minor: 2, patch: 31 };
  assert.deepEqual(bumpVersion(current, 'minor'), { major: 1, minor: 3, patch: 0 });
  assert.deepEqual(bumpVersion(current, 'major'), { major: 2, minor: 0, patch: 0 });
});
test('unsupported update types and overflow are rejected', () => {
  const current = { major: 1, minor: 0, patch: 31 };
  assert.throws(() => bumpVersion(current, 'unknown'));
  assert.throws(() => bumpVersion(current, 'hotfix'));
  assert.throws(() => bumpVersion({ ...current, patch: Number.MAX_SAFE_INTEGER }));
});
test('invalid version is rejected without overwriting version metadata', () => {
  assert.throws(() => bumpVersion({ major: 1, minor: 0, patch: -1 }));
});
