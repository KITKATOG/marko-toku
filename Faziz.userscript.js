// ==UserScript==
// @name         Arbpay Sniper v5.0 [BRUTAL]
// @namespace    http://tampermonkey.net/
// @version      5.0.0
// @description  Neo-brutalist GUI, zero spam, triple-fire click
// @author       Anas
// @match        https://arbpay.cc/*
// @grant        none
// ==/UserScript==

(function () {
    'use strict';

    /* ═══════════════ CONFIG ═══════════════ */
    const TARGET_NUMBER  = '';
    const TARGET_PASS    = '';
    const CLICK_COOLDOWN = 60;
    const PURCHASE_RESET = 400;
    const STEALTH_MS     = 500;

    let isStarted      = false;
    let isPurchased    = false;
    let isMinimized    = false;
    let hasReachedPage = false;
    let lastClickTime  = 0;
    let rafId          = null;
    let lockedTarget   = localStorage.getItem('arbTarget') || '';

    let scanCount    = 0;
    let totalHits    = 0;
    let totalBought  = 0;
    let lastRateTS   = 0;

    const isMobile = /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
    const DIGIT_RE  = /\D/g;

    /* ═══════════════ HELPERS ═══════════════ */
    function setInputValue(input, value) {
        if (!input) return;
        const setter = Object.getOwnPropertyDescriptor(
            window.HTMLInputElement.prototype, 'value'
        )?.set;
        setter ? setter.call(input, value) : (input.value = value);
        input.dispatchEvent(new Event('input',  { bubbles: true }));
        input.dispatchEvent(new Event('change', { bubbles: true }));
    }

    function simulateClick(el) {
        if (!el) return;
        ['pointerdown','mousedown','pointerup','mouseup','click'].forEach(ev =>
            el.dispatchEvent(new (ev.startsWith('pointer') ? PointerEvent : MouseEvent)(ev, { bubbles: true, cancelable: true }))
        );
        el.click?.();
    }

    /* ═══════════════ NOTIFY ═══════════════ */
    const recentMsgs = new Map();

    function notify(msg, type = 'info') {
        const now = Date.now();
        if (now - (recentMsgs.get(msg) || 0) < 1500) return;
        recentMsgs.set(msg, now);

        let box = document.getElementById('anas-notify');
        if (!box) {
            box = document.createElement('div');
            box.id = 'anas-notify';
            Object.assign(box.style, {
                position: 'fixed', bottom: '14px', left: '14px',
                zIndex: 2e7, display: 'flex', flexDirection: 'column-reverse', gap: '6px',
                pointerEvents: 'none',
            });
            document.body.appendChild(box);
        }
        while (box.children.length >= 3) box.lastChild?.remove();

        const colors = {
            success: { bg: '#AAFF00', fg: '#000' },
            error:   { bg: '#FF3B3B', fg: '#fff' },
            warn:    { bg: '#FFE600', fg: '#000' },
            info:    { bg: '#C8B4FF', fg: '#000' },
        };
        const { bg, fg } = colors[type] || colors.info;

        const t = document.createElement('div');
        Object.assign(t.style, {
            padding: '7px 12px',
            background: bg,
            color: fg,
            border: '2px solid #000',
            boxShadow: '3px 3px 0 #000',
            fontFamily: '"Space Grotesk", "Archivo Black", sans-serif',
            fontSize: '11px',
            fontWeight: '700',
            textTransform: 'uppercase',
            letterSpacing: '0.06em',
            transform: 'translateY(8px)',
            opacity: '0',
            transition: 'all 0.12s cubic-bezier(.17,.67,.35,1.3)',
        });
        t.textContent = msg;
        box.prepend(t);
        requestAnimationFrame(() => {
            t.style.transform = 'translateY(0)';
            t.style.opacity = '1';
        });
        setTimeout(() => {
            t.style.opacity = '0';
            t.style.transform = 'translateY(6px)';
            setTimeout(() => t.remove(), 150);
        }, 2500);
    }

    /* ═══════════════ LOGIN / NAV ═══════════════ */
    function handleLogin() {
        if (!isStarted || hasReachedPage) return;
        const pass = document.querySelector('input[type=password]');
        if (!pass || pass.value) return;
        const tel = document.querySelector('input[type=tel]') || document.querySelector('input[type=text]');
        if (!tel) return;
        notify('Logging in', 'info');
        setInputValue(tel, TARGET_NUMBER);
        setInputValue(pass, TARGET_PASS);
        setTimeout(() => {
            const btn = document.querySelector('button.van-button--primary');
            btn && simulateClick(btn);
        }, 250);
    }

    function handleNavigation() {
        if (!isStarted || isPurchased) return;
        if (location.hash.includes('#/home')) {
            document.querySelectorAll('.x-home-nav .item')
                .forEach(i => i.textContent.includes('Buy') && simulateClick(i));
        }
        if (location.hash.includes('#/buy')) {
            const tab = [...document.querySelectorAll('.van-tab')]
                .find(t => t.textContent.includes('OTP-UPI'));
            if (tab && !tab.classList.contains('van-tab--active')) simulateClick(tab);
            else hasReachedPage = true;
        }
    }

    /* ═══════════════ DRAG ═══════════════ */
    function makeDraggable(el) {
        const handle = el.querySelector('.drag-handle');
        let sx = 0, sy = 0, sl = 0, st = 0;
        handle.addEventListener('pointerdown', e => {
            e.preventDefault();
            handle.setPointerCapture(e.pointerId);
            sx = e.clientX; sy = e.clientY;
            sl = el.offsetLeft; st = el.offsetTop;
            const move = ev => {
                el.style.left = sl + (ev.clientX - sx) + 'px';
                el.style.top  = st + (ev.clientY - sy) + 'px';
                el.style.right = 'auto';
            };
            const up = () => {
                handle.releasePointerCapture(e.pointerId);
                document.removeEventListener('pointermove', move);
                document.removeEventListener('pointerup', up);
            };
            document.addEventListener('pointermove', move, { passive: true });
            document.addEventListener('pointerup', up);
        }, { passive: false });
    }

    /* ═══════════════ GUI ═══════════════ */
    function injectAssets() {
        if (document.getElementById('anas-assets')) return;
        const s = document.createElement('style');
        s.id = 'anas-assets';
        s.textContent = `
            @import url('https://fonts.googleapis.com/css2?family=Archivo+Black&family=Space+Grotesk:wght@400;500;700&display=swap');

            #anas-gui {
                position: fixed;
                top: 70px;
                right: 14px;
                width: 210px;
                background: #C8B4FF;
                border: 3px solid #000;
                box-shadow: 6px 6px 0 #000;
                font-family: 'Space Grotesk', sans-serif;
                user-select: none;
                touch-action: none;
                z-index: 999999;
                transition: box-shadow 0.1s;
            }
            #anas-gui:active { box-shadow: 3px 3px 0 #000; }

            #anas-gui .g-header {
                background: #000;
                color: #C8B4FF;
                padding: 8px 12px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                cursor: grab;
                font-family: 'Archivo Black', sans-serif;
                font-size: 13px;
                letter-spacing: 0.08em;
                text-transform: uppercase;
            }
            #anas-gui .g-header:active { cursor: grabbing; }

            #anas-gui .g-header-right {
                display: flex;
                align-items: center;
                gap: 8px;
            }

            #anas-gui .g-badge {
                background: #AAFF00;
                color: #000;
                font-size: 8px;
                font-weight: 700;
                letter-spacing: 0.1em;
                padding: 2px 6px;
                border: 1px solid #000;
                text-transform: uppercase;
            }

            #anas-gui #g-min {
                color: #C8B4FF;
                font-size: 18px;
                line-height: 1;
                cursor: pointer;
                font-family: 'Archivo Black', sans-serif;
            }

            #anas-gui .g-body {
                padding: 12px;
            }

            #anas-gui .g-section-label {
                font-size: 8px;
                font-weight: 700;
                letter-spacing: 0.15em;
                text-transform: uppercase;
                color: #000;
                margin-bottom: 5px;
                opacity: 0.5;
            }

            #anas-gui #g-price {
                width: 100%;
                padding: 10px 8px;
                border: 3px solid #000;
                background: #fff;
                font-family: 'Archivo Black', sans-serif;
                font-size: 26px;
                text-align: center;
                color: #000;
                outline: none;
                box-shadow: 3px 3px 0 #000;
                margin-bottom: 10px;
                transition: box-shadow 0.1s, transform 0.1s;
            }
            #anas-gui #g-price:focus {
                box-shadow: 2px 2px 0 #000;
                transform: translate(1px, 1px);
            }
            #anas-gui #g-price::placeholder { color: #ccc; }

            #anas-gui .g-stats {
                display: grid;
                grid-template-columns: 1fr 1fr 1fr;
                gap: 6px;
                margin-bottom: 10px;
            }
            #anas-gui .g-stat {
                background: #FFE600;
                border: 2px solid #000;
                box-shadow: 2px 2px 0 #000;
                padding: 6px 4px;
                text-align: center;
            }
            #anas-gui .g-stat-val {
                font-family: 'Archivo Black', sans-serif;
                font-size: 16px;
                color: #000;
                line-height: 1;
            }
            #anas-gui .g-stat-lbl {
                font-size: 7px;
                font-weight: 700;
                letter-spacing: 0.1em;
                text-transform: uppercase;
                color: #000;
                opacity: 0.5;
                margin-top: 2px;
            }

            #anas-gui .g-status-bar {
                background: #fff;
                border: 2px solid #000;
                padding: 5px 8px;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.1em;
                text-transform: uppercase;
                color: #000;
                display: flex;
                align-items: center;
                gap: 6px;
                margin-bottom: 10px;
                box-shadow: 2px 2px 0 #000;
            }
            #anas-gui .g-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                border: 2px solid #000;
                background: #ccc;
                flex-shrink: 0;
            }
            #anas-gui .g-dot.live {
                background: #AAFF00;
                animation: brutal-blink 0.8s steps(1) infinite;
            }
            @keyframes brutal-blink {
                0%, 100% { opacity: 1; }
                50% { opacity: 0; }
            }

            #anas-gui #g-toggle {
                width: 100%;
                padding: 12px 8px;
                border: 3px solid #000;
                background: #AAFF00;
                color: #000;
                font-family: 'Archivo Black', sans-serif;
                font-size: 14px;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                cursor: pointer;
                box-shadow: 4px 4px 0 #000;
                transition: box-shadow 0.08s, transform 0.08s;
            }
            #anas-gui #g-toggle:active {
                box-shadow: 1px 1px 0 #000;
                transform: translate(3px, 3px);
            }
            #anas-gui #g-toggle.running {
                background: #FF3B3B;
                color: #fff;
            }

            /* Decorative corner marks */
            #anas-gui .g-corner {
                position: absolute;
                width: 8px;
                height: 8px;
                border: 2px solid #000;
                pointer-events: none;
            }
            #anas-gui .g-corner.tl { top: -2px; left: -2px; border-right: none; border-bottom: none; }
            #anas-gui .g-corner.tr { top: -2px; right: -2px; border-left: none; border-bottom: none; }
            #anas-gui .g-corner.bl { bottom: -2px; left: -2px; border-right: none; border-top: none; }
            #anas-gui .g-corner.br { bottom: -2px; right: -2px; border-left: none; border-top: none; }
        `;
        document.head.appendChild(s);
    }

    function createGUI() {
        if (document.getElementById('anas-gui')) return;
        injectAssets();

        const gui = document.createElement('div');
        gui.id = 'anas-gui';
        gui.innerHTML = `
            <div class="g-corner tl"></div>
            <div class="g-corner tr"></div>
            <div class="g-corner bl"></div>
            <div class="g-corner br"></div>

            <div class="drag-handle g-header">
                <span class="g-title">ANAS SNIPER</span>
                <div class="g-header-right">
                    <span class="g-badge">v5</span>
                    <span id="g-min">−</span>
                </div>
            </div>

            <div id="g-body" class="g-body">

                <div class="g-section-label">Target amount</div>
                <input id="g-price" type="number" placeholder="0000" value="${lockedTarget}" />

                <div class="g-status-bar">
                    <span class="g-dot" id="g-dot"></span>
                    <span id="g-status-text">STANDBY</span>
                </div>

                <div class="g-stats">
                    <div class="g-stat">
                        <div class="g-stat-val" id="gs-rate">0</div>
                        <div class="g-stat-lbl">scan/s</div>
                    </div>
                    <div class="g-stat">
                        <div class="g-stat-val" id="gs-hits">0</div>
                        <div class="g-stat-lbl">found</div>
                    </div>
                    <div class="g-stat" style="background:#FF3B3B;">
                        <div class="g-stat-val" id="gs-bought" style="color:#fff;">0</div>
                        <div class="g-stat-lbl" style="color:#fff;">bought</div>
                    </div>
                </div>

                <button id="g-toggle">START</button>
            </div>
        `;

        document.body.appendChild(gui);
        makeDraggable(gui);

        const priceInput = gui.querySelector('#g-price');
        const dot        = gui.querySelector('#g-dot');
        const statusText = gui.querySelector('#g-status-text');
        const toggleBtn  = gui.querySelector('#g-toggle');
        const minBtn     = gui.querySelector('#g-min');
        const body       = gui.querySelector('#g-body');

        priceInput.oninput = () => {
            lockedTarget = priceInput.value;
            localStorage.setItem('arbTarget', lockedTarget);
        };

        toggleBtn.onclick = () => {
            isStarted = !isStarted;
            isPurchased = false;

            if (isStarted) {
                toggleBtn.textContent = 'STOP';
                toggleBtn.classList.add('running');
                dot.classList.add('live');
                statusText.textContent = 'RUNNING';
                notify('Armed ' + (lockedTarget ? '₹' + lockedTarget : '— set target'), 'success');
                startRAF();
            } else {
                toggleBtn.textContent = 'START';
                toggleBtn.classList.remove('running');
                dot.classList.remove('live');
                statusText.textContent = 'STANDBY';
                notify('Stopped', 'warn');
                stopRAF();
            }
        };

        minBtn.onclick = () => {
            isMinimized = !isMinimized;
            body.style.display = isMinimized ? 'none' : 'block';
            minBtn.textContent = isMinimized ? '+' : '−';
        };
    }

    function updateStats() {
        const r = document.getElementById('gs-rate');
        const h = document.getElementById('gs-hits');
        const b = document.getElementById('gs-bought');
        if (r) r.textContent = scanCount;
        if (h) h.textContent = totalHits;
        if (b) b.textContent = totalBought;
        scanCount = 0;
        lastRateTS = Date.now();
    }

    /* ═══════════════ SNIPER ═══════════════ */
    function runSniper() {
        if (!isStarted || !location.hash.includes('#/buy')) return;
        if (!lockedTarget) return;

        const now = Date.now();
        scanCount++;
        if (now - lastRateTS >= 1000) updateStats();
        if (now - lastClickTime < CLICK_COOLDOWN) return;

        const rows = document.querySelectorAll('.item.mb32');
        for (const r of rows) {
            const amtEl = r.querySelector('.amount');
            if (!amtEl) continue;
            if (amtEl.textContent.replace(DIGIT_RE, '') !== lockedTarget) continue;

            const btn = r.querySelector('button');
            if (!btn || btn.disabled) continue;

            totalHits++;
            lastClickTime = now;
            notify('Found ₹' + lockedTarget, 'success');

            // Triple-fire
            simulateClick(btn);
            setTimeout(() => !btn.disabled && simulateClick(btn), 30);
            setTimeout(() => !btn.disabled && simulateClick(btn), 80);

            totalBought++;
            isPurchased = true;
            setTimeout(() => (isPurchased = false), PURCHASE_RESET);
            break;
        }
    }

    /* ═══════════════ RAF ═══════════════ */
    function rafLoop() {
        runSniper();
        if (isStarted) rafId = requestAnimationFrame(rafLoop);
    }
    function startRAF() {
        stopRAF();
        lastRateTS = Date.now(); scanCount = 0;
        rafId = requestAnimationFrame(rafLoop);
    }
    function stopRAF() {
        if (rafId) { cancelAnimationFrame(rafId); rafId = null; }
    }

    /* ═══════════════ BOOT ═══════════════ */
    setInterval(() => {
        createGUI();
        if (!isStarted) return;
        handleLogin();
        handleNavigation();
    }, STEALTH_MS);

})();
