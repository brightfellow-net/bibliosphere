def require_id(entity_id: int | None) -> int:
    """Narrow an entity's Optional id once persistence guarantees it is set."""
    assert entity_id is not None
    return entity_id
