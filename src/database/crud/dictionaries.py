"""Dictionary CRUD operations."""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from src.database.models import DictionaryItem

VALID_DICT_TYPES = {
    "requirement_types",
    "priorities",
    "statuses",
    "disciplines",
    "verification_methods",
    "link_types",
    "document_types",
}


def get_dictionary_items(db: Session, dict_type: str) -> List[DictionaryItem]:
    """Get all items for a given dictionary type, ordered by sort_order."""
    return (
        db.query(DictionaryItem)
        .filter(DictionaryItem.dict_type == dict_type)
        .order_by(DictionaryItem.sort_order.asc(), DictionaryItem.id.asc())
        .all()
    )


def get_dictionary_item(db: Session, item_id: int) -> Optional[DictionaryItem]:
    """Get dictionary item by ID."""
    return db.query(DictionaryItem).filter(DictionaryItem.id == item_id).first()


def create_dictionary_item(db: Session, dict_type: str, data: Dict[str, Any]) -> DictionaryItem:
    """Create a new dictionary item."""
    item = DictionaryItem(
        dict_type=dict_type,
        code=data.get("code"),
        name=data["name"],
        description=data.get("description"),
        color=data.get("color"),
        sort_order=data.get("sort_order", 0),
        is_active=data.get("is_active", True),
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_dictionary_item(db: Session, item_id: int, data: Dict[str, Any]) -> Optional[DictionaryItem]:
    """Update a dictionary item."""
    item = db.query(DictionaryItem).filter(DictionaryItem.id == item_id).first()
    if not item:
        return None
    for field in ("code", "name", "description", "color", "sort_order", "is_active"):
        if field in data:
            setattr(item, field, data[field])
    db.commit()
    db.refresh(item)
    return item


def delete_dictionary_item(db: Session, item_id: int) -> bool:
    """Delete a dictionary item."""
    item = db.query(DictionaryItem).filter(DictionaryItem.id == item_id).first()
    if not item:
        return False
    db.delete(item)
    db.commit()
    return True


def seed_dictionary_defaults(db: Session) -> None:
    """Populate dictionaries with default values if they are empty."""
    defaults = {
        "requirement_types": [
            {"code": "Supply", "name": "Supply", "description": "Состав поставки, перечень оборудования", "color": "blue-darken-1", "sort_order": 1},
            {"code": "Technical", "name": "Technical", "description": "Технические параметры и характеристики", "color": "cyan-darken-1", "sort_order": 2},
            {"code": "Functional", "name": "Functional", "description": "Функциональное поведение системы", "color": "green-darken-1", "sort_order": 3},
            {"code": "Performance", "name": "Performance", "description": "Производительность и метрики", "color": "teal-darken-1", "sort_order": 4},
            {"code": "Safety", "name": "Safety", "description": "Безопасность и защита", "color": "red-darken-1", "sort_order": 5},
            {"code": "Documentation", "name": "Documentation", "description": "Документирование и отчётность", "color": "brown", "sort_order": 6},
            {"code": "Interface", "name": "Interface", "description": "Интерфейсы и протоколы", "color": "purple", "sort_order": 7},
            {"code": "Constraint", "name": "Constraint", "description": "Ограничения и граничные условия", "color": "orange-darken-1", "sort_order": 8},
            {"code": "Process", "name": "Process", "description": "Процессы и рабочие процедуры", "color": "lime-darken-2", "sort_order": 9},
            {"code": "Unknown", "name": "Unknown", "description": "Тип не определён", "color": "grey", "sort_order": 10},
        ],
        "priorities": [
            {"code": "Mandatory", "name": "Mandatory", "description": "Обязательное требование", "color": "red", "sort_order": 1},
            {"code": "Recommended", "name": "Recommended", "description": "Рекомендуемое требование", "color": "orange", "sort_order": 2},
            {"code": "Optional", "name": "Optional", "description": "Необязательное требование", "color": "blue", "sort_order": 3},
            {"code": "Unknown", "name": "Unknown", "description": "Приоритет не определён", "color": "grey", "sort_order": 4},
        ],
        "statuses": [
            {"code": "pending", "name": "На рассмотрении", "description": "Ожидает проверки менеджером", "color": "orange", "sort_order": 1},
            {"code": "accepted", "name": "Принято", "description": "Требование подтверждено", "color": "green", "sort_order": 2},
            {"code": "rejected", "name": "Отклонено", "description": "Требование отклонено", "color": "red", "sort_order": 3},
            {"code": "modified", "name": "Изменено", "description": "Требование отредактировано", "color": "blue", "sort_order": 4},
            {"code": "in_progress", "name": "В работе", "description": "Исполнитель приступил", "color": "cyan", "sort_order": 5},
            {"code": "done", "name": "Выполнено", "description": "Исполнитель завершил", "color": "teal", "sort_order": 6},
            {"code": "blocked", "name": "Заблокировано", "description": "Выполнение заблокировано", "color": "grey", "sort_order": 7},
        ],
        "disciplines": [
            {"code": "Mechanical", "name": "Mechanical", "description": "Механика", "color": "blue", "sort_order": 1},
            {"code": "Electrical", "name": "Electrical", "description": "Электротехника", "color": "orange", "sort_order": 2},
            {"code": "I&C", "name": "I&C", "description": "КИПиА", "color": "cyan", "sort_order": 3},
            {"code": "Process", "name": "Process", "description": "Технология", "color": "green", "sort_order": 4},
            {"code": "Civil", "name": "Civil", "description": "Строительная часть", "color": "brown", "sort_order": 5},
            {"code": "HVAC", "name": "HVAC", "description": "Вентиляция и кондиционирование", "color": "teal", "sort_order": 6},
            {"code": "Piping", "name": "Piping", "description": "Трубопроводы", "color": "purple", "sort_order": 7},
            {"code": "Software", "name": "Software", "description": "Программное обеспечение", "color": "lime-darken-2", "sort_order": 8},
        ],
        "verification_methods": [
            {"code": "Analysis", "name": "Analysis", "description": "Анализ", "color": "blue", "sort_order": 1},
            {"code": "Test", "name": "Test", "description": "Испытание", "color": "green", "sort_order": 2},
            {"code": "Inspection", "name": "Inspection", "description": "Осмотр", "color": "orange", "sort_order": 3},
            {"code": "Demonstration", "name": "Demonstration", "description": "Демонстрация", "color": "purple", "sort_order": 4},
        ],
        "link_types": [
            {"code": "depends_on", "name": "Depends on", "description": "Зависит от", "color": "blue", "sort_order": 1},
            {"code": "conflicts_with", "name": "Conflicts with", "description": "Конфликтует с", "color": "red", "sort_order": 2},
            {"code": "derived_from", "name": "Derived from", "description": "Выведено из", "color": "green", "sort_order": 3},
            {"code": "parent_child", "name": "Parent/Child", "description": "Родитель/потомок", "color": "purple", "sort_order": 4},
        ],
        "document_types": [
            {"code": "TechnicalSpecification", "name": "Technical Specification", "description": "Техническая спецификация", "color": "blue", "sort_order": 1},
            {"code": "RequirementsDocument", "name": "Requirements Document", "description": "Документ требований", "color": "green", "sort_order": 2},
            {"code": "DesignDocument", "name": "Design Document", "description": "Проектная документация", "color": "purple", "sort_order": 3},
            {"code": "Other", "name": "Other", "description": "Прочее", "color": "grey", "sort_order": 4},
        ],
    }
    for dict_type, items in defaults.items():
        existing = db.query(DictionaryItem).filter(DictionaryItem.dict_type == dict_type).count()
        if existing == 0:
            for item_data in items:
                db.add(DictionaryItem(dict_type=dict_type, **item_data))
    db.commit()
