/**
 * @fileoverview
 * SOURCE CHECKLIST — Auto-Completion Detection
 * Feature: source-checklist
 *
 * Derives checklist completion status directly from the existing
 * COMPANY_STATE.currentCompany profile data. No manual ticking required.
 *
 * Completion is always re-computed from profile data on load — it is
 * never stored separately, ensuring it stays in sync with the profile.
 */

'use strict';

/**
 * Returns the canonical set of checklist sections with auto-derived completion,
 * based on the currently filled business profile fields.
 *
 * @param {Object|null} currentCompany - COMPANY_STATE.currentCompany
 * @returns {Array<import('../types/checklistTypes').ChecklistItem>}
 */
function computeChecklistFromProfile(currentCompany) {
  const c   = (currentCompany && currentCompany.company)  || {};
  const b   = (currentCompany && currentCompany.business) || {};
  const g   = (currentCompany && currentCompany.goals)    || {};
  const f   = (currentCompany && currentCompany.finance)  || {};
  const t   = (currentCompany && currentCompany.team)     || {};
  const obj = (currentCompany && currentCompany.objective) || '';

  const profileId = c.name || '';

  /**
   * Helper: field has meaningful content (not empty / 'Not sure' / whitespace-only).
   * @param {string|undefined} val
   * @param {number} [minLen=1]
   * @returns {boolean}
   */
  function hasValue(val, minLen = 1) {
    if (!val) return false;
    const trimmed = String(val).trim();
    if (trimmed.length < minLen) return false;
    if (trimmed.toLowerCase() === 'not sure') return false;
    return true;
  }

  return [
    // ── 1: Company Information ─────────────────────────────────────────────
    {
      id:          'company-information',
      profileId,
      section:     'company_information',
      label:       'Company Information',
      description: 'Company name, industry, stage, and location',
      required:    true,
      completed:   hasValue(c.name) && hasValue(c.industry) && hasValue(c.stage),
    },

    // ── 2: Business Description ────────────────────────────────────────────
    {
      id:          'business-description',
      profileId,
      section:     'business_description',
      label:       'Business Description',
      description: 'What your company does and the core value proposition',
      required:    true,
      completed:   hasValue(b.description, 15),
    },

    // ── 3: Business Model ──────────────────────────────────────────────────
    {
      id:          'business-model',
      profileId,
      section:     'business_model',
      label:       'Business Model',
      description: 'How your company generates revenue (B2C, B2B, SaaS, etc.)',
      required:    true,
      completed:   hasValue(b.business_model),
    },

    // ── 4: Target Customers ────────────────────────────────────────────────
    {
      id:          'target-customers',
      profileId,
      section:     'target_customers',
      label:       'Target Customers',
      description: 'Who your primary customers are and their characteristics',
      required:    true,
      completed:   hasValue(b.target_customers, 10),
    },

    // ── 5: Problem Statement ──────────────────────────────────────────────
    {
      id:          'problem-statement',
      profileId,
      section:     'problem_statement',
      label:       'Problem Statement',
      description: 'The specific pain point your company addresses',
      required:    true,
      completed:   hasValue(b.problem, 10),
    },

    // ── 6: Solution / Product ──────────────────────────────────────────────
    {
      id:          'solution-product',
      profileId,
      section:     'solution_product',
      label:       'Solution / Product',
      description: 'How your product or service solves the problem',
      required:    true,
      completed:   hasValue(b.solution, 10),
    },

    // ── 7: Goals & Objectives ──────────────────────────────────────────────
    {
      id:          'goals-objectives',
      profileId,
      section:     'goals_objectives',
      label:       'Goals & Objectives',
      description: 'Primary goal and short-term or long-term objectives',
      required:    true,
      completed:   hasValue(g.primary_goal) && (hasValue(g.short_term, 10) || hasValue(g.long_term, 10)),
    },

    // ── 8: Financial Information ──────────────────────────────────────────
    {
      id:          'financial-information',
      profileId,
      section:     'financial_information',
      label:       'Financial Information',
      description: 'Budget, expected revenue, and funding status',
      required:    true,
      completed:   hasValue(f.budget) || hasValue(f.expected_revenue) || hasValue(f.monthly_budget),
    },

    // ── 9: Team Information ────────────────────────────────────────────────
    {
      id:          'team-information',
      profileId,
      section:     'team_information',
      label:       'Team Information',
      description: 'Team size, your role, skills, and active departments',
      required:    false,   // Optional — helpful but not blocking
      completed:   hasValue(t.size) && hasValue(t.founder_role),
    },

    // ── 10: CompanyOS Objective ────────────────────────────────────────────
    {
      id:          'companyos-objective',
      profileId,
      section:     'companyos_objective',
      label:       'CompanyOS Objective',
      description: 'The primary directive telling CompanyOS what to accomplish',
      required:    true,
      completed:   hasValue(obj, 20),
    },
  ];
}

/**
 * Computes the overall readiness summary from a list of checklist items.
 * @param {Array<import('../types/checklistTypes').ChecklistItem>} items
 * @returns {import('../types/checklistTypes').ChecklistReadiness}
 */
function computeReadiness(items) {
  const total            = items.length;
  const completed        = items.filter(i => i.completed).length;
  const required         = items.filter(i => i.required);
  const requiredTotal    = required.length;
  const requiredComplete = required.filter(i => i.completed).length;
  const percent          = total > 0 ? Math.round((completed / total) * 100) : 0;
  const isReady          = requiredComplete === requiredTotal;
  const missingRequired  = required.filter(i => !i.completed).map(i => i.label);

  return { total, completed, requiredTotal, requiredComplete, percent, isReady, missingRequired };
}
