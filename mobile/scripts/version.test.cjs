const { test } = require('node:test');
const assert = require('node:assert/strict');
const { bumpVersion } = require('./bump-version.cjs');
test('normal updates increment patch and reset hotfix to one', () => {
  assert.deepEqual(bumpVersion({ major: 1, minor: 0, patch: 31, revision: 4 }), { major: 1, minor: 0, patch: 32, revision: 1 });
});
test('hotfix updates preserve the release and increment only hotfix', () => {
  assert.deepEqual(bumpVersion({ major: 1, minor: 0, patch: 31, revision: 1 }, 'hotfix'), { major: 1, minor: 0, patch: 31, revision: 2 });
});
test('minor and major updates reset lower release fields', () => {
  const current = { major: 1, minor: 2, patch: 31, revision: 4 };
  assert.deepEqual(bumpVersion(current, 'minor'), { major: 1, minor: 3, patch: 0, revision: 1 });
  assert.deepEqual(bumpVersion(current, 'major'), { major: 2, minor: 0, patch: 0, revision: 1 });
});
test('unsupported update types and overflow are rejected', () => {
  const current = { major: 1, minor: 0, patch: 31, revision: 1 };
  assert.throws(() => bumpVersion(current, 'unknown'));
  assert.throws(() => bumpVersion({ ...current, patch: Number.MAX_SAFE_INTEGER }));
});
test('invalid version is rejected without overwriting version metadata', () => {
  assert.throws(() => bumpVersion({ major: 1, minor: 0, patch: 0, revision: -1 }));
});
