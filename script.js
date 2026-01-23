/**
 * TAMA ANDREA STUDIO - Portfolio Core Interaction
 * Version: 2.0.0
 */

"use strict";

const PortfolioApp = (() => {
    // --- Configuration ---
    const CONFIG = {
        navbarScrollThreshold: 50,
        revealThreshold: 0.15,
        revealMargin: "0px 0px -50px 0px"
    };

    // --- Selectors ---
    const UI = {
        navbar: document.querySelector('#navbar'),
        menuToggle: document.querySelector('.menu-toggle'),
        navLinksContainer: document.querySelector('.nav-links'),
        navLinks: document.querySelectorAll('.nav-links a'),
        revealElements: document.querySelectorAll('.reveal'),
        modal: document.getElementById("imageModal"),
        modalImg: document.getElementById("imgFull"),
        modalCaption: document.getElementById("modal-caption"),
        closeModal: document.querySelector(".close-modal"),
        portfolioImages: document.querySelectorAll('.card-image img')
    };

    // --- Helpers ---
    // Mencegah fungsi dijalankan terlalu sering (Optimasi Performa)
    const throttle = (callback, limit) => {
        let wait = false;
        return () => {
            if (!wait) {
                callback.call();
                wait = true;
                setTimeout(() => wait = false, limit);
            }
        };
    };

    // --- Modules ---

    const initNavbar = () => {
        if (!UI.navbar) return;

        const handleScroll = () => {
            const isScrolled = window.scrollY > CONFIG.navbarScrollThreshold;
            // Gunakan class CSS daripada inline style agar lebih ringan
            UI.navbar.classList.toggle('navbar--scrolled', isScrolled);
        };

        window.addEventListener('scroll', throttle(handleScroll, 100));
    };

    const initMobileMenu = () => {
        if (!UI.menuToggle) return;

        const toggleMenu = (forceClose = false) => {
            const isOpen = forceClose ? false : UI.navLinksContainer.classList.toggle('active');
            if (forceClose) UI.navLinksContainer.classList.remove('active');

            // Update Icon (Lucide support)
            const icon = UI.menuToggle.querySelector('i');
            if (icon) {
                icon.setAttribute('data-lucide', isOpen ? 'x' : 'menu');
                if (window.lucide) lucide.createIcons();
            }
            
            // Lock body scroll saat menu buka
            document.body.style.overflow = isOpen ? 'hidden' : '';
        };

        UI.menuToggle.addEventListener('click', () => toggleMenu());
        
        // Tutup menu saat link diklik
        UI.navLinks.forEach(link => {
            link.addEventListener('click', () => toggleMenu(true));
        });
    };

    const initRevealAnimation = () => {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    observer.unobserve(entry.target);
                }
            });
        }, { threshold: CONFIG.revealThreshold, rootMargin: CONFIG.revealMargin });

        UI.revealElements.forEach(el => observer.observe(el));
    };

    const initImageModal = () => {
        if (!UI.modal) return;

        const openModal = (img) => {
            UI.modal.style.display = "flex";
            UI.modalImg.src = img.src;
            UI.modalCaption.textContent = img.alt;
            document.body.classList.add('modal-open');
        };

        const closeModal = () => {
            UI.modal.style.display = "none";
            document.body.classList.remove('modal-open');
        };

        UI.portfolioImages.forEach(img => {
            img.addEventListener('click', () => openModal(img));
        });

        UI.closeModal?.addEventListener('click', closeModal);
        
        // Tutup saat klik background atau tekan Esc
        window.addEventListener('click', (e) => { if (e.target === UI.modal) closeModal(); });
        window.addEventListener('keydown', (e) => { if (e.key === "Escape") closeModal(); });
    };

    const initSmoothScroll = () => {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                e.preventDefault();
                const targetId = this.getAttribute('href');
                if (targetId === '#') return;
                
                const target = document.querySelector(targetId);
                if (target) {
                    target.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            });
        });
    };

    // --- Entry Point ---
    const init = () => {
        initNavbar();
        initMobileMenu();
        initRevealAnimation();
        initImageModal();
        initSmoothScroll();
    };

    return { init };
})();

// Jalankan aplikasi saat DOM siap
document.addEventListener('DOMContentLoaded', PortfolioApp.init);
