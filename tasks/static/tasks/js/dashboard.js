/* ==========================================================================
   Dashboard: drag-and-drop task ordering (saved per user in this browser)
   Keeps the original storage key so existing custom orders are preserved.
   ========================================================================== */
(function () {
    'use strict';

    var taskList = document.getElementById('task-list');
    var resetButton = document.getElementById('reset-task-order');
    var dragStatus = document.getElementById('drag-status');

    if (!taskList) {
        if (resetButton) { resetButton.hidden = true; }
        return;
    }

    var storageKey = 'planit-task-order-' + taskList.getAttribute('data-user-id');
    var draggedTask = null;

    function announce(message) {
        if (dragStatus) { dragStatus.textContent = message; }
    }

    function getTaskCards() {
        return Array.prototype.slice.call(taskList.querySelectorAll('[data-task-id]'));
    }

    function getSavedTaskOrder() {
        try {
            var saved = localStorage.getItem(storageKey);
            return saved ? JSON.parse(saved) : [];
        } catch (error) {
            console.error('Unable to read saved task order:', error);
            return [];
        }
    }

    function updateResetVisibility() {
        if (resetButton) { resetButton.hidden = getSavedTaskOrder().length === 0; }
    }

    function saveTaskOrder() {
        var currentOrder = getTaskCards().map(function (card) { return card.dataset.taskId; });
        var savedOrder = getSavedTaskOrder();
        var combined = currentOrder.concat(savedOrder.filter(function (id) {
            return currentOrder.indexOf(id) === -1;
        }));

        try {
            localStorage.setItem(storageKey, JSON.stringify(combined));
            announce('Task order saved in this browser.');
        } catch (error) {
            console.error('Unable to save task order:', error);
            announce('Unable to save task order.');
        }
        updateResetVisibility();
    }

    function restoreTaskOrder() {
        var savedOrder = getSavedTaskOrder();
        if (!savedOrder.length) { return; }

        var position = new Map(savedOrder.map(function (id, index) { return [id, index]; }));
        var cards = getTaskCards();

        cards.sort(function (a, b) {
            var pa = position.has(a.dataset.taskId) ? position.get(a.dataset.taskId) : Number.MAX_SAFE_INTEGER;
            var pb = position.has(b.dataset.taskId) ? position.get(b.dataset.taskId) : Number.MAX_SAFE_INTEGER;
            return pa - pb;
        });

        cards.forEach(function (card) { taskList.appendChild(card); });
    }

    function flash(card) {
        card.classList.remove('is-moved');
        void card.offsetWidth;
        card.classList.add('is-moved');
    }

    restoreTaskOrder();
    updateResetVisibility();

    getTaskCards().forEach(function (card) {
        var handle = card.querySelector('.drag-handle');

        card.addEventListener('dragstart', function (event) {
            if (!card.dataset.dragAllowed) {
                event.preventDefault();
                return;
            }
            draggedTask = card;
            card.classList.add('dragging');
            event.dataTransfer.effectAllowed = 'move';
            event.dataTransfer.setData('text/plain', card.dataset.taskId);
        });

        card.addEventListener('dragend', function () {
            card.classList.remove('dragging');
            getTaskCards().forEach(function (item) {
                item.classList.remove('drag-over');
                delete item.dataset.dragAllowed;
            });
            draggedTask = null;
        });

        card.addEventListener('dragover', function (event) {
            if (!draggedTask || draggedTask === card) { return; }
            event.preventDefault();
            event.dataTransfer.dropEffect = 'move';
            card.classList.add('drag-over');
        });

        card.addEventListener('dragleave', function () {
            card.classList.remove('drag-over');
        });

        card.addEventListener('drop', function (event) {
            event.preventDefault();
            card.classList.remove('drag-over');
            if (!draggedTask || draggedTask === card) { return; }

            var rect = card.getBoundingClientRect();
            if (event.clientY > rect.top + rect.height / 2) {
                card.after(draggedTask);
            } else {
                card.before(draggedTask);
            }
            flash(draggedTask);
            saveTaskOrder();
        });

        if (!handle) { return; }

        handle.addEventListener('mousedown', function () {
            card.dataset.dragAllowed = 'true';
        });

        handle.addEventListener('mouseup', function () {
            delete card.dataset.dragAllowed;
        });

        handle.addEventListener('touchstart', function () {
            announce('Use a mouse, or focus the handle and press the arrow keys, to reorder tasks.');
        }, { passive: true });

        handle.addEventListener('click', function () {
            announce('Drag the handle, or use the arrow keys, to move this task.');
        });

        /* Keyboard reordering for accessibility */
        handle.addEventListener('keydown', function (event) {
            if (event.key !== 'ArrowUp' && event.key !== 'ArrowDown') { return; }
            event.preventDefault();

            var sibling = event.key === 'ArrowUp' ? card.previousElementSibling : card.nextElementSibling;
            if (!sibling) { return; }

            if (event.key === 'ArrowUp') { sibling.before(card); } else { sibling.after(card); }
            handle.focus();
            flash(card);
            saveTaskOrder();
        });
    });

    if (resetButton) {
        resetButton.addEventListener('click', function () {
            try { localStorage.removeItem(storageKey); } catch (error) { /* ignore */ }
            announce('Custom task order cleared. Reloading the original order…');
            window.location.reload();
        });
    }
})();
