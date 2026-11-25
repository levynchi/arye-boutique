document.addEventListener('DOMContentLoaded', () => {
    const navDrawer = document.querySelector('[data-mobile-nav]');
    const navOverlay = document.querySelector('[data-mobile-nav-overlay]');
    const navToggle = document.querySelector('[data-menu-toggle]');
    const navClose = document.querySelector('[data-mobile-nav-close]');
    const navLinks = document.querySelectorAll('[data-mobile-nav-link]');
    const focusableSelectors = 'a[href], button:not([disabled]), input:not([disabled]), [tabindex]:not([tabindex="-1"])';

    if (!navDrawer || !navOverlay || !navToggle) {
        return;
    }

    function isOpen() {
        return navDrawer.classList.contains('is-active');
    }

    function openNav() {
        // inert מוסר לפני הפתיחה: מגירה סגורה לא נמצאת בסדר ה-Tab ולא נקראת בקורא מסך
        navDrawer.inert = false;
        navDrawer.classList.add('is-active');
        navOverlay.classList.add('is-active');
        navDrawer.setAttribute('aria-hidden', 'false');
        navToggle.setAttribute('aria-expanded', 'true');
        document.body.style.overflow = 'hidden';
        (navClose || navDrawer).focus();
    }

    function closeNav(returnFocus = true) {
        if (!isOpen()) {
            return;
        }
        navDrawer.classList.remove('is-active');
        navOverlay.classList.remove('is-active');
        navDrawer.setAttribute('aria-hidden', 'true');
        navToggle.setAttribute('aria-expanded', 'false');
        document.body.style.overflow = '';
        navDrawer.inert = true;
        if (returnFocus) {
            navToggle.focus();
        }
    }

    navToggle.addEventListener('click', () => {
        if (isOpen()) {
            closeNav();
        } else {
            openNav();
        }
    });

    if (navClose) {
        navClose.addEventListener('click', () => closeNav());
    }

    navOverlay.addEventListener('click', () => closeNav());

    // לחיצה על קישור מנווטת לדף אחר - אין צורך להחזיר את הפוקוס לכפתור התפריט
    navLinks.forEach(link => {
        link.addEventListener('click', () => closeNav(false));
    });

    // הפוקוס נשאר בתוך המגירה כל עוד היא פתוחה
    navDrawer.addEventListener('keydown', (event) => {
        if (event.key !== 'Tab') {
            return;
        }
        const focusable = Array.from(navDrawer.querySelectorAll(focusableSelectors))
            .filter(element => element.offsetParent !== null);
        if (focusable.length === 0) {
            return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
        }
    });

    document.addEventListener('keydown', (event) => {
        if (event.key === 'Escape' && isOpen()) {
            closeNav();
        }
    });
});
