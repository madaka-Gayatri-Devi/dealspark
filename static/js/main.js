/**
 * DealSpark Main JavaScript
 * Handles:
 * - Smart debounced search autocomplete with category + product matching
 * - Recently viewed products tracking & client-side rendering (localStorage)
 * - Anonymous favorites & wishlist sync
 * - Web Share API with clipboard copy fallback & WhatsApp sharing
 * - Scroll-triggered section reveals (IntersectionObserver)
 * - Animated statistics count-up
 * - Back to top smooth scrolling
 * - Dynamic toast notifications
 */

document.addEventListener('DOMContentLoaded', () => {
  // Initialize Bootstrap Tooltips
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  tooltipTriggerList.map((tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl));

  // Auto-dismiss Flash Alerts after 6 seconds
  const alerts = document.querySelectorAll('.alert-dismissible');
  alerts.forEach((alert) => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      if (bsAlert) {
        bsAlert.close();
      }
    }, 6000);
  });

  // Initialize Debounced Autocomplete Search for Navbar & Hero
  initSearchAutocomplete();

  // Initialize Scroll-Triggered Section Reveals & Animated Counters
  initScrollReveal();
  initCounters();

  // Initialize Back to Top Button
  initBackToTop();

  // Sync anonymous favorites from localStorage
  syncFavoritesUI();

  // Render Recently Viewed Deals on Homepage if container exists
  renderRecentlyViewed();
});

/**
 * Toast Notification Trigger
 */
function showDealSparkToast(message, type = 'info') {
  const toastContainer = document.getElementById('toastContainer');
  if (!toastContainer) return;

  const toastId = 'toast-' + Date.now();
  let iconClass = 'bi-info-circle-fill text-primary';
  if (type === 'success') iconClass = 'bi-check-circle-fill text-success';
  if (type === 'warning') iconClass = 'bi-exclamation-triangle-fill text-warning';
  if (type === 'danger') iconClass = 'bi-x-circle-fill text-danger';

  const toastHtml = `
    <div id="${toastId}" class="toast align-items-center text-bg-white border-0 shadow-lg mb-2" role="alert" aria-live="assertive" aria-atomic="true">
      <div class="d-flex">
        <div class="toast-body d-flex align-items-center gap-2">
          <i class="bi ${iconClass} fs-5"></i>
          <div>${message}</div>
        </div>
        <button type="button" class="btn-close me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
      </div>
    </div>
  `;

  toastContainer.insertAdjacentHTML('beforeend', toastHtml);
  const toastElement = document.getElementById(toastId);
  const toast = new bootstrap.Toast(toastElement, { delay: 4000 });
  toast.show();

  toastElement.addEventListener('hidden.bs.toast', () => {
    toastElement.remove();
  });
}

/**
 * Scroll Reveal using IntersectionObserver
 */
function initScrollReveal() {
  const revealElements = document.querySelectorAll('.ds-reveal');
  if (!revealElements.length) return;

  if ('IntersectionObserver' in window) {
    const observer = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: '0px 0px -40px 0px' }
    );

    revealElements.forEach((el) => observer.observe(el));
  } else {
    // Fallback if IntersectionObserver not supported
    revealElements.forEach((el) => el.classList.add('is-visible'));
  }
}

/**
 * Animated Numerical Count-Up for Homepage Trust Statistics
 */
function initCounters() {
  const counterElements = document.querySelectorAll('[data-counter]');
  if (!counterElements.length) return;

  function startCount(el) {
    const target = parseInt(el.getAttribute('data-counter'), 10);
    if (isNaN(target) || target <= 0) return;

    let current = 0;
    const duration = 1400; // ms
    const startTime = performance.now();

    function update(time) {
      const elapsed = time - startTime;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      current = Math.floor(eased * target);
      el.textContent = current;

      if (progress < 1) {
        requestAnimationFrame(update);
      } else {
        el.textContent = target;
      }
    }
    requestAnimationFrame(update);
  }

  if ('IntersectionObserver' in window) {
    const counterObserver = new IntersectionObserver(
      (entries, obs) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            startCount(entry.target);
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.2 }
    );
    counterElements.forEach((el) => counterObserver.observe(el));
  } else {
    counterElements.forEach((el) => startCount(el));
  }
}

/**
 * Debounced Search Autocomplete Engine
 * Supports Navbar Search and Hero Search with Categories & Products
 */
