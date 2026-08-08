/**
 * @fileoverview
 * SOURCE CHECKLIST — Type Definitions (JSDoc)
 * Feature: source-checklist
 * All types used by the Source Checklist feature are documented here.
 */

'use strict';

/**
 * @typedef {'user_provided'|'company_document'|'financial_record'|'internal_data'|'market_research'|'website'|'existing_profile'|'other'} SourceType
 */

/**
 * @typedef {Object} ChecklistItemSource
 * @property {SourceType} sourceType       - How/where the info came from
 * @property {string}     sourceReference  - Short label/description of the source
 * @property {string}     notes            - Optional free-text notes
 * @property {string}     updatedAt        - ISO timestamp of last update
 */

/**
 * @typedef {Object} ChecklistItem
 * @property {string}            id              - Unique slug identifier e.g. "company-information"
 * @property {string}            profileId       - Company name (profile identifier)
 * @property {string}            section         - Section key e.g. "company_information"
 * @property {string}            label           - Human-readable label
 * @property {string}            description     - Short description of what this section covers
 * @property {boolean}           required        - Whether this section is required for generation
 * @property {boolean}           completed       - Auto-derived from profile data
 * @property {ChecklistItemSource} source        - User-entered source metadata (persisted)
 */

/**
 * @typedef {Object} ChecklistReadiness
 * @property {number}  total            - Total checklist items
 * @property {number}  completed        - Number of completed items
 * @property {number}  requiredTotal    - Total required items
 * @property {number}  requiredComplete - Completed required items
 * @property {number}  percent          - Overall completion percentage (0-100)
 * @property {boolean} isReady          - true if all required sections complete
 * @property {string[]} missingRequired - Labels of incomplete required sections
 */

/**
 * Source type display labels
 * @type {Object.<string, string>}
 */
const SOURCE_TYPE_LABELS = {
  user_provided:     'User provided',
  company_document:  'Company document',
  financial_record:  'Financial record',
  internal_data:     'Internal data',
  market_research:   'Market research',
  website:           'Website',
  existing_profile:  'Existing profile data',
  other:             'Other',
};

/**
 * Default source object for new items
 * @type {ChecklistItemSource}
 */
const DEFAULT_SOURCE = {
  sourceType:      'user_provided',
  sourceReference: '',
  notes:           '',
  updatedAt:       '',
};
