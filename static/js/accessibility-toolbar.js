(function () {
    function initAccessibilityToolbar() {
        const toolbar = document.getElementById('accessibility-toolbar');
        if (!toolbar) {
            return;
        }

        const toggleButton = toolbar.querySelector('#accessibility-toggle');
        const panel = toolbar.querySelector('#accessibility-panel');
        if (!toggleButton || !panel) {
            return;
        }

        const body = document.body;
        const controls = Array.from(panel.querySelectorAll('.accessibility-control'));

        const FONT_CLASSES = ['', 'accessibility-font-large', 'accessibility-font-xlarge'];
        const STORAGE_KEY = 'aryeAccessibilitySettings';

        const DEFAULT_TOGGLES = {
            highContrast: false,
            highlightLinks: false,
            textSpacing: false,
            lineHeight: false,
            textAlign: false,
            dyslexiaFont: false,
            bigCursor: false,
            tooltips: false,
            reduceMotion: false,
            hideImages: false,
            lowSaturation: false,
        };

        const TOGGLE_CONFIG = {
            highContrast: { className: 'accessibility-high-contrast', action: 'toggle-contrast' },
            highlightLinks: { className: 'accessibility-highlight-links', action: 'toggle-links' },
            textSpacing: { className: 'accessibility-text-spacing', action: 'toggle-text-spacing' },
            lineHeight: { className: 'accessibility-line-height', action: 'toggle-line-height' },
            textAlign: { className: 'accessibility-text-align', action: 'toggle-text-align' },
            dyslexiaFont: { className: 'accessibility-dyslexia-font', action: 'toggle-dyslexia-font' },
            bigCursor: { className: 'accessibility-big-cursor', action: 'toggle-big-cursor' },
            tooltips: { className: 'accessibility-tooltips', action: 'toggle-tooltips' },
            reduceMotion: { className: 'accessibility-reduce-motion', action: 'toggle-reduce-motion' },
            hideImages: { className: 'accessibility-hide-images', action: 'toggle-hide-images' },
            lowSaturation: { className: 'accessibility-low-saturation', action: 'toggle-low-saturation' },
        };

        const ACTION_TO_TOGGLE = Object.fromEntries(
            Object.entries(TOGGLE_CONFIG).map(([key, config]) => [config.action, key])
        );

        let toggles = { ...DEFAULT_TOGGLES };
        let fontIndex = 0;
        let isPanelOpen = false;

        function loadSettings() {
            try {
                const stored = localStorage.getItem(STORAGE_KEY);
                if (!stored) {
                    return;
                }
                const parsed = JSON.parse(stored);
                if (typeof parsed.fontIndex === 'number') {
                    fontIndex = Math.min(Math.max(parsed.fontIndex, 0), FONT_CLASSES.length - 1);
                }
                if (parsed.toggles) {
                    toggles = { ...DEFAULT_TOGGLES, ...parsed.toggles };
                }
            } catch (error) {
                console.warn('Unable to load accessibility settings', error);
            }
        }

        function saveSettings() {
            const payload = {
                fontIndex,
                toggles,
            };

            try {
                localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
            } catch (error) {
                console.warn('Unable to save accessibility settings', error);
            }
        }

        function applyFontClass() {
            body.classList.remove(...FONT_CLASSES.filter(Boolean));
            const className = FONT_CLASSES[fontIndex];
            if (className) {
                body.classList.add(className);
            }
            updateFontButtons();
        }

        function updateFontButtons() {
            const increaseBtn = panel.querySelector('[data-action="increase-font"]');
            const decreaseBtn = panel.querySelector('[data-action="decrease-font"]');
            const resetBtn = panel.querySelector('[data-action="reset-font"]');

            if (increaseBtn) {
                const disabled = fontIndex >= FONT_CLASSES.length - 1;
                increaseBtn.disabled = disabled;
                increaseBtn.setAttribute('aria-disabled', String(disabled));
            }

            if (decreaseBtn) {
                const disabled = fontIndex <= 0;
                decreaseBtn.disabled = disabled;
                decreaseBtn.setAttribute('aria-disabled', String(disabled));
            }

            if (resetBtn) {
                const disabled = fontIndex === 0;
                resetBtn.disabled = disabled;
                resetBtn.setAttribute('aria-disabled', String(disabled));
            }
        }

        function updateToggleButton(key) {
            const config = TOGGLE_CONFIG[key];
            if (!config) {
                return;
            }
            const button = panel.querySelector(`[data-action="${config.action}"]`);
            if (!button) {
                return;
            }
            const isActive = Boolean(toggles[key]);
            button.setAttribute('aria-pressed', String(isActive));
            button.classList.toggle('is-active', isActive);
        }

        function applyToggleStates() {
            Object.entries(TOGGLE_CONFIG).forEach(([key, config]) => {
                if (toggles[key]) {
                    body.classList.add(config.className);
                } else {
                    body.classList.remove(config.className);
                }
                updateToggleButton(key);
            });
        }

        function setFontIndex(newIndex) {
            const clamped = Math.min(Math.max(newIndex, 0), FONT_CLASSES.length - 1);
            if (clamped === fontIndex) {
                return;
            }
            fontIndex = clamped;
            applyFontClass();
            saveSettings();
        }

        function resetAllSettings() {
            fontIndex = 0;
            toggles = { ...DEFAULT_TOGGLES };
            applyFontClass();
            applyToggleStates();
            saveSettings();
        }

        function focusFirstControl() {
            const firstControl = panel.querySelector('.accessibility-control');
            if (firstControl) {
                firstControl.focus();
            } else {
                toggleButton.focus();
            }
        }

        function handleOutsideClick(event) {
            if (!isPanelOpen) {
                return;
            }

            if (!panel.contains(event.target) && event.target !== toggleButton) {
                setPanelOpen(false);
            }
        }

        function handlePanelKeyDown(event) {
            if (event.key === 'Escape') {
                event.preventDefault();
                setPanelOpen(false);
            }
        }

        function setPanelOpen(open) {
            if (open === isPanelOpen) {
                return;
            }

            isPanelOpen = open;
            toggleButton.setAttribute('aria-expanded', String(open));

            if (open) {
                panel.removeAttribute('hidden');
                panel.classList.add('is-open');
                document.addEventListener('click', handleOutsideClick);
                panel.addEventListener('keydown', handlePanelKeyDown);
                setTimeout(focusFirstControl, 0);
            } else {
                panel.setAttribute('hidden', '');
                panel.classList.remove('is-open');
                document.removeEventListener('click', handleOutsideClick);
                panel.removeEventListener('keydown', handlePanelKeyDown);
                toggleButton.focus();
            }
        }

        function handleControlClick(event) {
            const action = event.currentTarget.dataset.action;

            if (!action) {
                return;
            }

            if (action === 'increase-font') {
                setFontIndex(fontIndex + 1);
                return;
            }

            if (action === 'decrease-font') {
                setFontIndex(fontIndex - 1);
                return;
            }

            if (action === 'reset-font') {
                setFontIndex(0);
                return;
            }

            if (action === 'reset-settings') {
                resetAllSettings();
                return;
            }

            const toggleKey = ACTION_TO_TOGGLE[action];
            if (toggleKey) {
                toggles[toggleKey] = !toggles[toggleKey];
                applyToggleStates();
                saveSettings();
            }
        }

        toggleButton.addEventListener('click', event => {
            event.preventDefault();
            event.stopPropagation();
            setPanelOpen(!isPanelOpen);
        });

        controls.forEach(control => {
            control.addEventListener('click', handleControlClick);
        });

        loadSettings();
        applyFontClass();
        applyToggleStates();
        setPanelOpen(false);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAccessibilityToolbar);
    } else {
        initAccessibilityToolbar();
    }
})();

