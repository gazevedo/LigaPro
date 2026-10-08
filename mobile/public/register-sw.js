/* Installation is available on HTTPS and localhost; registration must not block login. */
if ('serviceWorker' in navigator && window.isSecureContext) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/service-worker.js').catch(() => {
      console.warn('Não foi possível preparar a instalação do LigaPro.');
    });
  });
}
