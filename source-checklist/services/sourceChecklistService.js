/**
 * @fileoverview
 * SOURCE CHECKLIST — Persistence Service
 * Feature: source-checklist
 *
 * Handles loading and saving of checklist SOURCE METADATA (sourceType,
 * sourceReference, notes) per business profile.
 *
 * Persistence strategy:
 *   - Primary: localStorage with key `cos_checklist_<profileKey>`
 *   - Backend: PUT /api/source-checklist/<profileKey> for server-side storage
 *
 * The checklist COMPLETION status is never stored — it is always
 * re-derived from profile data via checklistCompletion.js.
 *
 * Each company has its own isolated storage key so switching profiles
 * always loads the correct checklist.
 */

'use strict';

const SourceChecklistService = {

  /**
   * Converts a company name to a stable localStorage key segment.
   * @param {string} companyName
   * @returns {string} e.g. "beanrush_coffee"
   */
  _slug(companyName) {
    return companyName.trim().toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '');
  },

  /**
   * Returns the localStorage key for a given company name.
   * @param {string} companyName
   * @returns {string|null}
   */
  _key(companyName) {
    if (!companyName) return null;
    return 'cos_checklist_' + this._slug(companyName);
  },

  /**
   * Loads saved source metadata for a company.
   * Returns an object keyed by checklist item id.
   *
   * @param {string} companyName
   * @returns {Object.<string, import('../types/checklistTypes').ChecklistItemSource>}
   */
  load(companyName) {
    const key = this._key(companyName);
    if (!key) return {};
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      console.warn('[SourceChecklist] localStorage load failed:', e);
      return {};
    }
  },

  /**
   * Saves the entire source metadata object for a company.
   *
   * @param {string} companyName
   * @param {Object.<string, import('../types/checklistTypes').ChecklistItemSource>} metadata
   */
  save(companyName, metadata) {
    const key = this._key(companyName);
    if (!key) return;
    try {
      localStorage.setItem(key, JSON.stringify(metadata));
    } catch (e) {
      console.warn('[SourceChecklist] localStorage save failed:', e);
    }
    // Also persist to backend (fire-and-forget)
    this._syncToBackend(companyName, metadata);
  },

  /**
   * Updates a single checklist item's source metadata and persists.
   *
   * @param {string} companyName
   * @param {string} itemId
   * @param {{ sourceType?: string, sourceReference?: string, notes?: string }} updates
   * @returns {import('../types/checklistTypes').ChecklistItemSource}
   */
  updateItem(companyName, itemId, updates) {
    const data    = this.load(companyName);
    const current = data[itemId] || { ...DEFAULT_SOURCE };
    data[itemId]  = {
      sourceType:      updates.sourceType      !== undefined ? updates.sourceType      : current.sourceType,
      sourceReference: updates.sourceReference !== undefined ? updates.sourceReference : current.sourceReference,
      notes:           updates.notes           !== undefined ? updates.notes           : current.notes,
      updatedAt:       new Date().toISOString(),
    };
    this.save(companyName, data);
    return data[itemId];
  },

  /**
   * Clears saved checklist data for a company (e.g., on profile reset).
   * @param {string} companyName
   */
  clear(companyName) {
    const key = this._key(companyName);
    if (key) localStorage.removeItem(key);
  },

  /**
   * Loads the BeanRush sample checklist data into localStorage
   * if the profile matches BeanRush Coffee and no data has been saved yet.
   * This fulfils the "one completed sample record" bounty requirement.
   *
   * @param {string} companyName
   */
  seedSampleIfNeeded(companyName) {
    if (!isBeanRushProfile(companyName)) return;
    const key = this._key(companyName);
    if (!key) return;
    // Only seed if no data exists yet
    const existing = localStorage.getItem(key);
    if (!existing) {
      try {
        localStorage.setItem(key, JSON.stringify(BEANRUSH_SAMPLE_CHECKLIST));
        console.log('[SourceChecklist] Seeded BeanRush sample checklist data.');
      } catch (e) {
        console.warn('[SourceChecklist] Sample seed failed:', e);
      }
    }
  },

  /**
   * Syncs metadata to the backend API (fire-and-forget).
   * Falls back silently if the backend is unavailable.
   *
   * @param {string} companyName
   * @param {Object} metadata
   */
  _syncToBackend(companyName, metadata) {
    const profileKey = this._slug(companyName);
    const apiBase    = (typeof API_BASE !== 'undefined' ? API_BASE : '');
    fetch(`${apiBase}/api/source-checklist/${encodeURIComponent(profileKey)}`, {
      method:  'PUT',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ items: metadata }),
    }).catch(() => {
      // Backend unavailable — localStorage is the source of truth
    });
  },

  /**
   * Attempts to load metadata from the backend, merges with localStorage.
   * Called once on page load to ensure server state is not missed.
   *
   * @param {string} companyName
   * @returns {Promise<Object>}
   */
  async loadFromBackend(companyName) {
    const profileKey = this._slug(companyName);
    const apiBase    = (typeof API_BASE !== 'undefined' ? API_BASE : '');
    try {
      const res = await fetch(`${apiBase}/api/source-checklist/${encodeURIComponent(profileKey)}`);
      if (!res.ok) return this.load(companyName);
      const json    = await res.json();
      const local   = this.load(companyName);
      // Merge: prefer whichever entry has a more recent updatedAt
      const merged  = { ...json.items, ...local };
      // For conflicts, pick the newer one
      for (const id of Object.keys(json.items || {})) {
        if (local[id]) {
          const serverTs = new Date(json.items[id].updatedAt || 0).getTime();
          const localTs  = new Date(local[id].updatedAt || 0).getTime();
          merged[id]     = localTs >= serverTs ? local[id] : json.items[id];
        }
      }
      this.save(companyName, merged);
      return merged;
    } catch (_) {
      return this.load(companyName);
    }
  },
};
