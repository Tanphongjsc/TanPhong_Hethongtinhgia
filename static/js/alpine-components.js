document.addEventListener('alpine:init', () => {
  Alpine.data('formulaEditor', () => ({
    insert(token) {
      const editor = this.$refs.expression;
      if (!editor) return;
      const start = editor.selectionStart;
      const end = editor.selectionEnd;
      editor.setRangeText(token, start, end, 'end');
      editor.dispatchEvent(new Event('input', { bubbles: true }));
      editor.focus();
    },
  }));
  Alpine.data('appShell', () => ({
    expanded: window.matchMedia('(min-width: 1280px)').matches,
    desktop: window.matchMedia('(min-width: 992px)').matches,
    mobileOpen: false,
    density: 'compact',
    resizeHandler: null,
    sidebarTimer: null,
    init() {
      try {
        const saved = localStorage.getItem('costing.sidebar.expanded');
        if (saved !== null) this.expanded = saved === 'true';
        const density = localStorage.getItem('costing.ui.density');
        if (density === 'comfortable') this.density = density;
      } catch (_) { /* Browser storage can be disabled. */ }
      document.documentElement.dataset.density = this.density;
      this.$watch('expanded', (value) => {
        try { localStorage.setItem('costing.sidebar.expanded', String(value)); } catch (_) {}
      });
      this.resizeHandler = () => {
        this.desktop = window.matchMedia('(min-width: 992px)').matches;
        if (this.desktop) this.mobileOpen = false;
      };
      window.addEventListener('resize', this.resizeHandler);
    },
    destroy() {
      window.removeEventListener('resize', this.resizeHandler);
      window.clearTimeout(this.sidebarTimer);
    },
    setDensity(value) {
      if (!['compact', 'comfortable'].includes(value)) return;
      this.density = value;
      document.documentElement.dataset.density = value;
      try { localStorage.setItem('costing.ui.density', value); } catch (_) {}
    },
    toggleSidebar() {
      if (this.desktop) {
        // Animate an explicit toggle, never the first render or a breakpoint change.
        window.clearTimeout(this.sidebarTimer);
        this.$el.dataset.sidebarMotion = 'true';
        this.expanded = !this.expanded;
        this.sidebarTimer = window.setTimeout(() => { delete this.$el.dataset.sidebarMotion; }, 200);
      }
      else this.mobileOpen = !this.mobileOpen;
    },
  }));
  Alpine.data('overlayPanel', (initiallyOpen = false) => ({
    open: initiallyOpen,
    show() { this.open = true; },
    close() { this.open = false; },
  }));
  Alpine.data('toast', () => ({
    visible: true,
    timer: null,
    init() {
      const severity = this.$el.dataset.severity || 'success';
      if (severity.split(' ').includes('error')) return;
      this.timer = window.setTimeout(() => { this.visible = false; }, severity.includes('warning') ? 10000 : 6000);
    },
    destroy() { window.clearTimeout(this.timer); },
  }));
});

// Presentation only: focus, tooltip and busy state. No request/payload rewriting.
(() => {
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  const focusError = (root = document) => {
    const field = root.querySelector?.('input[aria-invalid="true"]:not([type="hidden"]), select[aria-invalid="true"], textarea[aria-invalid="true"]');
    if (!field || field.disabled) return;
    // A newly mounted Alpine focus trap must prefer the same invalid field.
    field.setAttribute('autofocus', '');
    window.requestAnimationFrame(() => {
      if (!field.isConnected || !field.getClientRects().length) return;
      field.focus({ preventScroll: true });
      field.scrollIntoView({ block: 'center', behavior: motion.matches ? 'instant' : 'smooth' });
    });
  };
  const initialize = (root = document) => {
    root.querySelectorAll?.('.ui-breadcrumbs').forEach((nav) => { nav.scrollLeft = nav.scrollWidth; });
    focusError(root);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', () => initialize());
  else initialize();
  document.addEventListener('htmx:afterSettle', (event) => {
    const root = event.detail.elt?.isConnected ? event.detail.elt : document;
    initialize(root);
  });

  const busyTargets = new WeakMap();
  document.addEventListener('htmx:beforeRequest', (event) => {
    const target = event.detail.target;
    if (target) {
      busyTargets.set(event.detail.xhr, target);
      target.setAttribute('aria-busy', 'true');
    }
  });
  document.addEventListener('htmx:afterRequest', (event) => {
    const target = busyTargets.get(event.detail.xhr);
    target?.removeAttribute('aria-busy');
    busyTargets.delete(event.detail.xhr);
  });

  // Delegated tooltip survives HTMX swaps and gives keyboard users the same cue.
  let tooltip, owner;
  const hide = () => {
    if (owner && tooltip) {
      const ids = (owner.getAttribute('aria-describedby') || '').split(/\s+/).filter((id) => id && id !== tooltip.id);
      if (ids.length) owner.setAttribute('aria-describedby', ids.join(' '));
      else owner.removeAttribute('aria-describedby');
    }
    tooltip?.remove(); tooltip = null; owner = null;
  };
  const show = (target) => {
    const text = target?.dataset.tooltip;
    if (!text || (target.dataset.collapsedTooltip !== undefined && target.closest('.ui-shell')?.dataset.collapsed !== 'true')) return;
    hide(); owner = target;
    tooltip = document.createElement('div');
    tooltip.id = 'ui-tooltip'; tooltip.className = 'ui-tooltip'; tooltip.role = 'tooltip';
    tooltip.textContent = text;
    document.body.appendChild(tooltip);
    const rect = target.getBoundingClientRect();
    const hint = tooltip.getBoundingClientRect();
    const left = Math.min(Math.max(8, rect.left + rect.width / 2 - hint.width / 2), window.innerWidth - hint.width - 8);
    const top = rect.bottom + hint.height + 8 < window.innerHeight ? rect.bottom + 6 : Math.max(8, rect.top - hint.height - 6);
    tooltip.style.left = `${left}px`; tooltip.style.top = `${top}px`;
    target.setAttribute('aria-describedby', `${target.getAttribute('aria-describedby') || ''} ui-tooltip`.trim());
  };
  document.addEventListener('mouseover', (event) => {
    const target = event.target.closest('[data-tooltip]');
    if (target && target !== owner) show(target);
  });
  document.addEventListener('mouseout', (event) => {
    if (owner && !owner.contains(event.relatedTarget)) hide();
  });
  document.addEventListener('focusin', (event) => show(event.target.closest('[data-tooltip]')));
  document.addEventListener('focusout', hide);
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') hide(); });
  document.addEventListener('htmx:beforeSwap', hide);
  window.addEventListener('resize', hide);
  window.addEventListener('scroll', hide, true);
})();
