/**
 * @fileoverview
 * SOURCE CHECKLIST — Feature Entry Point
 * Feature: source-checklist
 *
 * Wires together the Source Checklist feature:
 * - Initialises on DOMContentLoaded (after the main app loads)
 * - Hooks into the existing CompanyOS app patterns
 *
 * Script load order (declared in index.html):
 *   1. checklistTypes.js       — JSDoc typedefs + constants
 *   2. sampleChecklist.js      — BeanRush sample data + isBeanRushProfile()
 *   3. checklistCompletion.js  — computeChecklistFromProfile(), computeReadiness()
 *   4. sourceChecklistService.js — SourceChecklistService
 *   5. SourceChecklist.js      — SourceChecklist component (main)
 *   6. index.js                — THIS FILE — wiring & init
 */

'use strict';

// ─── DOMContentLoaded Init ────────────────────────────────────────────────────
//
// The main app's DOMContentLoaded listener is already declared in index.html.
// We add a SECOND listener here — both will fire on the same event.
// This is safe and standard practice for modular vanilla JS.
//
document.addEventListener('DOMContentLoaded', () => {
  // Allow the main app's DOMContentLoaded to complete first (it calls
  // loadFromStorage and restores COMPANY_STATE) before we initialise.
  requestAnimationFrame(() => {
    try {
      SourceChecklist.init();
    } catch (e) {
      console.warn('[SourceChecklist] Init error:', e);
    }
  });
});

// ─── Patch: update readiness widget when results page is shown ────────────────
//
// We patch the existing `navigate` function minimally — only to fire
// SourceChecklist.updateReadinessWidget() when the results page is navigated to.
// This is the only way to hook into the results page rendering without
// modifying populateAllPages() directly.
//
(function patchNavigate() {
  const _originalNavigate = window.navigate;
  if (typeof _originalNavigate !== 'function') {
    // navigate() is defined later in the inline script — retry after a tick
    requestAnimationFrame(patchNavigate);
    return;
  }

  window.navigate = function(pageId) {
    _originalNavigate(pageId);

    // When results page is shown, update widget
    if (pageId === 'results') {
      try { SourceChecklist.updateReadinessWidget(); } catch (_) {}
    }
    // When overview page is shown after a company loads, refresh badge
    if (pageId === 'overview') {
      try { SourceChecklist.refresh(); } catch (_) {}
    }
  };
})();

// ─── Expose refreshChecklist globally ─────────────────────────────────────────
//
// The main app calls populateAllPages() after generation completes.
// We want to refresh the checklist state at that point.
// Hook by patching populateAllPages.
//
(function patchPopulateAllPages() {
  const _orig = window.populateAllPages;
  if (typeof _orig !== 'function') {
    requestAnimationFrame(patchPopulateAllPages);
    return;
  }
  window.populateAllPages = function(d) {
    _orig(d);
    try { SourceChecklist.refresh(); } catch (_) {}
  };
})();
