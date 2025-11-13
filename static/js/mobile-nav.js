document.addEventListener('DOMContentLoaded', () => {
    const navDrawer = document.querySelector('[data-mobile-nav]');
    const navOverlay = document.querySelector('[data-mobile-nav-overlay]');
    const navToggle = document.querySelector('[data-menu-toggle]');
    const navClose = document.querySelector('[data-mobile-nav-close]');
    const navLinks = document.querySelectorAll('[data-mobile-nav-link]');

    if (!navDrawer || !navOverlay || !navToggle) {
        return;
    }

    function openNav() {
        navDrawer.classList.add('is-active');
        navOverlay.classList.add('is-active');
        navDrawer.setAttribute('aria-hidden', 'false');
        document.body.style.overflow = 'hidden';
    }

    function closeNav() {
        navDrawer.classList.remove('is-active');
        navOverlay.classList.remove('is-active');
        navDrawer.setAttribute('aria-hidden', 'true');
        document.body.style.overflow = '';
    }

    navToggle.addEventListener('click', () => {
        if (navDrawer.classList.contains('is-active')) {
            closeNav();
        } else {
            openNav();
        }
    });

    if (navClose) {
        navClose.addEventListener('click', closeNav);
    }

    navOverlay.addEventListener('click', closeNav);

    navLinks.forEach(link => {
        link.addEventListener('click', closeNav);
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && navDrawer.classList.contains('is-active')) {
            closeNav();
        }
    });
});

