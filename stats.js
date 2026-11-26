/* Digital Worlds Lab: privacy-friendly stats (GoatCounter, no cookies, no personal data).
   Counts page views (with referrer and utm_source/ref as the source) and clicks on shop links. */
(function () {
  var inFrame = window.self !== window.top;
  window.goatcounter = window.goatcounter || {};
  // Calculators embedded on other sites are counted as /embed/<page>, so they do not mix with own visits.
  if (inFrame) window.goatcounter.path = function (p) { return '/embed' + location.pathname; };
  var SHOPS = /(^|\.)(etsy\.com|gumroad\.com|whop\.com)$/;
  function track(e) {
    var a = e.target && e.target.closest ? e.target.closest('a[href]') : null;
    if (!a) return;
    var u;
    try { u = new URL(a.href, location.href); } catch (x) { return; }
    var m = u.hostname.match(SHOPS);
    if (!m) return;
    var shop = m[2].split('.')[0];
    var target = (u.pathname.match(/\/listing\/(\d+)/) || [])[1] || u.pathname.replace(/[^\w-]+/g, '-').replace(/^-|-$/g, '').slice(0, 40) || 'home';
    var ev = { path: 'out-' + shop + '-' + target + ' from ' + location.pathname, title: (a.textContent || '').trim().slice(0, 80), event: true };
    if (window.goatcounter && window.goatcounter.count) window.goatcounter.count(ev);
  }
  document.addEventListener('click', track, true);
  document.addEventListener('auxclick', track, true);
})();
