import { shouldSwipeBack } from '../components/SwipeBack';
test('right swipe from the left edge goes back', () => {
  expect(shouldSwipeBack(8, 80, 10)).toBe(true);
});
test('vertical scrolls, table swipes and left swipes do not trigger back', () => {
  expect(shouldSwipeBack(8, 10, 80)).toBe(false);
  expect(shouldSwipeBack(150, 80, 0)).toBe(false);
  expect(shouldSwipeBack(8, -80, 0)).toBe(false);
});
