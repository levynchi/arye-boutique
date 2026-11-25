/*
 * התאמות נגישות כלליות:
 * 1. רכיב עם role="button" שאינו <button> מופעל גם ב-Enter וברווח.
 * 2. כפתורי בחירה (בד / מידה) מדווחים לקורא מסך מה נבחר, לפי המחלקה active.
 */
(function () {
    const CHOICE_SELECTOR = '.fabric-option, .size-option, .product-options-btn';

    document.addEventListener('keydown', (event) => {
        if (event.key !== 'Enter' && event.key !== ' ') {
            return;
        }
        const target = event.target;
        if (!(target instanceof Element) || !target.matches('[role="button"]') || target.tagName === 'BUTTON') {
            return;
        }
        event.preventDefault();
        target.click();
    });

    function syncPressed(element) {
        element.setAttribute('aria-pressed', String(element.classList.contains('active')));
    }

    function syncAll(root) {
        if (root.matches && root.matches(CHOICE_SELECTOR)) {
            syncPressed(root);
        }
        if (root.querySelectorAll) {
            root.querySelectorAll(CHOICE_SELECTOR).forEach(syncPressed);
        }
    }

    function start() {
        syncAll(document.body);
        new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes') {
                    if (mutation.target.matches(CHOICE_SELECTOR)) {
                        syncPressed(mutation.target);
                    }
                } else {
                    mutation.addedNodes.forEach(syncAll);
                }
            });
        }).observe(document.body, {
            subtree: true, childList: true, attributes: true, attributeFilter: ['class'],
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', start);
    } else {
        start();
    }
})();
