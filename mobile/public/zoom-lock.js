/* Keep touch controls at their designed scale without affecting single-finger scrolling. */
if (window.matchMedia('(pointer: coarse)').matches) {
  for (const type of ['gesturestart', 'gesturechange']) {
    document.addEventListener(type, event => event.preventDefault(), { passive: false });
  }
  document.addEventListener('touchmove', event => {
    if (event.touches.length > 1) event.preventDefault();
  }, { passive: false });
}
