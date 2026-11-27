/* ==========================================================================
   PlanIt — shared interface behaviour
   Progressive enhancement only: every form and link still works without JS.
   ========================================================================== */
(function () {
    'use strict';

    var root = document.documentElement;
    var $ = function (selector, scope) { return (scope || document).querySelector(selector); };
    var $$ = function (selector, scope) { return Array.prototype.slice.call((scope || document).querySelectorAll(selector)); };
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function store(key, value) {
        try {
            if (value === undefined) { return localStorage.getItem(key); }
            if (value === null) { localStorage.removeItem(key); } else { localStorage.setItem(key, value); }
        } catch (error) { return null; }
        return null;
    }

    function iconSvg(name, size) {
        size = size || 16;
        return '<svg class="icon" width="' + size + '" height="' + size + '" aria-hidden="true"><use href="#i-' + name + '"></use></svg>';
    }

    function isTyping(target) {
        return target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName));
    }

    /* ---------------- Toasts ---------------- */

    var toastRegion = $('#toast-region');
    var TONE_ICON = { success: 'check', danger: 'alert-circle', warning: 'alert-triangle', accent: 'bell', info: 'info' };

    function dismissToast(toast) {
        if (!toast || toast.classList.contains('is-leaving')) { return; }
        toast.classList.add('is-leaving');
        setTimeout(function () { toast.remove(); }, reduceMotion ? 0 : 200);
    }

    function armToast(toast, timeout) {
        var timer = setTimeout(function () { dismissToast(toast); }, timeout || 5000);
        toast.addEventListener('mouseenter', function () { clearTimeout(timer); });
        toast.addEventListener('mouseleave', function () {
            timer = setTimeout(function () { dismissToast(toast); }, 2500);
        });
    }

    function showToast(message, options) {
        if (!toastRegion) { return; }
        options = options || {};
        var tone = options.tone || 'success';
        var toast = document.createElement('div');
        toast.className = 'toast tone-' + tone;

        var icon = document.createElement('span');
        icon.className = 'toast-icon';
        icon.innerHTML = iconSvg(options.icon || TONE_ICON[tone] || 'check', 14);

        var content = document.createElement('div');
        content.className = 'toast-content';
        if (options.title) {
            var title = document.createElement('p');
            title.className = 'toast-title';
            title.textContent = options.title;
            content.appendChild(title);
        }
        var text = document.createElement('p');
        text.className = 'toast-message';
        text.textContent = message;
        content.appendChild(text);
        if (options.href) {
            var link = document.createElement('a');
            link.className = 'toast-action';
            link.href = options.href;
            link.textContent = options.linkText || 'View';
            content.appendChild(link);
        }

        var close = document.createElement('button');
        close.type = 'button';
        close.className = 'icon-btn toast-close';
        close.setAttribute('aria-label', 'Dismiss');
        close.innerHTML = iconSvg('x', 14);
        close.addEventListener('click', function () { dismissToast(toast); });

        toast.appendChild(icon);
        toast.appendChild(content);
        toast.appendChild(close);
        toastRegion.appendChild(toast);

        var toasts = $$('.toast:not(.is-leaving)', toastRegion);
        if (toasts.length > 3) { dismissToast(toasts[0]); }
        armToast(toast, options.timeout);
        return toast;
    }

    window.PlanIt = { toast: showToast };

    $$('.toast[data-autodismiss]').forEach(function (toast) { armToast(toast, 5000); });
    document.addEventListener('click', function (event) {
        var close = event.target.closest('[data-toast-close]');
        if (close) { dismissToast(close.closest('.toast')); }
    });

    /* Flash messages carried across a redirect (client-side only). */
    var FLASH_KEY = 'planit-flash';

    function setFlash(message, path) {
        if (!message) { return; }
        try {
            sessionStorage.setItem(FLASH_KEY, JSON.stringify({ message: message, path: path || location.pathname, at: Date.now() }));
        } catch (error) { /* ignore */ }
    }

    (function consumeFlash() {
        try {
            var raw = sessionStorage.getItem(FLASH_KEY);
            if (!raw) { return; }
            sessionStorage.removeItem(FLASH_KEY);
            var flash = JSON.parse(raw);
            if (flash.path === location.pathname && Date.now() - flash.at < 15000) {
                showToast(flash.message);
            }
        } catch (error) { /* ignore */ }
    })();

    /* ---------------- Theme ---------------- */

    function syncThemeLabels() {
        var dark = root.getAttribute('data-theme') === 'dark';
        $$('[data-theme-label]').forEach(function (label) {
            label.textContent = dark ? 'Light mode' : 'Dark mode';
        });
        $$('[data-theme-toggle]').forEach(function (button) {
            button.setAttribute('aria-pressed', dark ? 'true' : 'false');
        });
    }

    syncThemeLabels();

    document.addEventListener('click', function (event) {
        var toggle = event.target.closest('[data-theme-toggle]');
        if (!toggle) { return; }
        var next = root.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        root.classList.add('theme-transition');
        root.setAttribute('data-theme', next);
        store('planit-theme', next);
        syncThemeLabels();
        setTimeout(function () { root.classList.remove('theme-transition'); }, 320);
    });

    /* ---------------- Sidebar ---------------- */

    var shell = $('#app-shell');
    var navOpenButton = $('[data-nav-open]');

    function setNav(open) {
        if (!shell) { return; }
        shell.classList.toggle('nav-open', open);
        if (navOpenButton) { navOpenButton.setAttribute('aria-expanded', open ? 'true' : 'false'); }
        document.body.style.overflow = open ? 'hidden' : '';
        if (open) {
            var first = $('.sidebar .nav-item');
            if (first) { first.focus({ preventScroll: true }); }
        }
    }

    document.addEventListener('click', function (event) {
        if (event.target.closest('[data-nav-open]')) { setNav(true); }
        if (event.target.closest('[data-nav-close]')) { setNav(false); }
        if (event.target.closest('[data-sidebar-toggle]')) {
            var collapsed = root.getAttribute('data-sidebar') === 'collapsed';
            if (collapsed) {
                root.removeAttribute('data-sidebar');
                store('planit-sidebar', 'expanded');
            } else {
                root.setAttribute('data-sidebar', 'collapsed');
                store('planit-sidebar', 'collapsed');
            }
            hideTooltip();
        }
    });

    window.matchMedia('(min-width: 1024px)').addEventListener('change', function (query) {
        if (query.matches) { setNav(false); }
    });

    /* ---------------- Tooltips ---------------- */

    var tooltip = null;
    var tooltipTimer = null;

    function sidebarIsRail() {
        return root.getAttribute('data-sidebar') === 'collapsed' && window.innerWidth >= 1024;
    }

    function showTooltip(target) {
        var text = target.getAttribute('data-tooltip');
        if (!text) { return; }
        var inSidebar = !!target.closest('.sidebar');
        if (inSidebar && !sidebarIsRail() && !target.classList.contains('sidebar-collapse')) { return; }
        if (window.matchMedia('(hover: none)').matches) { return; }

        if (!tooltip) {
            tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            tooltip.setAttribute('role', 'tooltip');
            document.body.appendChild(tooltip);
        }
        tooltip.textContent = text;
        tooltip.classList.remove('is-visible');

        var rect = target.getBoundingClientRect();
        var tipRect = tooltip.getBoundingClientRect();
        var top;
        var left;
        if (inSidebar) {
            top = rect.top + rect.height / 2 - tipRect.height / 2;
            left = rect.right + 10;
        } else {
            top = rect.bottom + 8;
            left = rect.left + rect.width / 2 - tipRect.width / 2;
            left = Math.max(8, Math.min(left, window.innerWidth - tipRect.width - 8));
        }
        tooltip.style.top = top + 'px';
        tooltip.style.left = left + 'px';
        requestAnimationFrame(function () { tooltip.classList.add('is-visible'); });
    }

    function hideTooltip() {
        clearTimeout(tooltipTimer);
        if (tooltip) { tooltip.classList.remove('is-visible'); }
    }

    document.addEventListener('mouseover', function (event) {
        var target = event.target.closest('[data-tooltip]');
        if (!target) { return; }
        clearTimeout(tooltipTimer);
        tooltipTimer = setTimeout(function () { showTooltip(target); }, 350);
    });
    document.addEventListener('mouseout', function (event) {
        if (event.target.closest('[data-tooltip]')) { hideTooltip(); }
    });
    document.addEventListener('focusin', function (event) {
        var target = event.target.closest('[data-tooltip]');
        if (target && target.matches(':focus-visible')) { showTooltip(target); }
    });
    document.addEventListener('focusout', hideTooltip);
    window.addEventListener('scroll', hideTooltip, { passive: true });

    /* ---------------- Dropdowns ---------------- */

    function closeDropdowns(except) {
        $$('[data-dropdown].is-open').forEach(function (dropdown) {
            if (dropdown === except) { return; }
            dropdown.classList.remove('is-open');
            var trigger = $('[data-dropdown-trigger]', dropdown);
            if (trigger) { trigger.setAttribute('aria-expanded', 'false'); }
        });
    }

    document.addEventListener('click', function (event) {
        var trigger = event.target.closest('[data-dropdown-trigger]');
        if (trigger) {
            var dropdown = trigger.closest('[data-dropdown]');
            var open = !dropdown.classList.contains('is-open');
            closeDropdowns(dropdown);
            dropdown.classList.toggle('is-open', open);
            trigger.setAttribute('aria-expanded', open ? 'true' : 'false');
            if (open) {
                var firstItem = $('[role="menuitem"]', dropdown);
                if (firstItem && event.detail === 0) { firstItem.focus(); }
            }
            return;
        }
        if (!event.target.closest('[data-dropdown-menu]')) { closeDropdowns(); }
    });

    document.addEventListener('keydown', function (event) {
        var menu = event.target.closest && event.target.closest('[data-dropdown-menu]');
        if (!menu || (event.key !== 'ArrowDown' && event.key !== 'ArrowUp')) { return; }
        event.preventDefault();
        var items = $$('[role="menuitem"]', menu);
        var index = items.indexOf(document.activeElement);
        var next = event.key === 'ArrowDown' ? index + 1 : index - 1;
        items[(next + items.length) % items.length].focus();
    });

    /* ---------------- Dialogs ---------------- */

    function openModal(dialog) {
        if (!dialog || dialog.open) { return; }
        closeDropdowns();
        setNav(false);
        dialog.classList.remove('is-closing');
        if (typeof dialog.showModal === 'function') { dialog.showModal(); } else { dialog.setAttribute('open', ''); }
    }

    function closeModal(dialog) {
        if (!dialog || !dialog.open || dialog.classList.contains('is-closing')) { return; }
        if (reduceMotion) { dialog.close(); return; }
        dialog.classList.add('is-closing');
        setTimeout(function () {
            dialog.classList.remove('is-closing');
            dialog.close();
        }, 170);
    }

    $$('dialog.modal').forEach(function (dialog) {
        dialog.addEventListener('cancel', function (event) {
            event.preventDefault();
            closeModal(dialog);
        });
        dialog.addEventListener('click', function (event) {
            if (event.target === dialog) { closeModal(dialog); }
            if (event.target.closest('[data-modal-close]')) { closeModal(dialog); }
        });
    });

    /* New-task dialog */
    var taskModal = $('#task-modal');

    function toLocalInput(date) {
        var pad = function (n) { return String(n).padStart(2, '0'); };
        return date.getFullYear() + '-' + pad(date.getMonth() + 1) + '-' + pad(date.getDate()) +
            'T' + pad(date.getHours()) + ':' + pad(date.getMinutes());
    }

    function openTaskModal(due) {
        if (!taskModal) { return; }
        var form = $('form', taskModal);
        var dueInput = $('[data-due-input]', taskModal);
        if (due && dueInput) { dueInput.value = due; }
        openModal(taskModal);
        setTimeout(function () { $('[name="title"]', form).focus(); }, 30);
    }

    document.addEventListener('click', function (event) {
        var opener = event.target.closest('[data-open-task-modal]');
        if (opener) {
            event.preventDefault();
            openTaskModal(opener.getAttribute('data-due'));
        }

        var preset = event.target.closest('[data-due-preset]');
        if (preset) {
            var scope = preset.closest('form') || document;
            var input = $('[data-due-input]', scope);
            if (!input) { return; }
            var date = new Date();
            var kind = preset.getAttribute('data-due-preset');
            if (kind === 'today') {
                date.setHours(Math.max(date.getHours() + 1, 18), 0, 0, 0);
                if (date.getDate() !== new Date().getDate()) { date = new Date(); date.setHours(23, 30, 0, 0); }
            } else if (kind === 'tomorrow') {
                date.setDate(date.getDate() + 1);
                date.setHours(9, 0, 0, 0);
            } else if (kind === 'week') {
                date.setDate(date.getDate() + ((8 - date.getDay()) % 7 || 7));
                date.setHours(9, 0, 0, 0);
            }
            input.value = toLocalInput(date);
            input.dispatchEvent(new Event('change', { bubbles: true }));
        }
    });

    if (taskModal) {
        taskModal.addEventListener('keydown', function (event) {
            if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
                event.preventDefault();
                var form = $('form', taskModal);
                if (form.requestSubmit) { form.requestSubmit(); } else { form.submit(); }
            }
        });
    }

    /* ---------------- Confirmations, async forms, loading states ---------------- */

    var confirmModal = $('#confirm-modal');
    var pendingConfirm = null;

    function askConfirm(form, submitter) {
        if (!confirmModal) { return false; }
        $('#confirm-title', confirmModal).textContent = form.getAttribute('data-confirm-title') || 'Are you sure?';
        $('#confirm-message', confirmModal).textContent = form.getAttribute('data-confirm');
        $('[data-confirm-label]', confirmModal).textContent = form.getAttribute('data-confirm-label') || 'Delete';
        pendingConfirm = { form: form, submitter: submitter };
        openModal(confirmModal);
        setTimeout(function () { $('[data-modal-close]', confirmModal).focus(); }, 30);
        return true;
    }

    if (confirmModal) {
        $('[data-confirm-accept]', confirmModal).addEventListener('click', function () {
            var pending = pendingConfirm;
            pendingConfirm = null;
            closeModal(confirmModal);
            if (!pending) { return; }
            pending.form.dataset.confirmed = 'true';
            if (pending.form.requestSubmit) {
                pending.form.requestSubmit(pending.submitter && pending.submitter.form === pending.form ? pending.submitter : undefined);
            } else {
                pending.form.submit();
            }
        });
    }

    var progressBar = $('#progress-bar');

    function startProgress() {
        if (!progressBar) { return; }
        progressBar.classList.remove('is-active');
        void progressBar.offsetWidth;
        progressBar.classList.add('is-active');
    }

    function setLoading(button, loading) {
        if (!button) { return; }
        button.classList.toggle('is-loading', loading);
        if (loading) { button.setAttribute('aria-busy', 'true'); } else { button.removeAttribute('aria-busy'); }
    }

    function submitAsync(form, submitter) {
        var check = $('.task-check', form);
        if (check) { check.classList.add('is-checking'); }
        setLoading(submitter, true);
        startProgress();

        fetch(form.action, {
            method: 'POST',
            body: new FormData(form),
            credentials: 'same-origin',
            redirect: 'manual',
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        }).then(function (response) {
            if (response.type === 'opaqueredirect' || response.ok) {
                setFlash(form.getAttribute('data-flash'), location.pathname);
                var row = form.closest('[data-task-id], .notification-item');
                if (row && form.hasAttribute('data-confirm') && !reduceMotion) {
                    row.style.opacity = '0';
                    row.style.transform = 'translateX(12px)';
                    setTimeout(function () { location.reload(); }, 180);
                } else {
                    setTimeout(function () { location.reload(); }, check && !reduceMotion ? 260 : 0);
                }
            } else {
                HTMLFormElement.prototype.submit.call(form);
            }
        }).catch(function () {
            HTMLFormElement.prototype.submit.call(form);
        });
    }

    document.addEventListener('submit', function (event) {
        var form = event.target;
        var submitter = event.submitter || $('[type="submit"]', form);

        if (form.hasAttribute('data-confirm') && form.dataset.confirmed !== 'true') {
            if (askConfirm(form, submitter)) {
                event.preventDefault();
                return;
            }
        }
        delete form.dataset.confirmed;

        if (form.hasAttribute('data-async') && window.fetch) {
            event.preventDefault();
            submitAsync(form, submitter && submitter.classList.contains('btn') ? submitter : null);
            return;
        }

        if (form.hasAttribute('data-flash')) {
            setFlash(form.getAttribute('data-flash'), form.getAttribute('data-flash-path'));
        }

        if (!form.hasAttribute('data-no-loading') && submitter && submitter.classList.contains('btn')) {
            setTimeout(function () { setLoading(submitter, true); }, 0);
        }
        startProgress();
    });

    /* Re-enable buttons when the page is restored from the back/forward cache. */
    window.addEventListener('pageshow', function (event) {
        if (event.persisted) {
            $$('.is-loading').forEach(function (button) { setLoading(button, false); });
            if (progressBar) { progressBar.classList.remove('is-active'); }
        }
    });

    /* Thin progress bar on internal navigation. */
    document.addEventListener('click', function (event) {
        var link = event.target.closest('a[href]');
        if (!link || event.defaultPrevented || event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) { return; }
        if (link.target === '_blank' || link.hasAttribute('download')) { return; }
        var url = new URL(link.href, location.href);
        if (url.origin !== location.origin || (url.pathname === location.pathname && url.search === location.search && url.hash)) { return; }
        startProgress();
    });

    /* ---------------- Keyboard shortcuts ---------------- */

    document.addEventListener('keydown', function (event) {
        if (event.key === 'Escape') {
            closeDropdowns();
            if (shell && shell.classList.contains('nav-open')) { setNav(false); }
            return;
        }
        if (isTyping(event.target) || event.ctrlKey || event.metaKey || event.altKey || $('dialog[open]')) { return; }

        if (event.key === '/') {
            var search = $('[data-search-input]');
            if (search && search.offsetParent !== null) {
                event.preventDefault();
                search.focus();
                search.select();
            }
        } else if (event.key === 'n' || event.key === 'N') {
            if (taskModal) {
                event.preventDefault();
                openTaskModal();
            }
        }
    });

    /* ---------------- Password helpers ---------------- */

    document.addEventListener('click', function (event) {
        var toggle = event.target.closest('[data-toggle-password]');
        if (!toggle) { return; }
        var input = toggle.parentElement.querySelector('input');
        var show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        toggle.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
        toggle.setAttribute('aria-pressed', show ? 'true' : 'false');
        toggle.innerHTML = iconSvg(show ? 'eye-off' : 'eye', 16);
    });

    function scorePassword(value) {
        if (!value) { return 0; }
        var score = 0;
        if (value.length >= 8) { score++; }
        if (value.length >= 12) { score++; }
        if (/[a-z]/.test(value) && /[A-Z]/.test(value)) { score++; }
        if (/\d/.test(value) && /[^A-Za-z0-9]/.test(value)) { score++; }
        else if (/\d/.test(value) || /[^A-Za-z0-9]/.test(value)) { score += 0.5; }
        return Math.max(1, Math.min(4, Math.floor(score)));
    }

    var STRENGTH_LABELS = ['', 'Weak', 'Fair', 'Good', 'Strong'];

    $$('[data-strength-for]').forEach(function (meter) {
        var input = document.getElementById(meter.getAttribute('data-strength-for'));
        var label = $('.strength-label', meter);
        if (!input) { return; }
        input.addEventListener('input', function () {
            var score = scorePassword(input.value);
            meter.setAttribute('data-score', String(score));
            label.textContent = input.value ? STRENGTH_LABELS[score] : '';
        });
    });

    $$('[data-match-for]').forEach(function (hint) {
        var confirm = document.getElementById(hint.getAttribute('data-match-confirm'));
        var original = document.getElementById(hint.getAttribute('data-match-for'));
        if (!confirm || !original) { return; }
        function update() {
            if (!confirm.value) {
                hint.textContent = '';
                hint.className = 'match-hint';
                confirm.setCustomValidity('');
                return;
            }
            var match = confirm.value === original.value;
            hint.className = 'match-hint ' + (match ? 'is-match' : 'is-mismatch');
            hint.innerHTML = iconSvg(match ? 'check' : 'x', 12) + (match ? 'Passwords match' : 'Passwords don’t match yet');
            confirm.setCustomValidity(match ? '' : 'Passwords do not match.');
        }
        confirm.addEventListener('input', update);
        original.addEventListener('input', update);
    });

    /* ---------------- Small enhancements ---------------- */

    $$('[data-greeting]').forEach(function (element) {
        var hour = new Date().getHours();
        element.textContent = hour < 5 ? 'Good evening' : hour < 12 ? 'Good morning' : hour < 18 ? 'Good afternoon' : 'Good evening';
    });

    $$('[data-today-label]').forEach(function (element) {
        try {
            element.textContent = new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
        } catch (error) { /* keep server value */ }
    });

    document.addEventListener('click', function (event) {
        var toggle = event.target.closest('[data-toggle-target]');
        if (!toggle) { return; }
        var target = document.getElementById(toggle.getAttribute('data-toggle-target'));
        if (!target) { return; }
        var open = target.hasAttribute('hidden');
        target.toggleAttribute('hidden', !open);
        toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
        if (open) {
            var field = $('input, select', target);
            if (field) { field.focus(); }
        }
    });

    /* Client-side tab filter (e.g. notifications: all / unread) */
    $$('[data-filter-group]').forEach(function (group) {
        var list = document.getElementById(group.getAttribute('data-filter-group'));
        if (!list) { return; }
        group.addEventListener('click', function (event) {
            var tab = event.target.closest('[data-filter]');
            if (!tab) { return; }
            var filter = tab.getAttribute('data-filter');
            $$('[data-filter]', group).forEach(function (item) {
                var active = item === tab;
                item.classList.toggle('is-active', active);
                item.setAttribute('aria-pressed', active ? 'true' : 'false');
            });
            var visible = 0;
            $$('[data-unread]', list).forEach(function (item) {
                var show = filter === 'all' || item.getAttribute('data-unread') === 'true';
                item.hidden = !show;
                if (show) { visible++; }
            });
            var empty = document.getElementById(list.id + '-filtered-empty');
            if (empty) { empty.hidden = visible !== 0; }
        });
    });

    /* ---------------- Real-time notifications ---------------- */

    if (shell && shell.getAttribute('data-notifications-url')) {
        var updatesUrl = shell.getAttribute('data-notifications-url');
        var notificationsPage = shell.getAttribute('data-notifications-page');
        var lastNotificationId = parseInt(shell.getAttribute('data-last-notification'), 10) || 0;
        var polling = false;

        var updateCount = function (count) {
            $$('[data-unread-count]').forEach(function (badge) {
                badge.textContent = count > 99 ? '99+' : String(count);
                badge.hidden = !count;
            });
            $$('[data-unread-dot]').forEach(function (dot) { dot.hidden = !count; });
            var bell = $('[data-bell]');
            if (bell) { bell.setAttribute('aria-label', 'Notifications' + (count ? ' (' + count + ' unread)' : '')); }
        };

        var ringBell = function () {
            var bell = $('[data-bell]');
            if (!bell) { return; }
            bell.classList.remove('is-ringing');
            void bell.offsetWidth;
            bell.classList.add('is-ringing');
        };

        var checkNotifications = function () {
            if (polling || document.hidden) { return; }
            polling = true;
            fetch(updatesUrl + '?last_id=' + lastNotificationId, {
                method: 'GET',
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
                credentials: 'same-origin',
                redirect: 'manual'
            }).then(function (response) {
                if (!response.ok) { return null; }
                return response.json();
            }).then(function (data) {
                if (!data) { return; }
                updateCount(data.unread_count);
                var fresh = data.notifications || [];
                if (!fresh.length) { return; }
                fresh.forEach(function (item) {
                    lastNotificationId = Math.max(lastNotificationId, item.id);
                });
                fresh.slice(-3).forEach(function (item) {
                    showToast(item.message, { title: 'New notification', tone: 'accent', icon: 'bell', href: notificationsPage, linkText: 'View notifications' });
                });
                ringBell();
            }).catch(function (error) {
                console.error('Unable to fetch notifications:', error);
            }).then(function () {
                polling = false;
            });
        };

        setInterval(checkNotifications, 10000);
        document.addEventListener('visibilitychange', function () {
            if (!document.hidden) { checkNotifications(); }
        });
    }
})();
