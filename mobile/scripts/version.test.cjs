const { test } = require('node:test');
const assert = require('node:assert/strict');
const { bumpVersion } = require('./bump-version.cjs');
test('automatic updates increment revision while keeping release version', () => {
  assert.deepEqual(bumpVersion({ major: 1, minor: 0, patch: 0, revision: 9 }), { major: 1, minor: 0, patch: 0, revision: 10 });
});
test('invalid version is rejected without overwriting version metadata', () => {
  assert.throws(() => bumpVersion({ major: 1, minor: 0, patch: 0, revision: -1 }));
});
