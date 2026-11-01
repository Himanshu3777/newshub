// NewsHub theme: dark (black) default, light (white) toggle, remembered per device.
(function(){
  var saved = localStorage.getItem('nh-theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  document.addEventListener('DOMContentLoaded', function(){
    var btn = document.getElementById('theme-toggle');
    function label(){ btn.textContent = document.documentElement.getAttribute('data-theme') === 'light' ? '🌙 Dark' : '☀ Light'; }
    if(btn){ label(); btn.addEventListener('click', function(){
      var cur = document.documentElement.getAttribute('data-theme') === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', cur);
      localStorage.setItem('nh-theme', cur); label();
    });}
  });
})();
