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
    resizeHandler: null,
    init() {
      try {
        const saved = localStorage.getItem('costing.sidebar.expanded');
        if (saved !== null) this.expanded = saved === 'true';
      } catch (_) { /* Browser storage can be disabled. */ }
      this.$watch('expanded', (value) => {
        try { localStorage.setItem('costing.sidebar.expanded', String(value)); } catch (_) {}
      });
      this.resizeHandler = () => {
        this.desktop = window.matchMedia('(min-width: 992px)').matches;
        if (this.desktop) this.mobileOpen = false;
      };
      window.addEventListener('resize', this.resizeHandler);
    },
    destroy() { window.removeEventListener('resize', this.resizeHandler); },
    toggleSidebar() {
      if (this.desktop) this.expanded = !this.expanded;
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
    init() { this.timer = window.setTimeout(() => { this.visible = false; }, 6000); },
    destroy() { window.clearTimeout(this.timer); },
  }));
});
