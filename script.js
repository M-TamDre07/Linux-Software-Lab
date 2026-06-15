/**
 * TAMA ANDREA — Portfolio Script v4.0
 * Muhammad Andreatama · Graphic Designer
 * ─────────────────────────────────────────────────────────────
 * Modules:
 *  1. Typewriter         — rotating phrases in hero
 *  2. Reveal             — IntersectionObserver scroll animation
 *  3. Counter            — animated number counters
 *  4. Navbar             — scroll + mobile hamburger
 *  5. Lightbox           — keyboard-accessible image zoom
 *  6. Portfolio Filter   — filter cards by category
 *  7. Dark Mode          — toggle + localStorage persist
 *  8. Scroll Progress    — progress bar at top
 *  9. Back To Top        — scroll-triggered button
 * 10. Hire Me Float      — show after scroll
 * 11. Smooth Scroll      — href="#..." anchor
 * 12. Year              — dynamic footer year
 * 13. Lucide re-render  — ensure icons render after DOM mutations
 * ─────────────────────────────────────────────────────────────
 */

'use strict';

/* ============================================================
   UTILITIES
   ============================================================ */
const $ = (sel, ctx = document) => ctx.querySelector(sel);
const $$ = (sel, ctx = document) => [...ctx.querySelectorAll(sel)];

/** requestAnimationFrame throttle */
const rafThrottle = (fn) => {
  let scheduled = false;
  return (...args) => {
    if (scheduled) return;
    scheduled = true;
    requestAnimationFrame(() => { fn(...args); scheduled = false; });
  };
};

/** Safely re-render Lucide icons (no-op if not loaded yet) */
const renderIcons = () => {
  if (window.lucide) window.lucide.createIcons();
};

/* ============================================================
   1. TYPEWRITER
   ============================================================ */
const Typewriter = {
  phrases: [
    'Branding Modern',
    'Visual Identity',
    'Desain Poster',
    'Social Media Content',
    'Logo & Identitas',
    'Creative Design',
  ],
  speed:   85,
  delSpeed:50,
  pause:   2400,
  _el: null, _idx: 0, _char: 0, _del: false, _tid: null,

  init() {
    this._el = $('#typewriter');
    if (!this._el) return;
    this._tid = setTimeout(() => this._tick(), 900);
  },

  _tick() {
    const phrase = this.phrases[this._idx];
    if (!this._del) {
      // typing forward
      this._el.textContent = phrase.slice(0, ++this._char);
      if (this._char === phrase.length) {
        this._del = true;
        this._tid = setTimeout(() => this._tick(), this.pause);
        return;
      }
      this._tid = setTimeout(() => this._tick(), this.speed);
    } else {
      // deleting
      this._el.textContent = phrase.slice(0, --this._char);
      if (this._char === 0) {
        this._del = false;
        this._idx = (this._idx + 1) % this.phrases.length;
        this._tid = setTimeout(() => this._tick(), 380);
        return;
      }
      this._tid = setTimeout(() => this._tick(), this.delSpeed);
    }
  }
};

/* ============================================================
   2. SCROLL REVEAL
   ============================================================ */
const Reveal = {
  init() {
    const els = $$('.reveal');
    if (!els.length) return;

    if (!('IntersectionObserver' in window)) {
      els.forEach(el => el.classList.add('is-visible'));
      return;
    }

    const obs = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        obs.unobserve(entry.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -48px 0px' });

    els.forEach(el => obs.observe(el));
  }
};

/* ============================================================
   3. COUNTER ANIMATION
   ============================================================ */
const Counter = {
  init() {
    const els = $$('[data-count]');
    if (!els.length || !('IntersectionObserver' in window)) return;

    const obs = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        this._run(entry.target);
        obs.unobserve(entry.target);
      });
    }, { threshold: 0.5 });

    els.forEach(el => obs.observe(el));
  },

  _run(el) {
    const target   = parseInt(el.dataset.count, 10);
    if (isNaN(target)) return;
    const duration = 1600;
    const step     = 16;
    const increment = target / (duration / step);
    let current = 0;

    const timer = setInterval(() => {
      current = Math.min(current + increment, target);
      el.textContent = Math.floor(current);
      if (current >= target) clearInterval(timer);
    }, step);
  }
};

