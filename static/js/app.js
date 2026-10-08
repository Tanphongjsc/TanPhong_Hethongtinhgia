// Synchronize filter controls after table-only pagination/sort updates.
document.addEventListener('htmx:afterSwap', (event) => {
  const target = event.detail.elt || event.target;
  if (target?.matches('[data-sort][data-per-page]')) {
    const formId = target.dataset.filterForm || 'cost-element-filters';
    const filters = document.getElementById(formId);
    if (filters) {
      filters.elements.sort.value = target.dataset.sort;
      filters.elements.per_page.value = target.dataset.perPage;
    }
  }
});

// Cached history restores HTML attributes, while input values may have changed
// only as DOM properties. Restore the visible controls from the pushed URL.
document.addEventListener('htmx:historyRestore', () => {
  const query = new URLSearchParams(window.location.search);
  document.querySelectorAll('[data-filter-form]').forEach((table) => {
    const form = document.getElementById(table.dataset.filterForm);
    if (!form) return;
    Array.from(form.elements).forEach((control) => {
      if (!control.name || control.type === 'submit') return;
      if (control.name === 'sort') control.value = table.dataset.sort;
      else if (control.name === 'per_page') control.value = table.dataset.perPage;
      else control.value = query.get(control.name) || '';
    });
  });
});

// Native POST forms (including new-version forms) need the same protection as
// hx-disabled-elt. Defer disabling so the clicked button's name/value is sent.
document.addEventListener('submit', (event) => {
  const form = event.target;
  if (event.defaultPrevented || !(form instanceof HTMLFormElement)
      || form.method.toLowerCase() !== 'post' || form.hasAttribute('hx-post')) return;
  if (form.dataset.submitting === 'true') {
    event.preventDefault();
    return;
  }
  form.dataset.submitting = 'true';
  window.setTimeout(() => {
    form.querySelectorAll('button[type="submit"], input[type="submit"]').forEach((button) => {
      if (!button.disabled) {
        button.dataset.submitLocked = 'true';
        button.disabled = true;
      }
    });
  }, 0);
});
window.addEventListener('pageshow', () => {
  document.querySelectorAll('form[data-submitting]').forEach((form) => delete form.dataset.submitting);
  document.querySelectorAll('[data-submit-locked]').forEach((button) => {
    button.disabled = false;
    delete button.dataset.submitLocked;
  });
});
