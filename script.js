/**
 * TAMA ANDREA STUDIO — Portfolio Core Interaction
 * Version: 3.0.0
 */

"use strict";

const PortfolioApp = (() => {

    // --- Configuration ---
    const CONFIG = {
        navbarScrollThreshold: 50,
        revealThreshold: 0.15,
        revealMargin: "0px 0px -50px 0px",
        backToTopThreshold: 400,
        typewriterPhrases: [
            "Branding Modern",
            "Visual Identity",
            "Desain Poster",
            "Social Media Content",
            "Logo & Identitas"
        ],
        typewriterSpeed: 90,
        typewriterDeleteSpeed: 55,
        typewriterPause: 2200
    };

    // --- Selectors (resolved after DOMContentLoaded) ---
    let UI = {};

    const resolveUI = () => {
        UI = {
            navbar:             document.querySelector('#navbar'),
            menuToggle:         document.querySelector('.menu-toggle'),
            navLinksContainer:  document.querySelector('.nav-links'),
            navLinks:           document.querySelectorAll('.nav-links a'),
            revealElements:     document.querySelectorAll('.reveal'),
            modal:              document.getElementById('imageModal'),
            modalImg:           document.getElementById('imgFull'),
            modalCaption:       document.getElementById('modal-caption'),
            closeModal:         document.querySelector('.close-modal'),
            portfolioImages:    document.querySelectorAll('.card-image img'),
            themeToggle:        document.getElementById('theme-toggle'),
            themeIcon:          document.getElementById('theme-icon'),
            scrollProgress:     document.getElementById('scroll-progress'),
            backToTop:          document.getElementById('back-to-top'),
            typewriterEl:       document.getElementById('typewriter')
        };
    };

    // --- Helpers ---
    const throttle = (callback, limit) => {
        let wait = false;
        return (...args) => {
            if (!wait) {
                callback.apply(null, args);
                wait = true;
                setTimeout(() => { wait = false; }, limit);
            }
        };
    };

    // --- Module: Navbar Scroll Effect ---
    const initNavbar = () => {
        if (!UI.navbar) return;

        const handleScroll = () => {
            UI.navbar.classList.toggle('navbar--scrolled', window.scrollY > CONFIG.navbarScrollThreshold);
        };

        window.addEventListener('scroll', throttle(handleScroll, 100));
        handleScroll(); // Run on load
    };

    // --- Module: Mobile Menu (Hamburger) ---
    const initMobileMenu = () => {
        if (!UI.menuToggle || !UI.navLinksContainer) return;

        const toggleMenu = (forceClose = false) => {
            const willBeOpen = forceClose ? false : !UI.navLinksContainer.classList.contains('active');

            UI.navLinksContainer.classList.toggle('active', willBeOpen);
            document.body.style.overflow = willBeOpen ? 'hidden' : '';

            const icon = UI.menuToggle.querySelector('i');
            if (icon) {
                icon.setAttribute('data-lucide', willBeOpen ? 'x' : 'menu');
                if (window.lucide) lucide.createIcons();
            }
        };

        UI.menuToggle.addEventListener('click', () => toggleMenu());

        // Close menu when a nav link is clicked
        UI.navLinks.forEach(link => {
            link.addEventListener('click', () => toggleMenu(true));
        });
    };

    // --- Module: Reveal on Scroll ---
    const initRevealAnimation = () => {
        if (!UI.revealElements.length) return;

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: CONFIG.revealThreshold,
            rootMargin: CONFIG.revealMargin
        });

        UI.revealElements.forEach(el => observer.observe(el));
    };

    // --- Module: Image Lightbox Modal ---
    const initImageModal = () => {
        if (!UI.modal || !UI.modalImg) return;

        const openModal = (img) => {
            UI.modal.style.display = 'flex';
            UI.modalImg.src = img.src;
            if (UI.modalCaption) UI.modalCaption.textContent = img.alt;
            document.body.classList.add('modal-open');
        };

        const closeModal = () => {
            UI.modal.style.display = 'none';
            document.body.classList.remove('modal-open');
        };

        UI.portfolioImages.forEach(img => {
            img.addEventListener('click', () => openModal(img));
        });

        UI.closeModal?.addEventListener('click', closeModal);
        window.addEventListener('click', (e) => { if (e.target === UI.modal) closeModal(); });
        window.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeModal(); });
    };

    // --- Module: Smooth Scroll ---
    const initSmoothScroll = () => {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const targetId = this.getAttribute('href');
                if (targetId === '#') return;
                const target = document.querySelector(targetId);
                if (target) target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            });
        });
    };

    // --- Module: Dark Mode Toggle ---
    const initDarkMode = () => {
        if (!UI.themeToggle) return;

        // Load saved preference, default to light
        const savedTheme = localStorage.getItem('tama-theme') || 'light';
        applyTheme(savedTheme, false); // no icon re-create on first load (lucide does it after)

        UI.themeToggle.addEventListener('click', () => {
            const current = document.documentElement.getAttribute('data-theme') || 'light';
            const next = current === 'dark' ? 'light' : 'dark';
            applyTheme(next, true);
            localStorage.setItem('tama-theme', next);
        });
    };

    const applyTheme = (theme, reCreateIcons = true) => {
        document.documentElement.setAttribute('data-theme', theme);
        if (UI.themeIcon) {
            UI.themeIcon.setAttribute('data-lucide', theme === 'dark' ? 'sun' : 'moon');
            if (reCreateIcons && window.lucide) lucide.createIcons();
        }
    };

    // --- Module: Scroll Progress Bar + Back to Top Visibility ---
    const initScrollProgress = () => {
        const update = () => {
            const scrollTop = window.scrollY;
            const docHeight = document.documentElement.scrollHeight - window.innerHeight;

            // Update progress bar
            if (UI.scrollProgress) {
                const progress = docHeight > 0 ? (scrollTop / docHeight) * 100 : 0;
                UI.scrollProgress.style.width = `${progress}%`;
            }

            // Show/hide back-to-top
            if (UI.backToTop) {
                UI.backToTop.classList.toggle('visible', scrollTop > CONFIG.backToTopThreshold);
            }
        };

        window.addEventListener('scroll', throttle(update, 40));
        update(); // Initial run
    };

    // --- Module: Back to Top Button ---
    const initBackToTop = () => {
        if (!UI.backToTop) return;
        UI.backToTop.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    };

    // --- Module: Typewriter Effect ---
    const initTypewriter = () => {
        const el = UI.typewriterEl;
        if (!el) return;

        const phrases = CONFIG.typewriterPhrases;
        let phraseIndex = 0;
        let charIndex = 0;
        let isDeleting = false;
        let timer = null;

        const tick = () => {
            const current = phrases[phraseIndex];

            if (!isDeleting) {
                // Typing forward
                el.textContent = current.slice(0, charIndex + 1);
                charIndex++;

                if (charIndex === current.length) {
                    // Fully typed — pause before deleting
                    isDeleting = true;
                    timer = setTimeout(tick, CONFIG.typewriterPause);
                    return;
                }
                timer = setTimeout(tick, CONFIG.typewriterSpeed);

            } else {
                // Deleting
                el.textContent = current.slice(0, charIndex - 1);
                charIndex--;

                if (charIndex === 0) {
                    // Fully deleted — move to next phrase
                    isDeleting = false;
                    phraseIndex = (phraseIndex + 1) % phrases.length;
                    timer = setTimeout(tick, 400); // brief pause before next word
                    return;
                }
                timer = setTimeout(tick, CONFIG.typewriterDeleteSpeed);
            }
        };

        // Start after slight delay so page load feels smooth
        timer = setTimeout(tick, 1200);
    };

    // --- Entry Point ---
    const init = () => {
        resolveUI();
        initNavbar();
        initMobileMenu();
        initRevealAnimation();
        initImageModal();
        initSmoothScroll();
        initDarkMode();
        initScrollProgress();
        initBackToTop();
        initTypewriter();
    };

    return { init };

})();

// Boot when DOM is ready
document.addEventListener('DOMContentLoaded', PortfolioApp.init);
