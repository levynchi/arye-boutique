document.addEventListener('DOMContentLoaded', function () {
    const menu = document.querySelector('.account-menu');
    if (!menu) {
        return;
    }

    const toggle = menu.querySelector('.account-menu-toggle');
    const panel = menu.querySelector('.account-menu-panel');
    if (!toggle || !panel) {
        return;
    }

    function closeMenu() {
        panel.hidden = true;
        toggle.setAttribute('aria-expanded', 'false');
    }

    function openMenu() {
        panel.hidden = false;
        toggle.setAttribute('aria-expanded', 'true');
        const firstItem = panel.querySelector('a, button');
        if (firstItem) {
            firstItem.focus();
        }
    }

    toggle.addEventListener('click', function (event) {
        event.stopPropagation();
        if (panel.hidden) {
            openMenu();
        } else {
            closeMenu();
        }
    });

    document.addEventListener('click', function (event) {
        if (!menu.contains(event.target)) {
            closeMenu();
        }
    });

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            closeMenu();
        }
    });
});
