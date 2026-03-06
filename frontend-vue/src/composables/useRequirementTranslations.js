/**
 * Composable for translating requirement types and priorities to Russian
 */

export function useRequirementTranslations() {
  const typeTranslations = {
    'Technical': 'Техническое',
    'Functional': 'Функциональное',
    'Performance': 'Производительность',
    'Safety': 'Безопасность',
    'Documentation': 'Документационное',
    'Interface': 'Интерфейс',
    'Constraint': 'Ограничение',
    'Process': 'Процесс',
    'Supply': 'Поставка',
    'Unknown': 'Неизвестно'
  }

  const priorityTranslations = {
    'Mandatory': 'Обязательное',
    'Recommended': 'Рекомендованное',
    'Optional': 'Опциональное',
    'Unknown': 'Неизвестно'
  }

  const translateType = (type) => {
    if (!type) return ''
    return typeTranslations[type] || type
  }

  const translatePriority = (priority) => {
    if (!priority) return ''
    return priorityTranslations[priority] || priority
  }

  return {
    translateType,
    translatePriority,
    typeTranslations,
    priorityTranslations
  }
}