/* ============================================================
   4. NAVBAR  — scrolled class + mobile hamburger
   ============================================================ */
const Navbar = {
  init() {
    const nav  = $('#navbar');
    const btn  = $('#menuToggle');
    const menu = $('.nav-links');
    if (!nav) return;

    // Scrolled class
    const onScroll = rafThrottle(() => {
      nav.classList.toggle('navbar--scrolled', window.scrollY > 50);
    });
    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();

    // Hamburger
    if (!btn || !menu) return;

    const open = () => {
      menu.classList.add('active');
      btn.setAttribute('aria-expanded', 'true');
      document.body.style.overflow = 'hidden';
      this._setMenuIcon(btn, 'x');
    };
    const close = () => {
      menu.classList.remove('active');
      btn.setAttribute('aria-expanded', 'false');
      document.body.style.overflow = '';
      this._setMenuIcon(btn, 'menu');
    };
    const toggle = () => menu.classList.contains('active') ? close() : open();

    btn.addEventListener('click', toggle);

    // Close on link click
    $$('a', menu).forEach(a => a.addEventListener('click', close));

    // Close on outside click
    document.addEventListener('click', e => {
      if (menu.classList.contains('active') && !nav.contains(e.target)) close();
    });

    // Close on Escape
    window.addEventListener('keydown', e => {
      if (e.key === 'Escape' && menu.classList.contains('active')) close();
    });
  },

  _setMenuIcon(btn, name) {
    const ico = $('i[data-lucide]', btn) || btn.querySelector('[data-lucide]');
    if (ico) { ico.setAttribute('data-lucide', name); renderIcons(); }
  }
};

/* ============================================================
   5. LIGHTBOX
   ============================================================ */
