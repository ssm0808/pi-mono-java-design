  const slots = Array.from(roots, (root, index) => ({
    root, model: models[index], item: root.closest('.catalog-item'),
    shell: root.querySelector('[data-api-shell]'), fallback: null, cache: null
  }));
  if (slots.some((slot) => !slot.model || !slot.item || !slot.shell)) return;
  const detach = (shell) => {
    const fragment = document.createDocumentFragment();
    while (shell.firstChild) fragment.appendChild(shell.firstChild);
    return fragment;
  };
  const park = (slot) => {
    if (!slot.shell.firstChild) return;
    slot.cache = detach(slot.shell);
    delete slot.root.dataset.mounted;
  };
  const mount = (slot) => {
    if (slot.shell.firstChild) return;
    if (!slot.cache) {
      const staging = make('section', '');
      const shell = make('div', '');
      shell.setAttribute('data-api-shell', '');
      staging.appendChild(shell);
      try {
        renderOperation(staging, slot.model);
        shell.querySelectorAll('.contract-detail').forEach((section) => {
          const heading = section.querySelector('h3');
          const part = make('details', 'catalog-part');
          part.appendChild(make('summary', '', heading.textContent));
          heading.remove();
          section.replaceWith(part);
          part.appendChild(section);
        });
        slot.cache = detach(shell);
      } catch (error) {
        // Rendering failure must leave the complete native contract available.
        slot.cache = slot.fallback;
      }
      slot.fallback = null;
    }
    slot.shell.appendChild(slot.cache);
    slot.root.dataset.mounted = 'true';
  };
  const openSlot = (slot) => {
    slots.forEach((other) => {
      if (other === slot) return;
      if (other.item.open) other.item.open = false;
      park(other);
    });
    mount(slot);
    if (!slot.item.open) slot.item.open = true;
  };
  slots.forEach((slot) => {
    slot.item.querySelector('summary').addEventListener('click', (event) => {
      event.preventDefault();
      if (slot.item.open) {
        slot.item.open = false;
        park(slot);
      } else {
        openSlot(slot);
      }
    });
    slot.item.addEventListener('toggle', (event) => {
      if (event.target !== slot.item) return;
      if (slot.item.open) openSlot(slot);
      else park(slot);
    });
    slot.fallback = detach(slot.shell);
  });
  const openAnchor = () => {
    const slot = slots.find((item) => `#${item.item.id}` === window.location.hash);
    if (!slot) return;
    openSlot(slot);
    slot.item.scrollIntoView?.({ block: 'start' });
  };
  window.addEventListener('hashchange', openAnchor);
  slots.filter((slot) => slot.item.open).forEach(openSlot);
  openAnchor();
