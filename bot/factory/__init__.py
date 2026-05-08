import logging
from typing import List

from bot.factory.admin_permission_level_factory import AdminPermissionLevelFactory
from bot.factory.any_user_permission_level_factory import AnyUserPermissionLevelFactory
from bot.factory.moderator_permission_level_factory import ModeratorPermissionLevelFactory
from bot.factory.permission_level_factory import PermissionLevelFactory
from bot.factory.subscribed_permission_level_factory import SubscribedPermissionLevelFactory
from bot.factory.whitelisted_permission_level_factory import WhitelistedPermissionLevelFactory


def create_all_factories(logger: logging.Logger) -> List[PermissionLevelFactory]:
    return [
        AdminPermissionLevelFactory(logger),
        ModeratorPermissionLevelFactory(logger),
        SubscribedPermissionLevelFactory(logger),
        WhitelistedPermissionLevelFactory(logger),
        AnyUserPermissionLevelFactory(logger),
    ]