const Lightbox = {
  modal:    null,
  imgEl:    null,
  caption:  null,
  closeBtn: null,
  prevBtn:  null,
  nextBtn:  null,
  items:    [],  // all zoomable images [ {src, caption} ]
  current:  0,

  init() {
    this.modal   = $('#imageModal');
    this.imgEl   = $('#imgFull');
    this.caption = $('#modal-caption');
    this.closeBtn = $('#modalCloseBtn');
    this.prevBtn  = $('#modalPrev');
    this.nextBtn  = $('#modalNext');

    if (!this.modal || !this.imgEl) return;

    // Collect all zoom-able items from DOM
    this._collectItems();

    // Delegate click — catches .zoom-btn AND direct card-image img clicks
    document.addEventListener('click', e => {
      // zoom button (has data-src)
      const zBtn = e.target.closest('.zoom-btn');
      if (zBtn && zBtn.dataset.src) {
        e.preventDefault();
        const idx = this._findIndex(zBtn.dataset.src);
        this.open(idx >= 0 ? idx : 0, zBtn.dataset.src, zBtn.dataset.caption || '');
        return;
      }

      // direct img click inside .card-image
      const img = e.target.closest('.card-image img');
      if (img) {
        e.preventDefault();
        const src     = img.src;
        const cap     = img.alt || '';
        const idx     = this._findIndex(src);
        this.open(idx >= 0 ? idx : 0, src, cap);
        return;
      }

      // direct img click inside .prestasi-image
      const pImg = e.target.closest('.prestasi-image img');
      if (pImg) {
        e.preventDefault();
        const src = pImg.src;
        const cap = pImg.alt || '';
        const idx = this._findIndex(src);
        this.open(idx >= 0 ? idx : 0, src, cap);
        return;
      }
    });

    // Close button
    this.closeBtn?.addEventListener('click', () => this.close());

    // Backdrop click closes
    this.modal.addEventListener('click', e => {
      if (e.target === this.modal || e.target.classList.contains('modal-inner')) return;
      // only close if clicking the actual backdrop
    });
    this.modal.addEventListener('pointerdown', e => {
      if (e.target === this.modal) this.close();
    });

    // Nav buttons
    this.prevBtn?.addEventListener('click', () => this.go(this.current - 1));
    this.nextBtn?.addEventListener('click', () => this.go(this.current + 1));

    // Keyboard
    window.addEventListener('keydown', e => {
      if (!this.modal.classList.contains('is-open')) return;
      if (e.key === 'Escape')      this.close();
      if (e.key === 'ArrowLeft')   this.go(this.current - 1);
      if (e.key === 'ArrowRight')  this.go(this.current + 1);
    });

    // Touch swipe
    let touchX = 0;
    this.modal.addEventListener('touchstart', e => { touchX = e.touches[0].clientX; }, { passive: true });
    this.modal.addEventListener('touchend',   e => {
      const diff = touchX - e.changedTouches[0].clientX;
      if (Math.abs(diff) > 50) this.go(this.current + (diff > 0 ? 1 : -1));
    });
  },

  _collectItems() {
    // Collect from zoom-btn elements with data-src
    $$('.zoom-btn[data-src]').forEach(btn => {
      if (!this.items.find(i => i.src === btn.dataset.src)) {
        this.items.push({ src: btn.dataset.src, caption: btn.dataset.caption || '' });
      }
    });
    // Also collect portfolio/prestasi images
    $$('.card-image img, .prestasi-image.has-image img').forEach(img => {
      const src = img.getAttribute('src');
      if (src && !this.items.find(i => i.src === src)) {
        this.items.push({ src, caption: img.alt || '' });
      }
    });
  },

  _findIndex(src) {
    // Try exact src match, also check relative vs absolute
    return this.items.findIndex(item =>
      item.src === src || src.endsWith(item.src) || item.src.endsWith(src)
    );
  },

  open(idx, src, caption) {
    this.current = Math.max(0, Math.min(idx, this.items.length - 1));
    this._render(src, caption);
    this.modal.classList.add('is-open');
    this.modal.removeAttribute('aria-hidden');
    document.body.style.overflow = 'hidden';
    this.closeBtn?.focus();
    this._updateNav();
  },

  close() {
    this.modal.classList.remove('is-open');
    this.modal.setAttribute('aria-hidden', 'true');
    document.body.style.overflow = '';
    // reset src after fade-out
    setTimeout(() => { if (this.imgEl) this.imgEl.src = ''; }, 350);
  },

  go(idx) {
    if (idx < 0 || idx >= this.items.length) return;
    this.current = idx;
    const item   = this.items[this.current];
    this._render(item.src, item.caption);
    this._updateNav();
  },

  _render(src, caption) {
    if (!this.imgEl) return;
    // Quick fade swap
    this.imgEl.style.opacity = '0';
    setTimeout(() => {
      this.imgEl.src             = src;
      this.imgEl.alt             = caption;
      this.imgEl.style.opacity   = '1';
      this.imgEl.style.transition = 'opacity .25s ease';
      if (this.caption) this.caption.textContent = caption;
    }, 120);
  },

  _updateNav() {
    if (!this.prevBtn || !this.nextBtn) return;
    this.prevBtn.disabled = this.current <= 0;
    this.nextBtn.disabled = this.current >= this.items.length - 1;
    // Hide nav completely when only 1 item
    const showNav = this.items.length > 1;
    this.prevBtn.style.display = showNav ? '' : 'none';
    this.nextBtn.style.display = showNav ? '' : 'none';
  }
};

/* ============================================================
   6. PORTFOLIO FILTER
   ============================================================ */
const PortfolioFilter = {
  init() {
    const tabs  = $$('.filter-btn');
    const cards = $$('.portfolio-card');
    if (!tabs.length || !cards.length) return;

    tabs.forEach(tab => {
      tab.addEventListener('click', () => {
        // Update active tab
        tabs.forEach(t => {
          t.classList.remove('active');
          t.setAttribute('aria-selected', 'false');
        });
        tab.classList.add('active');
        tab.setAttribute('aria-selected', 'true');

        const filter = tab.dataset.filter;

        cards.forEach(card => {
          const match = filter === 'all' || card.dataset.category === filter;
          if (match) {
            card.classList.remove('hidden');
            // Re-trigger reveal if needed
            requestAnimationFrame(() => card.classList.add('is-visible'));
          } else {
            card.classList.add('hidden');
          }
        });
      });
    });
  }
};

