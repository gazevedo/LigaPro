const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');
function worker() {
  const handlers = {}, notifications = [], opened = [];
  const self = { addEventListener: (type, handler) => { handlers[type] = handler; }, registration: { showNotification: async (...args) => { notifications.push(args); } }, clients: { openWindow: async url => { opened.push(url); } } };
  vm.runInNewContext(readFileSync(require.resolve('../public/service-worker.js'), 'utf8'), { self, URL, encodeURIComponent });
  return { handlers, notifications, opened };
}
test('push displays a match reminder while the app is closed', async () => {
  const w = worker(); let pending;
  const id = '0123456789abcdef01234567';
  w.handlers.push({ data: { json: () => ({ title: 'LigaPro', body: 'Partida em 5 minutos', match_id: id }) }, waitUntil: promise => { pending = promise; } });
  await pending;
  assert.equal(w.notifications[0][1].tag, `match-${id}`);
  assert.equal(w.notifications[0][1].data.matchId, id);
  w.handlers.notificationclick({ notification: { close() {}, data: { matchId: id } }, waitUntil: promise => { pending = promise; } });
  await pending;
  assert.equal(w.opened[0], `/?matchReminder=${id}`);
});
test('invalid payloads do not display notifications or open external URLs', () => {
  const w = worker();
  w.handlers.push({ data: { json: () => ({ match_id: 'https://evil.example' }) }, waitUntil() { throw new Error('unexpected push'); } });
  w.handlers.notificationclick({ notification: { close() {}, data: {} }, waitUntil() { throw new Error('unexpected URL'); } });
  assert.equal(w.notifications.length, 0);
  assert.equal(w.opened.length, 0);
});
