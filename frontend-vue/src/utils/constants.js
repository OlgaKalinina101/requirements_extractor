/**
 * Shared application-wide constants.
 * Import from here instead of duplicating across components.
 *
 * @deprecated AVAILABLE_MODELS — prefer fetching from /api/models via useModelsStore.
 *            Kept as fallback when API is unavailable.
 */

export const AVAILABLE_MODELS = [
  { id: 'claude-sonnet-4.5', name: 'Claude Sonnet 4.5' },
  { id: 'claude-opus-4.6',   name: 'Claude Opus 4.6' },
  { id: 'gpt-4.1',           name: 'GPT-4.1' },
  { id: 'qwen-3.5-plus',     name: 'Qwen3.5 Plus 2026-02-15' },
  { id: 'gemini-3.1-pro',    name: 'Gemini 3.1 Pro Preview' },
]

/** Map model id → display name */
export const MODEL_DISPLAY_NAMES = Object.fromEntries(
  AVAILABLE_MODELS.map(m => [m.id, m.name])
)

export const DOCUMENT_STATUS_ICON = {
  pending:    'mdi-clock-outline',
  processing: 'mdi-loading',
  completed:  'mdi-check-circle',
  failed:     'mdi-alert-circle',
}

export const DOCUMENT_STATUS_COLOR = {
  pending:    'grey',
  processing: 'blue',
  completed:  'green',
  failed:     'red',
}

export const DOCUMENT_STATUS_TEXT = {
  pending:    'Ожидает',
  processing: 'Обработка',
  completed:  'Готово',
  failed:     'Ошибка',
}

export const ROLE_COLOR = {
  admin:            'error',
  manager:          'primary',
  department_head:  'teal',
}

export const ROLE_NAME = {
  admin:            'Администратор',
  manager:          'Менеджер',
  department_head:  'Руководитель отдела по задачам',
}
