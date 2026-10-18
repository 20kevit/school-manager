(function () {
    'use strict';

    /* === Mobile Sidebar Controller ===
     * The same sidebar is a permanent column on desktop and an off-canvas
     * drawer on mobile (<=1024px, matches CSS breakpoint in layout.css).
     * On mobile we expose the open state to AT via aria-expanded and keep
     * links unreachable while the drawer is closed using inert.
     */
    var toggle = document.getElementById('menu-toggle');
    var sidebar = document.getElementById('sidebar');
    var overlay = document.getElementById('sidebar-overlay');

    if (toggle && sidebar && overlay) {
        var mobileQuery = window.matchMedia('(max-width: 1024px)');
        var isOpen = false;

        var applyInert = function () {
            // Keep links focusable only while visible in the layout.
            sidebar.inert = mobileQuery.matches && !isOpen;
        };

        var updateBodyScroll = function () {
            document.body.style.overflow = (isOpen && mobileQuery.matches) ? 'hidden' : '';
        };

        var openSidebar = function () {
            isOpen = true;
            sidebar.classList.add('open');
            overlay.classList.add('active');
            toggle.setAttribute('aria-expanded', 'true');
            toggle.setAttribute('aria-label', 'بستن منو');
            applyInert();
            updateBodyScroll();
        };

        var closeSidebar = function (options) {
            options = options || {};
            isOpen = false;
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
            toggle.setAttribute('aria-expanded', 'false');
            toggle.setAttribute('aria-label', 'باز کردن منو');
            applyInert();
            updateBodyScroll();
            if (options.restoreFocus && mobileQuery.matches) {
                toggle.focus();
            }
        };

        toggle.addEventListener('click', function () {
            if (isOpen) {
                closeSidebar();
            } else {
                openSidebar();
            }
        });

        overlay.addEventListener('click', function () {
            closeSidebar({ restoreFocus: true });
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && isOpen && mobileQuery.matches) {
                closeSidebar({ restoreFocus: true });
            }
        });

        // Navigate, don't leave a stale open drawer behind.
        sidebar.addEventListener('click', function (e) {
            if (mobileQuery.matches && e.target.closest('a, button')) {
                closeSidebar();
            }
        });

        var handleViewportChange = function () {
            closeSidebar();
        };

        if (typeof mobileQuery.addEventListener === 'function') {
            mobileQuery.addEventListener('change', handleViewportChange);
        } else if (typeof mobileQuery.addListener === 'function') {
            mobileQuery.addListener(handleViewportChange);
        }

        applyInert();
    }

    /* === Create User Form: role-dependent fields ===
     * Fields declare the roles for which they are required
     * (data-required-roles). Server-side validation stays authoritative.
     */
    var userForm = document.getElementById('create-user-form');
    if (userForm) {
        var roleSelect = userForm.querySelector('[data-user-form-role]');
        var passwordGroup = document.getElementById('password-group');
        var studentNote = document.getElementById('student-password-note');
        var profileFields = document.getElementById('profile-fields');
        var studentFields = document.getElementById('student-fields');
        var requiredInputs = userForm.querySelectorAll('[data-required-roles]');

        var syncUserForm = function () {
            var role = roleSelect ? roleSelect.value : '';
            // Unselected role defaults to the ADMIN password contract,
            // matching the server-rendered generic form.
            var effectiveRole = role || 'ADMIN';
            var isStudent = role === 'STUDENT';

            requiredInputs.forEach(function (input) {
                var roles = input.getAttribute('data-required-roles').split(',');
                input.required = roles.indexOf(effectiveRole) !== -1;
            });

            if (passwordGroup) passwordGroup.hidden = isStudent;
            if (studentNote) studentNote.hidden = !isStudent;
            if (profileFields) profileFields.hidden = role === '' || role === 'ADMIN';
            if (studentFields) studentFields.hidden = !isStudent;
        };

        if (roleSelect) {
            roleSelect.addEventListener('change', syncUserForm);
        }
        syncUserForm();
    }

    /* === Auto-dismiss Flash Messages === */
    var alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(function (alert) {
        setTimeout(function () {
            alert.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            setTimeout(function () { alert.remove(); }, 300);
        }, 5000);
    });

    /* === Toast System === */
    window.showToast = function (message, type) {
        type = type || 'info';
        var container = document.getElementById('toast-container');
        if (!container) return;

        var toast = document.createElement('div');
        toast.className = 'toast toast-' + type;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(function () {
            toast.style.animation = 'toastOut 0.3s ease forwards';
            setTimeout(function () { toast.remove(); }, 300);
        }, 3000);
    };

    /* === Button Loading State === */
    document.addEventListener('submit', function (e) {
        var btn = e.target.querySelector('button[type="submit"]');
        if (btn && !btn.classList.contains('no-loading')) {
            btn.classList.add('loading');
            btn.disabled = true;
        }
    });

    /* === Confirmation Dialogs === */
    document.addEventListener('click', function (e) {
        var el = e.target.closest('[data-confirm]');
        if (el) {
            var message = el.getAttribute('data-confirm');
            if (!confirm(message)) {
                e.preventDefault();
                e.stopPropagation();
            }
        }
    });
})();
