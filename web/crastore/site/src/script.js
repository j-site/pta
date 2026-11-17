(function () {
  var lp = document.getElementById('crastore-lp');
  if (!lp) return;

  // mobile menu
  var menuBtn = document.getElementById('clMenuBtn');
  var gnav = document.getElementById('clGnav');
  function closeMenu() {
    if (!menuBtn || !gnav) return;
    menuBtn.classList.remove('open');
    gnav.classList.remove('open');
    menuBtn.setAttribute('aria-expanded', 'false');
    menuBtn.setAttribute('aria-label', 'メニューを開く');
  }
  if (menuBtn && gnav) {
    menuBtn.addEventListener('click', function () {
      var willOpen = !gnav.classList.contains('open');
      menuBtn.classList.toggle('open', willOpen);
      gnav.classList.toggle('open', willOpen);
      menuBtn.setAttribute('aria-expanded', willOpen ? 'true' : 'false');
      menuBtn.setAttribute('aria-label', willOpen ? 'メニューを閉じる' : 'メニューを開く');
    });
    gnav.addEventListener('click', function (e) {
      if (e.target.closest('a')) closeMenu();
    });
    document.addEventListener('click', function (e) {
      if (!gnav.classList.contains('open')) return;
      if (gnav.contains(e.target) || menuBtn.contains(e.target)) return;
      closeMenu();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeMenu();
    });
    window.addEventListener('resize', function () {
      if (window.innerWidth > 1080) closeMenu();
    });
  }

  // 著作権表記の年を自動更新
  var y = document.getElementById('clYear');
  if (y) y.textContent = new Date().getFullYear();

  // scroll reveal（JSが動いたときだけ。動かない環境では要素は最初から見えている）
  var reveals = lp.querySelectorAll('.reveal');
  var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce || !('IntersectionObserver' in window) || !reveals.length) return;
  lp.classList.add('js-on');
  Array.prototype.forEach.call(reveals, function (el) {
    if (el.getBoundingClientRect().top < window.innerHeight) el.classList.add('on');
  });
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (en.isIntersecting) { en.target.classList.add('on'); io.unobserve(en.target); }
    });
  }, { threshold: 0, rootMargin: '0px 0px -8% 0px' });
  Array.prototype.forEach.call(reveals, function (el) { io.observe(el); });
  setTimeout(function () {
    Array.prototype.forEach.call(reveals, function (el) { el.classList.add('on'); });
  }, 1500);
})();
