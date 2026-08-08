/**
 * @fileoverview
 * SOURCE CHECKLIST — Sample Completed Record
 * Feature: source-checklist
 *
 * One fully-completed checklist record for BeanRush Coffee.
 * This is the bounty-required sample demonstrating all checklist
 * sections in a complete state.
 *
 * Source values use truthful labels only (no invented URLs or fake research).
 */

'use strict';

/**
 * BeanRush Coffee — fully completed source checklist record.
 * Profile key: "beanrush_coffee"
 *
 * This is loaded automatically when the BeanRush demo profile is active.
 * @type {Object.<string, import('../types/checklistTypes').ChecklistItemSource>}
 */
const BEANRUSH_SAMPLE_CHECKLIST = {
  'company-information': {
    sourceType:      'user_provided',
    sourceReference: 'Founder-provided company details',
    notes:           'BeanRush Coffee — Early Stage F&B startup in Chandigarh, India.',
    updatedAt:       '2026-08-08T04:00:00.000Z',
  },
  'business-description': {
    sourceType:      'user_provided',
    sourceReference: 'Founder-provided business description',
    notes:           'Specialty coffee kiosks with mobile app pre-ordering for students and young professionals.',
    updatedAt:       '2026-08-08T04:00:00.000Z',
  },
  'business-model': {
    sourceType:      'existing_profile',
    sourceReference: 'Existing profile data — B2C',
    notes:           'Direct consumer sales via kiosk and mobile app.',
    updatedAt:       '2026-08-08T04:00:00.000Z',
  },
  'target-customers': {
    sourceType:      'user_provided',
    sourceReference: 'Founder-provided customer segments',
    notes:           'Students 18–25 and young professionals 22–35 in Chandigarh.',
    updatedAt:       '2026-08-08T04:00:00.000Z',
  },
  'problem-statement': {
    sourceType:      'user_provided',
    sourceReference: 'Founder-identified market gap',
    notes:           'Lack of tech-enabled affordable specialty coffee in Chandigarh; long queues at existing cafes.',
    updatedAt:       '2026-08-08T04:00:00.000Z',
  },
  'solution-product': {
    sourceType:      'user_provided',
    sourceReference: 'Founder-defined product concept',
    notes:           'Mobile app-enabled grab-and-go kiosks with loyalty rewards in high-footfall areas.',
    updatedAt:       '2026-08-08T04:00:00.000Z',
  },
  'goals-objectives': {
    sourceType:      'user_provided',
    sourceReference: 'Founder-provided goals',
    notes:           'Launch Sector 17 location in 3 months. 5 locations in Punjab within 2 years.',
    updatedAt:       '2026-08-08T04:00:00.000Z',
  },
  'financial-information': {
    sourceType:      'user_provided',
    sourceReference: 'Founder-provided financial information',
    notes:           'Bootstrap budget ₹8.5 lakh. Expected ₹1.5 lakh/month by Month 3.',
    updatedAt:       '2026-08-08T04:00:00.000Z',
  },
  'team-information': {
    sourceType:      'internal_data',
    sourceReference: 'Internal team data',
    notes:           'Team of 2–5. Founder & CEO with coffee industry background.',
    updatedAt:       '2026-08-08T04:00:00.000Z',
  },
  'companyos-objective': {
    sourceType:      'user_provided',
    sourceReference: 'Founder-defined primary directive',
    notes:           'Complete go-to-market strategy, financial model, and marketing plan including mobile app strategy.',
    updatedAt:       '2026-08-08T04:00:00.000Z',
  },
};

/**
 * Returns true if the given company name matches the BeanRush demo profile.
 * @param {string|null|undefined} companyName
 * @returns {boolean}
 */
function isBeanRushProfile(companyName) {
  if (!companyName) return false;
  return companyName.trim().toLowerCase() === 'beanrush coffee';
}