function initSearchAutocomplete() {
  setupAutocomplete({
    inputId: 'navSearchInput',
    boxId: 'searchSuggestionsBox',
    clearBtnId: 'navSearchClear'
  });

  setupAutocomplete({
    inputId: 'heroSearchInput',
    boxId: 'heroSuggestionsBox',
    clearBtnId: 'heroSearchClear'
  });
}

function setupAutocomplete({ inputId, boxId, clearBtnId }) {
  const searchInput = document.getElementById(inputId);
  const suggestionsBox = document.getElementById(boxId);
  const clearBtn = clearBtnId ? document.getElementById(clearBtnId) : null;
  if (!searchInput || !suggestionsBox) return;

  let debounceTimer = null;
  let activeIndex = -1;

  // Toggle clear button visibility
  function updateClearButton() {
    if (!clearBtn) return;
    if (searchInput.value.trim().length > 0) {
      clearBtn.classList.remove('d-none');
    } else {
      clearBtn.classList.add('d-none');
    }
  }

  if (clearBtn) {
    clearBtn.addEventListener('click', () => {
      searchInput.value = '';
      suggestionsBox.innerHTML = '';
      suggestionsBox.classList.add('d-none');
      updateClearButton();
      searchInput.focus();
    });
  }

  searchInput.addEventListener('input', (e) => {
    const query = e.target.value.trim();
    updateClearButton();
    clearTimeout(debounceTimer);

    if (query.length < 2) {
      suggestionsBox.innerHTML = '';
      suggestionsBox.classList.add('d-none');
      return;
    }

    // Show loading skeleton while in-flight
    suggestionsBox.innerHTML = `
      <div class="p-3">
        <div class="ds-skeleton-bar" style="width: 45%;"></div>
        <div class="ds-skeleton-bar" style="width: 80%;"></div>
        <div class="ds-skeleton-bar" style="width: 65%;"></div>
      </div>
    `;
    suggestionsBox.classList.remove('d-none');

    debounceTimer = setTimeout(() => {
      fetch(`/api/search/suggestions?q=${encodeURIComponent(query)}`)
        .then((res) => {
          if (!res.ok) throw new Error('Network error');
          return res.json();
        })
        .then((data) => {
          renderSuggestions(data.suggestions || [], data.categories || [], query);
        })
        .catch(() => {
          suggestionsBox.innerHTML = `
            <div class="p-3 text-center text-danger small">
              <i class="bi bi-exclamation-circle me-1"></i> Unable to load live suggestions. Press Enter to view all results.
            </div>
          `;
          suggestionsBox.classList.remove('d-none');
        });
    }, 300);
  });

  function renderSuggestions(deals, categories, query) {
    activeIndex = -1;
    if (deals.length === 0 && categories.length === 0) {
      suggestionsBox.innerHTML = `
        <div class="p-4 text-center text-muted">
          <div class="fs-4 mb-2 text-warning"><i class="bi bi-search"></i></div>
          <div class="fw-bold text-dark mb-1">No deals found for "${escapeHtml(query)}"</div>
          <div class="small">Try searching for keywords like "kurti", "headphones", or "smartphone".</div>
        </div>
      `;
      suggestionsBox.classList.remove('d-none');
      return;
    }

    let html = '<div class="list-group list-group-flush">';

    // 1. Render Matching Categories
    if (categories && categories.length > 0) {
      html += `<div class="ds-autocomplete-section-title"><i class="bi bi-collection text-warning me-2"></i> Matching Categories</div>`;
      categories.forEach((cat) => {
        html += `
          <a href="/category/${cat.slug}" class="ds-autocomplete-cat-item ds-autocomplete-interactive-item">
            <span class="d-flex align-items-center gap-2">
              <span class="p-1 rounded-circle bg-warning bg-opacity-10 text-warning d-flex align-items-center justify-content-center" style="width: 24px; height: 24px;">
                <i class="bi ${cat.icon || 'bi-tag'}"></i>
              </span>
              <span>${escapeHtml(cat.name)}</span>
            </span>
            <span class="badge bg-light text-muted border">${cat.deals_count} Deals</span>
          </a>
        `;
      });
    }

    // 2. Render Matching Deals
    if (deals && deals.length > 0) {
      html += `<div class="ds-autocomplete-section-title"><i class="bi bi-tag-fill text-primary me-2"></i> Matching Deals</div>`;
      deals.forEach((item) => {
        html += `
          <a href="/deal/${item.slug}" class="ds-autocomplete-item ds-autocomplete-interactive-item">
            <img src="${item.image_url}" alt="${escapeHtml(item.title)}" class="ds-autocomplete-img" onerror="this.onerror=null; this.src='https://placehold.co/46x46/f8fafc/64748b?text=Deal';">
            <div class="flex-grow-1 overflow-hidden">
              <div class="ds-autocomplete-title">${escapeHtml(item.title)}</div>
              <div class="ds-autocomplete-meta d-flex align-items-center gap-2 flex-wrap">
                <span class="fw-bold text-dark">${item.discounted_price}</span>
                ${item.original_price ? `<span class="text-decoration-line-through">${item.original_price}</span>` : ''}
                ${item.discount_percentage > 0 ? `<span class="badge bg-success small">${item.discount_percentage}% OFF</span>` : ''}
                ${item.merchant_name ? `<span class="text-muted small">• ${escapeHtml(item.merchant_name)}</span>` : ''}
              </div>
            </div>
          </a>
        `;
      });
    }

    // 3. View All Search Results Footer
    html += `
      <a href="/search?q=${encodeURIComponent(query)}" class="p-2 text-center text-primary-custom small fw-bold d-block bg-light text-decoration-none border-top">
        View all search results for "${escapeHtml(query)}" <i class="bi bi-arrow-right ms-1"></i>
      </a>
    </div>`;

    suggestionsBox.innerHTML = html;
    suggestionsBox.classList.remove('d-none');
  }

  // Keyboard navigation inside suggestions (Up/Down/Enter/Escape)
  searchInput.addEventListener('keydown', (e) => {
    const items = suggestionsBox.querySelectorAll('.ds-autocomplete-interactive-item');
    if (suggestionsBox.classList.contains('d-none') || items.length === 0) return;

    if (e.key === 'ArrowDown') {
      e.preventDefault();
      activeIndex = (activeIndex + 1) % items.length;
      updateActiveItem(items);
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      activeIndex = (activeIndex - 1 + items.length) % items.length;
      updateActiveItem(items);
    } else if (e.key === 'Enter' && activeIndex >= 0) {
      e.preventDefault();
      items[activeIndex].click();
    } else if (e.key === 'Escape') {
      suggestionsBox.classList.add('d-none');
    }
  });

  function updateActiveItem(items) {
    items.forEach((it, idx) => {
      if (idx === activeIndex) {
        it.classList.add('active');
        it.scrollIntoView({ block: 'nearest' });
      } else {
        it.classList.remove('active');
      }
    });
  }

  // Click outside closes the dropdown
  document.addEventListener('click', (e) => {
    if (!searchInput.contains(e.target) && !suggestionsBox.contains(e.target)) {
      suggestionsBox.classList.add('d-none');
    }
  });
}

