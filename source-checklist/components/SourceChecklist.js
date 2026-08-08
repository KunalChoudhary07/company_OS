/**
 * @fileoverview
 * SOURCE CHECKLIST — Main Component
 * Feature: source-checklist
 *
 * Renders the Source Checklist page and manages all UI interactions:
 * - Page rendering with profile selector
 * - Per-item completion (auto-derived) + source metadata (user-entered)
 * - Overall progress bar and readiness indicator
 * - Mini readiness widget rendered on the Results page
 * - Persists source metadata via SourceChecklistService
 *
 * All functions are namespaced under the `SourceChecklist` global object.
 * No framework dependencies — vanilla JS matching the existing app style.
 */

'use strict';

const SourceChecklist = (() => {

  // ─── Internal State ──────────────────────────────────────────────────────

  let _currentCompanyName = null;   // Active company name
  let _items              = [];     // Current checklist items (merged)
  let _sourceData         = {};     // Saved source metadata keyed by item id
  let _expandedItemId     = null;   // Which item's source panel is open
  let _loading            = false;

  // ─── Helpers ─────────────────────────────────────────────────────────────

  /**
   * Returns the current company name from COMPANY_STATE.
   * @returns {string|null}
   */
  function _getCompanyName() {
    return (typeof COMPANY_STATE !== 'undefined' &&
            COMPANY_STATE.currentCompany &&
            COMPANY_STATE.currentCompany.company &&
            COMPANY_STATE.currentCompany.company.name) || null;
  }

  /**
   * Merge computed items (from profile data) with saved source metadata.
   * @param {Array} computed
   * @param {Object} saved
   * @returns {Array}
   */
  function _mergeItems(computed, saved) {
    return computed.map(item => ({
      ...item,
      source: saved[item.id] ? { ...DEFAULT_SOURCE, ...saved[item.id] } : { ...DEFAULT_SOURCE },
    }));
  }

  /**
   * Builds a progress bar HTML string.
   * @param {number} pct  0-100
   * @returns {string}
   */
  function _progressBar(pct) {
    return `
      <div class="cl-progress-track">
        <div class="cl-progress-fill" style="width:${pct}%"></div>
      </div>`;
  }

  /**
   * Returns a source type <select> HTML for the given item.
   * @param {string} itemId
   * @param {string} currentType
   * @returns {string}
   */
  function _sourceTypeSelect(itemId, currentType) {
    const options = Object.entries(SOURCE_TYPE_LABELS).map(([val, label]) =>
      `<option value="${val}" ${val === currentType ? 'selected' : ''}>${label}</option>`
    ).join('');
    return `<select class="checklist-source-select" id="src-type-${itemId}" aria-label="Source type">${options}</select>`;
  }

  // ─── Rendering ───────────────────────────────────────────────────────────

  /**
   * Renders a single checklist item card.
   * @param {import('../types/checklistTypes').ChecklistItem & { source: object }} item
   * @param {boolean} isExpanded
   * @returns {string} HTML
   */
  function _renderItem(item, isExpanded) {
    const done        = item.completed;
    const requiredCls = item.required ? 'required' : 'optional';
    const itemCls     = done
      ? 'completed'
      : `incomplete ${requiredCls}`;

    const iconCls = done ? 'done' : `pending ${requiredCls}`;
    const iconName = done ? 'check_circle' : 'radio_button_unchecked';
    const iconStyle = done
      ? 'font-variation-settings:\'FILL\' 1'
      : 'font-variation-settings:\'FILL\' 0';

    const hasSource = item.source && (item.source.sourceReference || item.source.notes);
    const sourceSummary = hasSource
      ? `<span class="cl-source-summary has-source">
           <span class="material-symbols-outlined text-[12px]">link</span>
           ${SOURCE_TYPE_LABELS[item.source.sourceType] || 'User provided'} · ${item.source.sourceReference || '—'}
         </span>`
      : `<span class="cl-source-summary">
           <span class="material-symbols-outlined text-[12px]">add_circle</span>
           Add source
         </span>`;

    const expandIconName = isExpanded ? 'expand_less' : 'expand_more';

    const panelOpen = isExpanded ? 'open' : '';
    const savedRef  = (item.source && item.source.sourceReference) ? item.source.sourceReference : '';
    const savedNotes = (item.source && item.source.notes) ? item.source.notes : '';

    return `
      <div class="checklist-item ${itemCls}" id="cl-item-${item.id}">
        <div class="checklist-item-header" onclick="SourceChecklist.toggleExpand('${item.id}')" aria-expanded="${isExpanded}" aria-controls="cl-panel-${item.id}">
          <div class="checklist-status-icon ${iconCls}" aria-hidden="true">
            <span class="material-symbols-outlined text-[16px]" style="${iconStyle}">${iconName}</span>
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex items-center justify-between gap-4">
              <div class="flex items-center gap-2">
                <span class="font-body-md text-[14px] font-medium ${done ? 'text-on-surface' : 'text-on-surface-variant'}">${item.label}</span>
                <span class="checklist-badge ${requiredCls}">${item.required ? 'REQUIRED' : 'OPTIONAL'}</span>
              </div>
            </div>
            <div class="mt-1">${sourceSummary}</div>
          </div>
          <span class="material-symbols-outlined text-[20px] text-outline checklist-expand-icon transition-transform ${isExpanded ? 'rotate-180' : ''}" style="flex-shrink:0">${expandIconName}</span>
        </div>

        <div class="checklist-source-panel ${panelOpen}" id="cl-panel-${item.id}" role="region" aria-label="Source information for ${item.label}">
          <div class="bg-surface-container rounded-b-lg p-5 space-y-4 border border-t-0 border-outline-variant/30">
            <div class="flex items-center gap-1.5 font-mono-sm text-[11px] mb-2 ${done ? 'text-primary-container' : 'text-outline'}">
              <span class="material-symbols-outlined text-[14px]" style="${iconStyle}">${iconName}</span>
              <span class="uppercase tracking-wider">${done ? 'Complete' : 'Incomplete'} · ${item.required ? 'REQUIRED' : 'OPTIONAL'}</span>
            </div>
            <p class="font-body-sm text-[12px] text-on-surface-variant">${item.description}</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label class="form-label" for="src-type-${item.id}">Source Type</label>
                ${_sourceTypeSelect(item.id, (item.source && item.source.sourceType) || 'user_provided')}
              </div>
              <div>
                <label class="form-label" for="src-ref-${item.id}">Source / Reference</label>
                <input
                  type="text"
                  id="src-ref-${item.id}"
                  class="form-input"
                  placeholder="e.g. Founder-provided, Annual report, Market survey…"
                  value="${_escHtml(savedRef)}"
                  autocomplete="off"
                />
              </div>
            </div>
            <div>
              <label class="form-label" for="src-notes-${item.id}">Notes <span style="font-weight:400;text-transform:none;color:#516368;">(optional)</span></label>
              <textarea
                id="src-notes-${item.id}"
                class="form-input"
                rows="2"
                placeholder="Any additional context about this source…"
              >${_escHtml(savedNotes)}</textarea>
            </div>
            <div class="flex items-center gap-3">
              <button
                class="cl-save-btn"
                id="cl-save-btn-${item.id}"
                onclick="SourceChecklist.saveSource('${item.id}')"
                aria-label="Save source for ${item.label}"
              >
                <span class="material-symbols-outlined text-[14px]">save</span>
                Save Source
              </button>
              <span id="cl-save-confirm-${item.id}" class="font-mono-sm text-[11px] text-primary-container hidden">
                <span class="material-symbols-outlined text-[13px] align-middle">check_circle</span> Saved
              </span>
            </div>
          </div>
        </div>
      </div>`;
  }

  /**
   * Renders the full checklist page into #source-checklist-root.
   */
  function _renderPage() {
    const root = document.getElementById('source-checklist-root');
    if (!root) return;

    const companyName = _getCompanyName();

    // ── Empty state: no company ──────────────────────────────────────────
    if (!companyName) {
      root.innerHTML = `
        <div class="cl-empty fade-in-up">
          <div class="cl-empty-icon">
            <span class="material-symbols-outlined text-primary-container text-[24px]">checklist</span>
          </div>
          <h2 class="font-headline-md text-[18px] text-on-surface mb-2">No Business Profile Selected</h2>
          <p class="font-body-md text-[13px] text-on-surface-variant mb-6 max-w-xs">Create or configure your company profile to see the source checklist.</p>
          <button onclick="handleCreateCompany()" class="flex items-center gap-2 bg-primary-container text-on-primary-container font-label-md text-[13px] font-semibold px-6 py-2.5 rounded-DEFAULT hover:bg-primary-fixed transition-colors">
            <span class="material-symbols-outlined text-[16px]">add_business</span>
            Create Company
          </button>
        </div>`;
      return;
    }

    // ── Compute readiness ────────────────────────────────────────────────
    const readiness = computeReadiness(_items);
    const { total, completed, requiredTotal, requiredComplete, percent, isReady, missingRequired } = readiness;
    const optionalTotal = total - requiredTotal;

    const statusHtml = isReady
      ? `<div class="cl-status-ready"><span class="material-symbols-outlined text-[16px]" style="font-variation-settings:'FILL' 1">check_circle</span>Ready for generation</div>`
      : `<div class="cl-status-incomplete"><span class="material-symbols-outlined text-[16px]">warning</span>${missingRequired.length} required section${missingRequired.length !== 1 ? 's' : ''} need${missingRequired.length === 1 ? 's' : ''} attention</div>`;

    const missingHtml = !isReady && missingRequired.length > 0
      ? `<div class="card rounded-xl p-4 border-error/20 bg-error-container/5 mt-2">
           <p class="font-label-md text-[11px] text-error uppercase tracking-widest mb-2">Missing Required Sections</p>
           <ul class="space-y-1">
             ${missingRequired.map(l => `<li class="flex items-center gap-2 font-body-md text-[13px] text-on-surface-variant"><span class="material-symbols-outlined text-[14px] text-error">error</span>${l}</li>`).join('')}
           </ul>
           <button onclick="navigate('onboarding')" class="mt-3 flex items-center gap-1.5 text-[12px] text-primary-container hover:underline font-label-md">
             <span class="material-symbols-outlined text-[14px]">edit</span>Complete Missing Sections
           </button>
         </div>`
      : '';

    // ── Profile pill ─────────────────────────────────────────────────────
    const industry = COMPANY_STATE.currentCompany?.company?.industry || '';
    const stage    = COMPANY_STATE.currentCompany?.company?.stage    || '';

    // ── Checklist items HTML ──────────────────────────────────────────────
    const required = _items.filter(i => i.required);
    const optional = _items.filter(i => !i.required);

    const itemsHtml = [
      ...required.map(i => _renderItem(i, _expandedItemId === i.id)),
      optional.length > 0 ? `<div class="pt-2"><p class="font-label-md text-[11px] text-outline uppercase tracking-widest mb-3">Optional Sections</p></div>` : '',
      ...optional.map(i => _renderItem(i, _expandedItemId === i.id)),
    ].join('');

    root.innerHTML = `
      <div class="fade-in-up space-y-6">

        <!-- ── Page Header ──────────────────────────────────────────────── -->
        <div class="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div class="flex items-center gap-2 mb-1">
              <span class="material-symbols-outlined text-primary-container text-[20px]">checklist</span>
              <h1 class="font-headline-lg text-[28px] font-semibold text-on-surface">Source Checklist</h1>
            </div>
            <p class="font-body-md text-[13px] text-on-surface-variant">
              Check required business profile inputs and sources before generation.
            </p>
          </div>
          <div class="flex flex-col items-end gap-2">
            <div class="cl-profile-pill">
              <span class="material-symbols-outlined text-[16px] text-primary-container" style="font-variation-settings:'FILL' 1">business</span>
              <span class="font-semibold">${_escHtml(companyName)}</span>
              ${industry ? `<span class="text-outline text-[11px] font-mono-sm">· ${_escHtml(industry)}</span>` : ''}
            </div>
            ${stage ? `<span class="font-mono-sm text-[10px] text-outline">${_escHtml(stage)}</span>` : ''}
          </div>
        </div>

        <!-- ── Progress Card ────────────────────────────────────────────── -->
        <div class="card rounded-xl p-6 space-y-5">
          <div class="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
            <div>
              <h2 class="font-headline-md text-[18px] text-on-surface mb-2">Profile Readiness</h2>
              <div class="space-y-1">
                <p class="font-mono-sm text-[12px] text-on-surface-variant">${completed} / ${total} sections complete</p>
                <p class="font-mono-sm text-[11px] text-outline">${requiredComplete} / ${requiredTotal} required · ${optionalTotal} optional</p>
              </div>
            </div>
            <div class="flex flex-col items-start sm:items-end gap-1">
              <span class="font-headline-lg text-[32px] text-on-surface font-semibold leading-none mb-1">${percent}<span class="text-[20px] text-outline font-normal">%</span></span>
              ${statusHtml}
            </div>
          </div>
          <div>
            ${_progressBar(percent)}
            <div class="flex justify-between mt-1.5">
              <span class="font-mono-sm text-[10px] text-outline">0%</span>
              <span class="font-mono-sm text-[10px] text-outline">100%</span>
            </div>
          </div>
        </div>

        ${missingHtml}

        <!-- ── Checklist Items ───────────────────────────────────────────── -->
        <div class="space-y-3">
          ${itemsHtml}
        </div>

        <!-- ── Footer hint ──────────────────────────────────────────────── -->
        <p class="font-mono-sm text-[11px] text-outline text-center pb-4">
          Completion is automatically derived from your business profile. Edit profile fields to update checklist status.
        </p>
      </div>`;
  }

  /**
   * Renders or updates the mini readiness widget inside #checklist-readiness-widget
   * (on the Results/Review page).
   */
  function _renderReadinessWidget() {
    const widget = document.getElementById('checklist-readiness-widget');
    if (!widget) return;

    const companyName = _getCompanyName();
    if (!companyName || _items.length === 0) {
      widget.classList.add('hidden');
      return;
    }

    const { total, completed, requiredTotal, requiredComplete, percent, isReady } = computeReadiness(_items);

    const statusIcon = isReady
      ? '<span class="material-symbols-outlined text-[16px] text-primary-container" style="font-variation-settings:\'FILL\' 1">check_circle</span>'
      : '<span class="material-symbols-outlined text-[16px] text-tertiary-fixed-dim">warning</span>';

    const statusText = isReady
      ? `<span class="font-body-md text-[13px] text-primary-container font-medium">All required sections complete</span>`
      : `<span class="font-body-md text-[13px] text-tertiary-fixed-dim font-medium">${requiredTotal - requiredComplete} required section${(requiredTotal - requiredComplete) !== 1 ? 's' : ''} incomplete</span>`;

    widget.classList.remove('hidden');
    widget.innerHTML = `
      <div class="cl-readiness-widget fade-in-up">
        <div class="w-9 h-9 rounded-lg bg-primary-container/10 border border-primary-container/20 flex items-center justify-center flex-shrink-0">
          <span class="material-symbols-outlined text-primary-container text-[18px]">checklist</span>
        </div>
        <div class="flex-1 min-w-0">
          <p class="font-label-md text-[11px] text-on-surface-variant uppercase tracking-widest mb-0.5">Profile Readiness</p>
          <div class="flex items-center gap-2 flex-wrap">
            ${statusIcon}
            ${statusText}
          </div>
          <p class="font-mono-sm text-[11px] text-outline mt-0.5">${completed} / ${total} complete · ${requiredComplete} / ${requiredTotal} required · ${percent}%</p>
        </div>
        <div class="flex-shrink-0">
          ${_progressBar(percent)}
          <div class="font-mono-sm text-[10px] text-outline mt-1">${percent}% ready</div>
        </div>
        <button
          onclick="navigate('source-checklist'); SourceChecklist.onNavigate();"
          class="flex items-center gap-1.5 text-primary-container hover:text-primary-fixed font-label-md text-[12px] transition-colors flex-shrink-0"
          aria-label="View Source Checklist"
        >
          View Checklist <span class="material-symbols-outlined text-[14px]">arrow_forward</span>
        </button>
      </div>`;
  }

  // ─── Helpers ─────────────────────────────────────────────────────────────

  /**
   * Escapes HTML special characters to prevent XSS.
   * @param {string} str
   * @returns {string}
   */
  function _escHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  /**
   * Updates the sidebar badge showing completion ratio.
   */
  function _updateSidebarBadge() {
    const badge = document.getElementById('checklist-nav-badge');
    if (!badge) return;
    const companyName = _getCompanyName();
    if (!companyName || _items.length === 0) {
      badge.textContent = '';
      return;
    }
    const { completed, total, isReady } = computeReadiness(_items);
    badge.textContent = isReady ? '✓' : `${completed}/${total}`;
    badge.style.color = isReady ? '#00e5ff' : '#849396';
  }

  // ─── Public API ──────────────────────────────────────────────────────────

  return {

    /**
     * Called when the user navigates to the Source Checklist page.
     * Re-derives checklist from current profile and renders.
     */
    onNavigate() {
      const companyName = _getCompanyName();

      if (companyName !== _currentCompanyName) {
        // Company changed — re-initialise
        _currentCompanyName = companyName;
        _expandedItemId     = null;
        _sourceData         = {};
      }

      if (companyName) {
        // Seed BeanRush sample data if needed (first visit)
        SourceChecklistService.seedSampleIfNeeded(companyName);

        // Load saved source metadata
        _sourceData = SourceChecklistService.load(companyName);

        // Compute items from profile, merge with saved source data
        const computed = computeChecklistFromProfile(
          typeof COMPANY_STATE !== 'undefined' ? COMPANY_STATE.currentCompany : null
        );
        _items = _mergeItems(computed, _sourceData);
      } else {
        _items = [];
      }

      _renderPage();
      this.updateReadinessWidget();
      _updateSidebarBadge();
    },

    /**
     * Toggle the source info panel for a specific item.
     * @param {string} itemId
     */
    toggleExpand(itemId) {
      _expandedItemId = (_expandedItemId === itemId) ? null : itemId;
      // Re-render just the relevant items without full page re-render
      _items.forEach(item => {
        const panel = document.getElementById(`cl-panel-${item.id}`);
        const header = document.querySelector(`#cl-item-${item.id} .checklist-expand-icon`);
        if (!panel) return;
        const isOpen = item.id === _expandedItemId;
        panel.classList.toggle('open', isOpen);
        if (header) {
          header.classList.toggle('rotate-180', isOpen);
          header.textContent = isOpen ? 'expand_less' : 'expand_more';
        }
        // Update aria-expanded
        const headerEl = document.querySelector(`#cl-item-${item.id} .checklist-item-header`);
        if (headerEl) headerEl.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
      });
    },

    /**
     * Saves source info for a specific item from its form inputs.
     * @param {string} itemId
     */
    saveSource(itemId) {
      const companyName = _getCompanyName();
      if (!companyName) return;

      const typeEl  = document.getElementById(`src-type-${itemId}`);
      const refEl   = document.getElementById(`src-ref-${itemId}`);
      const notesEl = document.getElementById(`src-notes-${itemId}`);

      const updates = {
        sourceType:      typeEl  ? typeEl.value  : 'user_provided',
        sourceReference: refEl   ? refEl.value   : '',
        notes:           notesEl ? notesEl.value : '',
      };

      const saved = SourceChecklistService.updateItem(companyName, itemId, updates);

      // Update in-memory item source
      const item = _items.find(i => i.id === itemId);
      if (item) item.source = saved;

      // Reload _sourceData
      _sourceData = SourceChecklistService.load(companyName);

      // Update the source summary line in the header without full re-render
      const summaryEl = document.querySelector(`#cl-item-${itemId} .cl-source-summary`);
      if (summaryEl) {
        const hasSource = saved.sourceReference || saved.notes;
        summaryEl.className = `cl-source-summary ${hasSource ? 'has-source' : ''}`;
        summaryEl.innerHTML = hasSource
          ? `<span class="material-symbols-outlined text-[12px]">link</span>${SOURCE_TYPE_LABELS[saved.sourceType] || 'User provided'} · ${_escHtml(saved.sourceReference) || '—'}`
          : `<span class="material-symbols-outlined text-[12px]">add_circle</span>Add source`;
      }

      // Show "Saved" confirmation
      const confirmEl = document.getElementById(`cl-save-confirm-${itemId}`);
      const btnEl     = document.getElementById(`cl-save-btn-${itemId}`);
      if (confirmEl) {
        confirmEl.classList.remove('hidden');
        if (btnEl) { btnEl.classList.add('saved'); btnEl.querySelector('span:first-child').textContent = 'check'; btnEl.childNodes[btnEl.childNodes.length - 1].textContent = ' Saved'; }
        setTimeout(() => {
          confirmEl.classList.add('hidden');
          if (btnEl) { btnEl.classList.remove('saved'); btnEl.querySelector('span:first-child').textContent = 'save'; btnEl.childNodes[btnEl.childNodes.length - 1].textContent = ' Save Source'; }
        }, 2500);
      }

      _updateSidebarBadge();
    },

    /**
     * Refreshes the checklist when the business profile data changes.
     * Called after profile updates.
     */
    refresh() {
      if (!_currentCompanyName) return;
      const computed = computeChecklistFromProfile(
        typeof COMPANY_STATE !== 'undefined' ? COMPANY_STATE.currentCompany : null
      );
      _items = _mergeItems(computed, _sourceData);
      // If we're on the source-checklist page, re-render
      const page = document.getElementById('page-source-checklist');
      if (page && page.classList.contains('active')) {
        _renderPage();
      }
      this.updateReadinessWidget();
      _updateSidebarBadge();
    },

    /**
     * Updates the mini readiness widget on the results page.
     * Call this whenever the results page is shown or data changes.
     */
    updateReadinessWidget() {
      const companyName = _getCompanyName();
      if (!companyName && _items.length === 0) {
        const widget = document.getElementById('checklist-readiness-widget');
        if (widget) widget.classList.add('hidden');
        return;
      }
      _renderReadinessWidget();
    },

    /**
     * Gets the current readiness summary for external use.
     * @returns {import('../types/checklistTypes').ChecklistReadiness|null}
     */
    getReadiness() {
      if (_items.length === 0) return null;
      return computeReadiness(_items);
    },

    /**
     * Initialises the checklist state from storage on app startup.
     * Called once from DOMContentLoaded handler in index.js.
     */
    init() {
      const companyName = _getCompanyName();
      if (!companyName) return;

      _currentCompanyName = companyName;

      // Seed BeanRush sample
      SourceChecklistService.seedSampleIfNeeded(companyName);

      // Load saved source data
      _sourceData = SourceChecklistService.load(companyName);

      // Compute initial items
      const computed = computeChecklistFromProfile(
        typeof COMPANY_STATE !== 'undefined' ? COMPANY_STATE.currentCompany : null
      );
      _items = _mergeItems(computed, _sourceData);

      _updateSidebarBadge();
      this.updateReadinessWidget();
    },
  };

})();
