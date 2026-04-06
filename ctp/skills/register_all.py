"""Register all skill, pendant, and pet handlers with SkillEngine.

Imports all handler modules (which populate SKILL_HANDLERS, PENDANT_HANDLERS,
PET_HANDLERS in registry.py on import), then calls engine.register_* for each.
"""

# noqa: F401 — wildcard imports populate registry as side effects
from ctp.skills.handlers_roll import *          # SK_XXCT, SK_XE_DO, SK_MOONWALK
from ctp.skills.handlers_move import *          # SK_CAM_CO, SK_PHA_HUY
from ctp.skills.handlers_land_toll import *     # SK_BUA_SET, SK_NGOI_SAO, SK_CUONG_CHE
from ctp.skills.handlers_land_position import * # SK_SUNG_VANG, SK_LOC_XOAY
from ctp.skills.handlers_prison import *        # SK_JOKER, SK_HQXX
from ctp.skills.handlers_upgrade import *       # SK_TEDDY, SK_O_KY_DIEU, SK_MONG_NGUA
from ctp.skills.handlers_hybrid import *        # SK_LAU_DAI_TINH_AI, SK_AO_ANH, SK_BIEN_CAM
from ctp.skills.handlers_start import *         # SK_GRAMMY, SK_MU_PHEP
from ctp.skills.handlers_acquire import *       # SK_MC2, SK_TRUM_DU_LICH
from ctp.skills.handlers_multi import *         # SK_GAY_NHU_Y, SK_HO_DIEP, SK_SO_10
from ctp.skills.pendant_handlers_land import *  # PT_GIAY_BAY, PT_CUOP_NHA, PT_MANG_NHEN, PT_SIEU_TAXI
from ctp.skills.pendant_handlers_own import *   # PT_TU_TRUONG, PT_BAN_TAY_VANG, PT_TUI_BA_GANG, PT_KET_VANG
from ctp.skills.pendant_handlers_special import *  # PT_DKXX2, PT_XICH_NGOC, PT_CHONG_MUA_NHA, PT_SIEU_SAO_CHEP
from ctp.skills.pet_handlers import *           # PET_THIEN_THAN, PET_XI_CHO, PET_PHU_THU, PET_TROI_CHAN

from ctp.skills.registry import SKILL_HANDLERS, PENDANT_HANDLERS, PET_HANDLERS


def register_all_handlers(engine) -> None:
    """Register all 26 skill + 12 pendant + 4 pet handlers with a SkillEngine.

    Must be called after importing this module (the wildcard imports above
    already populate the registry dicts as a side effect).

    Args:
        engine: SkillEngine instance to register handlers with.
    """
    for sid, fn in SKILL_HANDLERS.items():
        engine.register_skill(sid, fn)
    for pid, fn in PENDANT_HANDLERS.items():
        engine.register_pendant(pid, fn)
    for pid, fn in PET_HANDLERS.items():
        engine.register_pet(pid, fn)
