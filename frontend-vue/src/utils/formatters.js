/**
 * Shared formatting helpers.
 * Pure functions — no Vue / Pinia dependencies.
 */

import {
  DOCUMENT_STATUS_ICON,
  DOCUMENT_STATUS_COLOR,
  DOCUMENT_STATUS_TEXT,
  ROLE_COLOR,
  ROLE_NAME,
} from './constants'

/**
 * Format an ISO date string to a short Russian locale string.
 * @param {string|null} dateString
 * @param {{ time?: boolean }} [opts]
 */
export function formatDate(dateString, { time = false } = {}) {
  if (!dateString) return ''
  const opts = { day: '2-digit', month: '2-digit', year: 'numeric' }
  if (time) {
    opts.hour = '2-digit'
    opts.minute = '2-digit'
  }
  return new Date(dateString).toLocaleDateString('ru-RU', opts)
}

export const getDocStatusIcon  = (s) => DOCUMENT_STATUS_ICON[s]  || 'mdi-file'
export const getDocStatusColor = (s) => DOCUMENT_STATUS_COLOR[s] || 'grey'
export const getDocStatusText  = (s) => DOCUMENT_STATUS_TEXT[s]  || s

export const getRoleColor = (role) => ROLE_COLOR[role] || 'secondary'
export const getRoleName  = (role) => ROLE_NAME[role]  || 'Пользователь'