/**
 * Back to Top Floating Button Handler
 */
function initBackToTop() {
  const btn = document.getElementById('btnBackToTop');
  if (!btn) return;

  window.addEventListener('scroll', () => {
    if (window.scrollY > 300) {
      btn.classList.add('show');
    } else {
      btn.classList.remove('show');
    }
  });

  btn.addEventListener('click', () => {
    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    });
  });
}

/**
 * DealSpark LocalStorage Favorites Engine
 * Anonymous visitors can bookmark deals without requiring an account.
 */
function getStoredFavorites() {
  try {
    const raw = localStorage.getItem('dealspark_favorites');
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function setStoredFavorites(ids) {
  try {
    localStorage.setItem('dealspark_favorites', JSON.stringify(ids));
  } catch (e) {}
}

function syncFavoritesUI() {
  const storedIds = getStoredFavorites().map(Number);
  const idSet = new Set(storedIds);

  // Sync wishlist buttons on deal cards
  document.querySelectorAll('.btn-wishlist-card[data-deal-id]').forEach((btn) => {
    const dealId = Number(btn.getAttribute('data-deal-id'));
    const icon = btn.querySelector('i');
    if (idSet.has(dealId)) {
      btn.classList.add('is-active');
      if (icon) icon.className = 'bi bi-heart-fill text-danger';
    } else {
      btn.classList.remove('is-active');
      if (icon) icon.className = 'bi bi-heart';
    }
  });

  // Sync detail page button
  const detailBtn = document.getElementById('detailFavBtn');
  if (detailBtn && detailBtn.hasAttribute('data-deal-id')) {
    const dealId = Number(detailBtn.getAttribute('data-deal-id'));
    const icon = detailBtn.querySelector('i');
    const label = detailBtn.querySelector('.fav-label');
    if (idSet.has(dealId)) {
      detailBtn.classList.add('is-active');
      if (icon) icon.className = 'bi bi-heart-fill text-danger fs-5';
      if (label) label.textContent = 'Saved in Wishlist';
    } else {
      detailBtn.classList.remove('is-active');
      if (icon) icon.className = 'bi bi-heart fs-5';
      if (label) label.textContent = 'Save Deal';
    }
  }
}

/**
 * Toggle Favorite / Wishlist Action (Client LocalStorage + Background Server Sync)
 */
function toggleDealFavorite(productId, buttonEl) {
  productId = Number(productId);
  let storedIds = getStoredFavorites().map(Number);
  const isCurrentlySaved = storedIds.includes(productId);
  let favorited = false;

  if (isCurrentlySaved) {
    storedIds = storedIds.filter((id) => id !== productId);
    favorited = false;
  } else {
    storedIds.push(productId);
    favorited = true;
  }
  setStoredFavorites(storedIds);

  // Update button visual state immediately
  const icon = buttonEl.querySelector('i');
  const label = buttonEl.querySelector('.fav-label');
  const isDetailBtn = buttonEl.id === 'detailFavBtn';

  if (favorited) {
    buttonEl.classList.add('is-active');
    if (icon) icon.className = 'bi bi-heart-fill text-danger' + (isDetailBtn ? ' fs-5' : '');
    if (label) label.textContent = 'Saved in Wishlist';
    showDealSparkToast('Deal saved to your favorites!', 'success');
  } else {
    buttonEl.classList.remove('is-active');
    if (icon) icon.className = 'bi bi-heart' + (isDetailBtn ? ' fs-5' : '');
    if (label) label.textContent = 'Save Deal';
    showDealSparkToast('Deal removed from favorites.', 'info');

    // If on the saved favorites page, smoothly animate card removal
    const favCol = document.getElementById(`fav-col-${productId}`);
    if (favCol) {
      favCol.style.transition = 'opacity 0.25s ease, transform 0.25s ease';
      favCol.style.opacity = '0';
      favCol.style.transform = 'scale(0.95)';
      setTimeout(() => {
        favCol.remove();
        const favCountEl = document.getElementById('favCount');
        if (favCountEl) {
          const remaining = document.querySelectorAll('#favCardsRow .col').length;
          favCountEl.textContent = remaining;
          if (remaining === 0) {
            window.location.href = '/favorites';
          }
        }
      }, 250);
    }
  }

  // Also sync with server in background if CSRF token present
  const csrfMeta = document.querySelector('meta[name="csrf-token"]');
  const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';

  fetch(`/favorites/toggle/${productId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken,
      'X-Requested-With': 'XMLHttpRequest',
    },
  }).catch(() => {});
}

/**
 * DealSpark Recently Viewed Products Engine (LocalStorage)
 */
function getRecentlyViewed() {
  try {
    const raw = localStorage.getItem('dealspark_recent_deals');
    return raw ? JSON.parse(raw) : [];
  } catch (e) {
    return [];
  }
}

function setRecentlyViewed(items) {
  try {
    localStorage.setItem('dealspark_recent_deals', JSON.stringify(items));
  } catch (e) {}
}

function trackRecentlyViewed(deal) {
  if (!deal || !deal.id) return;
  let items = getRecentlyViewed();
  // Remove if deal already tracked to place it at the front
  items = items.filter((item) => Number(item.id) !== Number(deal.id));
  items.unshift(deal);
  // Cap at 8 recent deals
  if (items.length > 8) {
    items = items.slice(0, 8);
  }
  setRecentlyViewed(items);
}

function renderRecentlyViewed() {
  const section = document.getElementById('recentlyViewedSection');
  const row = document.getElementById('recentlyViewedRow');
  if (!section || !row) return;

  const items = getRecentlyViewed();
  if (items.length === 0) {
    section.classList.add('d-none');
    return;
  }

  let html = '';
  items.forEach((deal) => {
    html += `
      <div class="col">
        <div class="deal-card h-100">
          <div class="deal-img-wrapper">
            <div class="deal-badges-start">
              ${deal.discount_percentage > 0 ? `<span class="badge-discount">${deal.discount_percentage}% OFF</span>` : ''}
            </div>
            <div class="deal-badges-end">
              ${deal.merchant_name ? `<span class="merchant-pill"><span class="merchant-pill-dot"></span>${escapeHtml(deal.merchant_name)}</span>` : ''}
            </div>
            <a href="/deal/${deal.slug}" class="deal-img-link" title="${escapeHtml(deal.title)}">
              <img src="${deal.image_url}" alt="${escapeHtml(deal.title)}" class="deal-img" loading="lazy" onerror="this.onerror=null; this.src='https://placehold.co/300x200/f8fafc/64748b?text=DealSpark';">
            </a>
          </div>
          <div class="deal-content">
            ${deal.category_name ? `<div class="deal-category mb-1">${escapeHtml(deal.category_name)}</div>` : ''}
            <h3 class="deal-title">
              <a href="/deal/${deal.slug}" class="text-decoration-none text-dark" title="${escapeHtml(deal.title)}">
                ${escapeHtml(deal.title)}
              </a>
            </h3>
            <div class="deal-price-row">
              <span class="deal-price-discounted">${deal.discounted_price}</span>
              ${deal.original_price ? `<span class="deal-price-original">${deal.original_price}</span>` : ''}
            </div>
            ${deal.savings ? `<div class="deal-savings-tag"><i class="bi bi-tag-fill"></i> Save ${deal.savings}</div>` : ''}
            <div class="deal-actions">
              <a href="/deal/${deal.slug}" class="btn-view-details">Details</a>
              <a href="/out/${deal.id}" target="_blank" rel="noopener noreferrer nofollow" class="btn-buy-now">
                <span>Buy Now</span>
                <i class="bi bi-box-arrow-up-right"></i>
              </a>
            </div>
          </div>
        </div>
      </div>
    `;
  });

  row.innerHTML = html;
  section.classList.remove('d-none');
}

function clearRecentlyViewed() {
  localStorage.removeItem('dealspark_recent_deals');
  const section = document.getElementById('recentlyViewedSection');
  if (section) {
    section.classList.add('d-none');
  }
  showDealSparkToast('Recently viewed history cleared.', 'info');
}

/**
 * Web Share API with Clipboard Fallback
 */
function shareDeal(dealTitle, dealUrl) {
  if (navigator.share) {
    navigator.share({
      title: dealTitle,
      text: `🔥 Found this price drop on DealSpark: ${dealTitle}`,
      url: dealUrl
    }).catch((err) => {
      // AbortError indicates user cancelled share dialog; do nothing
      if (err.name !== 'AbortError') {
        copyDealLink(dealUrl, dealTitle);
      }
    });
  } else {
    copyDealLink(dealUrl, dealTitle);
  }
}

/**
 * Copy Deal Link to Clipboard
 */
function copyDealLink(dealUrl, dealTitle) {
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(dealUrl)
      .then(() => {
        showDealSparkToast(`Copied deal link for "${dealTitle}"!`, 'success');
      })
      .catch(() => {
        fallbackCopyTextToClipboard(dealUrl, dealTitle);
      });
  } else {
    fallbackCopyTextToClipboard(dealUrl, dealTitle);
  }
}

function fallbackCopyTextToClipboard(text, dealTitle) {
  const textArea = document.createElement('textarea');
  textArea.value = text;
  textArea.style.position = 'fixed';
  textArea.style.left = '-9999px';
  document.body.appendChild(textArea);
  textArea.focus();
  textArea.select();

  try {
    const successful = document.execCommand('copy');
    if (successful) {
      showDealSparkToast(`Copied deal link for "${dealTitle}"!`, 'success');
    } else {
      showDealSparkToast('Failed to copy link. Please copy manually.', 'danger');
    }
  } catch (err) {
    showDealSparkToast('Could not copy link.', 'danger');
  }
  document.body.removeChild(textArea);
}

/**
 * Share Deal via WhatsApp
 */
function shareOnWhatsApp(dealTitle, dealUrl, price) {
  const text = encodeURIComponent(`🔥 Check out this deal on DealSpark: ${dealTitle} at just ${price}!\n👉 ${dealUrl}`);
  window.open(`https://api.whatsapp.com/send?text=${text}`, '_blank');
}

/**
 * HTML Escaper helper
 */
function escapeHtml(string) {
  if (!string) return '';
  return String(string)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}
