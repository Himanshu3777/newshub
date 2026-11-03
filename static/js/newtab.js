/* Story links open in a new tab (like the big news portals) so the reader
   never loses the homepage / listing they were browsing. Navigation links -
   home, categories, /news/ listing, pagination - stay in the same tab. */
(function () {
  "use strict";
  var STORY = /^\/news\/[^/?#]+\/?$/;
  function mark(root) {
    (root || document).querySelectorAll('a[href^="/news/"]').forEach(function (a) {
      if (STORY.test(a.getAttribute("href"))) {
        a.target = "_blank";
        a.rel = "noopener";
      }
    });
  }
  document.addEventListener("DOMContentLoaded", function () {
    mark(document);
    /* Live headline updates inject fresh links - mark those too. */
    new MutationObserver(function (muts) {
      muts.forEach(function (m) {
        m.addedNodes.forEach(function (n) { if (n.nodeType === 1) mark(n); });
      });
    }).observe(document.body, { childList: true, subtree: true });
  });
})();
