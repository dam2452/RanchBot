import logging
from typing import (
    List,
    Optional,
)

import aiogram

from bot.factory.admin_permission_level_factory import AdminPermissionLevelFactory
from bot.factory.any_user_permission_level_factory import AnyUserPermissionLevelFactory
from bot.factory.moderator_permission_level_factory import ModeratorPermissionLevelFactory
from bot.factory.permission_level_factory import PermissionLevelFactory
from bot.factory.subscribed_permission_level_factory import SubscribedPermissionLevelFactory
from bot.factory.whitelisted_permission_level_factory import WhitelistedPermissionLevelFactory


def create_all_factories(logger: logging.Logger, bot: Optional[aiogram.Bot]) -> List[PermissionLevelFactory]:
    return [
        AdminPermissionLevelFactory(logger, bot),
        ModeratorPermissionLevelFactory(logger, bot),
        SubscribedPermissionLevelFactory(logger, bot),
        WhitelistedPermissionLevelFactory(logger, bot),
        AnyUserPermissionLevelFactory(logger, bot),
    ]
