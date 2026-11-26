/*
 * מדידה ופיקסלים: Google Analytics 4, Meta Pixel, TikTok Pixel.
 *
 * שום סקריפט של צד שלישי לא נטען לפני שהגולש אישר בבאנר העוגיות.
 * שאר האתר קורא רק ל-window.aryeTrack(event, data), והקובץ הזה מתרגם
 * את האירוע לשלוש הפלטפורמות.
 *
 * אירועים: 'view' (צפייה במוצר), 'add_to_cart', 'checkout', 'purchase'.
 * data: { items: [{id, name, price, quantity}], value, order_id }
 */
(function () {
    'use strict';

    var CONSENT_KEY = 'aryeCookieConsent';
    var CURRENCY = 'ILS';

    var EVENT_NAMES = {
        view: { ga4: 'view_item', meta: 'ViewContent', tiktok: 'ViewContent' },
        add_to_cart: { ga4: 'add_to_cart', meta: 'AddToCart', tiktok: 'AddToCart' },
        checkout: { ga4: 'begin_checkout', meta: 'InitiateCheckout', tiktok: 'InitiateCheckout' },
        purchase: { ga4: 'purchase', meta: 'Purchase', tiktok: 'CompletePayment' }
    };

    var ids = {};
    try {
        var idsElement = document.getElementById('tracking-ids');
        if (idsElement) ids = JSON.parse(idsElement.textContent) || {};
    } catch (e) {
        ids = {};
    }
    var enabled = Boolean(ids.ga4 || ids.meta || ids.tiktok);

    var pending = [];   // אירועים שנורו לפני שהגולש בחר
    var loaded = false;

    function readStorage(key) {
        try { return window.localStorage.getItem(key); } catch (e) { return null; }
    }

    function writeStorage(key, value) {
        try { window.localStorage.setItem(key, value); } catch (e) { /* גלישה פרטית */ }
    }

    function loadScript(src) {
        var script = document.createElement('script');
        script.async = true;
        script.src = src;
        document.head.appendChild(script);
    }

    function loadGa4(id) {
        window.dataLayer = window.dataLayer || [];
        window.gtag = function () { window.dataLayer.push(arguments); };
        window.gtag('js', new Date());
        window.gtag('config', id);
        loadScript('https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(id));
    }

    function loadMeta(id) {
        if (!window.fbq) {
            var fbq = window.fbq = function () {
                fbq.callMethod ? fbq.callMethod.apply(fbq, arguments) : fbq.queue.push(arguments);
            };
            if (!window._fbq) window._fbq = fbq;
            fbq.push = fbq;
            fbq.loaded = true;
            fbq.version = '2.0';
            fbq.queue = [];
            loadScript('https://connect.facebook.net/en_US/fbevents.js');
        }
        window.fbq('init', id);
        window.fbq('track', 'PageView');
    }

    function loadTikTok(id) {
        var ttq = window.ttq = window.ttq || [];
        if (!ttq.methods) {
            window.TiktokAnalyticsObject = 'ttq';
            ttq.methods = ['page', 'track', 'identify', 'instances', 'debug', 'on', 'off', 'once',
                'ready', 'alias', 'group', 'enableCookie', 'disableCookie', 'holdConsent',
                'revokeConsent', 'grantConsent'];
            ttq.setAndDefer = function (target, method) {
                target[method] = function () {
                    target.push([method].concat(Array.prototype.slice.call(arguments, 0)));
                };
            };
            ttq.methods.forEach(function (method) { ttq.setAndDefer(ttq, method); });
            ttq.load = function (pixelId) {
                var url = 'https://analytics.tiktok.com/i18n/pixel/events.js';
                ttq._i = ttq._i || {};
                ttq._i[pixelId] = [];
                ttq._i[pixelId]._u = url;
                ttq._t = ttq._t || {};
                ttq._t[pixelId] = +new Date();
                ttq._o = ttq._o || {};
                ttq._o[pixelId] = {};
                loadScript(url + '?sdkid=' + encodeURIComponent(pixelId) + '&lib=ttq');
            };
        }
        ttq.load(id);
        ttq.page();
    }

    function loadAll() {
        if (loaded) return;
        loaded = true;
        if (ids.ga4) loadGa4(ids.ga4);
        if (ids.meta) loadMeta(ids.meta);
        if (ids.tiktok) loadTikTok(ids.tiktok);
    }

    function send(event, data) {
        var names = EVENT_NAMES[event];
        if (!names) return;

        var items = (data && data.items) || [];
        var value = Number(data && data.value) || 0;
        var orderId = data && data.order_id ? String(data.order_id) : '';

        // רכישה נשלחת פעם אחת בלבד, גם אם עמוד התודה נטען שוב
        var purchaseKey = 'aryePurchaseSent:' + orderId;
        if (event === 'purchase' && orderId) {
            if (readStorage(purchaseKey)) return;
            writeStorage(purchaseKey, '1');
        }
        var eventId = orderId ? event + '-' + orderId : '';

        if (ids.ga4 && window.gtag) {
            var gaParams = {
                currency: CURRENCY,
                value: value,
                items: items.map(function (item) {
                    return { item_id: String(item.id), item_name: item.name, price: Number(item.price) || 0, quantity: item.quantity || 1 };
                })
            };
            if (orderId) gaParams.transaction_id = orderId;
            window.gtag('event', names.ga4, gaParams);
        }

        if (ids.meta && window.fbq) {
            window.fbq('track', names.meta, {
                content_type: 'product',
                content_ids: items.map(function (item) { return String(item.id); }),
                contents: items.map(function (item) { return { id: String(item.id), quantity: item.quantity || 1 }; }),
                num_items: items.reduce(function (sum, item) { return sum + (item.quantity || 1); }, 0),
                value: value,
                currency: CURRENCY
            }, eventId ? { eventID: eventId } : undefined);
        }

        if (ids.tiktok && window.ttq) {
            window.ttq.track(names.tiktok, {
                contents: items.map(function (item) {
                    return { content_id: String(item.id), content_type: 'product', content_name: item.name, quantity: item.quantity || 1, price: Number(item.price) || 0 };
                }),
                value: value,
                currency: CURRENCY
            }, eventId ? { event_id: eventId } : undefined);
        }
    }

    function track(event, data) {
        if (!enabled) return;
        var consent = readStorage(CONSENT_KEY);
        if (consent === 'granted') {
            loadAll();
            send(event, data);
        } else if (consent !== 'denied') {
            pending.push([event, data]);
        }
    }

    window.aryeTrack = track;

    /* ---------- באנר ההסכמה ---------- */

    function initBanner() {
        var banner = document.getElementById('cookie-banner');
        var settingsLinks = document.querySelectorAll('[data-cookie-settings]');
        if (!banner || !enabled) return;

        function show() { banner.hidden = false; }
        function hide() { banner.hidden = true; }

        var accept = document.getElementById('cookie-accept');
        var decline = document.getElementById('cookie-decline');

        if (accept) {
            accept.addEventListener('click', function () {
                writeStorage(CONSENT_KEY, 'granted');
                hide();
                loadAll();
                pending.splice(0).forEach(function (entry) { send(entry[0], entry[1]); });
            });
        }

        if (decline) {
            decline.addEventListener('click', function () {
                var wasGranted = readStorage(CONSENT_KEY) === 'granted';
                writeStorage(CONSENT_KEY, 'denied');
                pending.length = 0;
                hide();
                // הסקריפטים שכבר נטענו נעצרים רק בטעינה מחדש של העמוד
                if (wasGranted) window.location.reload();
            });
        }

        Array.prototype.forEach.call(settingsLinks, function (link) {
            link.hidden = false;
            link.addEventListener('click', function (e) {
                e.preventDefault();
                show();
                if (accept) accept.focus();
            });
        });

        var consent = readStorage(CONSENT_KEY);
        if (consent === 'granted') {
            loadAll();
        } else if (consent !== 'denied') {
            show();
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initBanner);
    } else {
        initBanner();
    }
})();