/* ============================================================
   7. DARK MODE
   ============================================================ */
const DarkMode = {
  init() {
    const btn  = $('#theme-toggle');
    const icon = $('#theme-icon');
    if (!btn) return;

    const saved = localStorage.getItem('ta-portfolio-theme')
      || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
    this._apply(saved, icon);

    btn.addEventListener('click', () => {
      const current = document.documentElement.dataset.theme || 'light';
      const next    = current === 'dark' ? 'light' : 'dark';
      this._apply(next, icon);
      localStorage.setItem('ta-portfolio-theme', next);
    });
  },

  _apply(theme, icon) {
    document.documentElement.dataset.theme = theme;
    if (icon) {
      icon.setAttribute('data-lucide', theme === 'dark' ? 'sun' : 'moon');
      renderIcons();
    }
  }
};

/* ============================================================
   8. SCROLL PROGRESS BAR
   ============================================================ */
const ScrollProgress = {
  init() {
    const bar = $('#scroll-progress');
    if (!bar) return;

    const update = rafThrottle(() => {
      const scrollTop  = window.scrollY;
      const docHeight  = document.documentElement.scrollHeight - window.innerHeight;
      const pct        = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
      bar.style.width  = pct + '%';
    });

    window.addEventListener('scroll', update, { passive: true });
    update();
  }
};

/* ============================================================
   9. BACK TO TOP
   ============================================================ */
const BackToTop = {
  init() {
    const btn = $('#back-to-top');
    if (!btn) return;

    const onScroll = rafThrottle(() => {
      btn.classList.toggle('visible', window.scrollY > 400);
    });
    window.addEventListener('scroll', onScroll, { passive: true });

    btn.addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }
};

/* ============================================================
   10. HIRE ME FLOAT  — show after scrolling past hero
   ============================================================ */
const HireMeFloat = {
  init() {
    const el   = $('#hireMeFloat');
    const hero = $('#hero');
    if (!el || !hero) return;

    const obs = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        // Show float when hero leaves viewport
        el.style.opacity   = entry.isIntersecting ? '0' : '1';
        el.style.transform = entry.isIntersecting
          ? 'translateY(-50%) translateX(100%)'
          : 'translateY(-50%) translateX(0)';
        el.style.transition = 'opacity .4s ease, transform .4s ease';
        el.removeAttribute('aria-hidden');
      });
    }, { threshold: 0 });

    obs.observe(hero);

    // Initial state hidden
    el.style.opacity   = '0';
    el.style.transform = 'translateY(-50%) translateX(100%)';
  }
};

/* ============================================================
   11. SMOOTH SCROLL
   ============================================================ */
const SmoothScroll = {
  init() {
    document.addEventListener('click', e => {
      const a = e.target.closest('a[href^="#"]');
      if (!a) return;
      const href = a.getAttribute('href');
      if (!href || href === '#') return;
      const target = $(href);
      if (!target) return;
      e.preventDefault();
      const offset = target.getBoundingClientRect().top + window.scrollY - 80;
      window.scrollTo({ top: offset, behavior: 'smooth' });
    });
  }
};

/* ============================================================
   12. FOOTER YEAR
   ============================================================ */
const FooterYear = {
  init() {
    const el = $('#year');
    if (el) el.textContent = new Date().getFullYear();
  }
};

/* ============================================================
   BOOT — initialise all modules
   ============================================================ */
function boot() {
  DarkMode.init();       // First: apply saved theme before paint
  FooterYear.init();
  Navbar.init();
  Reveal.init();
  Counter.init();
  Typewriter.init();
  Lightbox.init();
  PortfolioFilter.init();
  ScrollProgress.init();
  BackToTop.init();
  HireMeFloat.init();
  SmoothScroll.init();

  // Re-render Lucide icons once everything is set up
  renderIcons();

  console.log('%c✦ Tama Andrea Portfolio v4.0 · Ready', 'color:#2563eb;font-weight:700;font-size:13px');
}

// Run when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
