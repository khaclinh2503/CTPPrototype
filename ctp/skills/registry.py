"""Handler registry — populated by handler modules during import.

Usage:
    # In a handler module (e.g., handlers/roll_handlers.py):
    from ctp.skills.registry import SKILL_HANDLERS
    def _handle_xe_do(player, ctx, cfg, engine):
        ...
    SKILL_HANDLERS["SK_XE_DO"] = _handle_xe_do

    # At game startup:
    from ctp.skills.registry import register_all
    register_all(engine)
"""

SKILL_HANDLERS: dict = {}
PENDANT_HANDLERS: dict = {}
PET_HANDLERS: dict = {}


def register_all(engine) -> None:
    """Register all handlers from registry dicts with a SkillEngine instance.

    Args:
        engine: SkillEngine instance to register handlers with.
    """
    for sid, fn in SKILL_HANDLERS.items():
        engine.register_skill(sid, fn)
    for pid, fn in PENDANT_HANDLERS.items():
        engine.register_pendant(pid, fn)
    for pid, fn in PET_HANDLERS.items():
        engine.register_pet(pid, fn)
