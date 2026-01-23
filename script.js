/* ==========================================================================
   INTERAKSI PORTFOLIO TAMA ANDREA STUDIO
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {

    // 1. NAVBAR SCROLL EFFECT
    const navbar = document.querySelector('#navbar');
    
    window.addEventListener('scroll', () => {
        if (window.scrollY > 50) {
            navbar.style.background = 'rgba(255, 255, 255, 0.95)';
            navbar.style.boxShadow = '0 4px 20px rgba(0,0,0,0.1)';
            navbar.style.height = '64px';
        } else {
            navbar.style.background = 'rgba(255, 255, 255, 0.8)';
            navbar.style.boxShadow = 'none';
            navbar.style.height = '72px';
        }
    });

    // 2. MOBILE MENU (HAMBURGER)
    const menuToggle = document.querySelector('.menu-toggle');
    const navLinksContainer = document.querySelector('.nav-links');

    if (menuToggle) {
        menuToggle.addEventListener('click', () => {
            navLinksContainer.classList.toggle('active');
            // Opsional: ganti icon saat diklik jika menggunakan lucide
            const icon = menuToggle.querySelector('i');
            if(navLinksContainer.classList.contains('active')) {
                icon.setAttribute('data-lucide', 'x');
            } else {
                icon.setAttribute('data-lucide', 'menu');
            }
            lucide.createIcons(); // Re-render icon
        });
    }

    // Tutup menu saat link diklik (untuk mobile)
    const links = document.querySelectorAll('.nav-links a');
    links.forEach(link => {
        link.addEventListener('click', () => {
            navLinksContainer?.classList.remove('active');
        });
    });

    // 3. REVEAL-ON-SCROLL ANIMATION (Intersection Observer)
    const revealElements = document.querySelectorAll('.reveal');
    
    const observerOptions = {
        threshold: 0.15,
        rootMargin: "0px 0px -50px 0px"
    };

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                // Tambahkan style inline untuk trigger animasi jika CSS belum ada
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    revealElements.forEach(el => {
        el.style.opacity = '0';
        el.style.transform = 'translateY(30px)';
        el.style.transition = 'all 0.8s cubic-bezier(0.2, 0.8, 0.2, 1)';
        observer.observe(el);
    });

    // 4. IMAGE MODAL (FITUR BARU: ZOOM GAMBAR)
    const modal = document.getElementById("imageModal");
    const modalImg = document.getElementById("imgFull");
    const captionText = document.getElementById("modal-caption");
    const closeBtn = document.querySelector(".close-modal");

    // Ambil semua gambar di dalam card portfolio
    const portfolioImages = document.querySelectorAll('.card-image img');

    portfolioImages.forEach(img => {
        img.style.cursor = 'zoom-in';
        img.onclick = function() {
            modal.style.display = "flex";
            modalImg.src = this.src;
            captionText.innerHTML = this.alt;
            document.body.style.overflow = 'hidden'; // Matikan scroll saat zoom
        }
    });

    // Tutup Modal
    if (closeBtn) {
        closeBtn.onclick = function() {
            modal.style.display = "none";
            document.body.style.overflow = 'auto';
        }
    }

    // Tutup modal jika klik di luar gambar
    window.onclick = function(event) {
        if (event.target == modal) {
            modal.style.display = "none";
            document.body.style.overflow = 'auto';
        }
    }

    // 5. SMOOTH SCROLL FOR LINKS
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth'
                });
            }
        });
    });
});
