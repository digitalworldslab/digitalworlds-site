/* Digital Worlds Lab: embeddable calculators. ?embed=1 shows a compact version for iframes;
   otherwise adds an "Embed this calculator" box with copy-paste code (iframe + credit link). */
(function () {
  var loc = window.location, embed = /[?&]embed=1/.test(loc.search);
  var canon = (document.querySelector('link[rel="canonical"]') || {}).href || (loc.origin + loc.pathname);
  var h1 = document.querySelector('h1'), name = h1 ? h1.textContent.trim() : 'Free calculator';
  var main = document.querySelector('main');
  if (!main) return;
  if (embed) {
    var css = document.createElement('style');
    css.textContent = 'main{padding:12px 12px 16px!important}.tools,.dwl-embed{display:none!important}';
    document.head.appendChild(css);
    var back = main.querySelector('p a[href="/"]'); if (back) back.parentNode.style.display = 'none';
    [].forEach.call(document.querySelectorAll('main a'), function (a) { a.target = '_blank'; a.rel = 'noopener'; });
    var c = document.createElement('p'); c.className = 'note';
    c.innerHTML = 'Free calculator by <a href="' + canon + '?utm_source=embed&utm_medium=iframe" target="_blank" rel="noopener">Digital Worlds Lab</a>';
    main.appendChild(c);
    return;
  }
  var code = '<iframe src="' + canon + '?embed=1" title="' + name.replace(/"/g, '') + '" width="100%" height="900" style="border:0;max-width:760px" loading="lazy"></iframe>\n' +
    '<p style="font-size:13px"><a href="' + canon + '">' + name + '</a> by Digital Worlds Lab</p>';
  var box = document.createElement('details'); box.className = 'card dwl-embed';
  box.innerHTML = '<summary>Embed this calculator on your blog or website (free)</summary>' +
    '<p class="note">Copy the code below into any page. It stays free, updates automatically and needs no sign-up. Please keep the credit link.</p>' +
    '<textarea readonly rows="4" style="width:100%;font:13px monospace;background:#160f28;color:#fff;border:1px solid #3d2f63;border-radius:8px;padding:8px"></textarea>' +
    '<p><button type="button" class="pill">Copy code</button></p>';
  box.querySelector('textarea').value = code;
  box.querySelector('button').onclick = function () {
    var t = box.querySelector('textarea'); t.select();
    try { navigator.clipboard.writeText(t.value); } catch (e) { document.execCommand('copy'); }
    this.textContent = 'Copied';
  };
  var tools = main.querySelector('.tools');
  if (tools) main.insertBefore(box, tools); else main.appendChild(box);
})();
