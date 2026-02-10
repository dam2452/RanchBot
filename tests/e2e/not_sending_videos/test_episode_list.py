import pytest

import bot.responses.not_sending_videos.episode_list_handler_responses as msg
from tests.e2e.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestEpisodeListHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_episodes_for_valid_season(self):
        season_number = 4
        response = self.send_command(f'/odcinki {season_number}')
        self.assert_message_hash_matches(response, expected_key=f"episode_list_season_{season_number}.message")

    @pytest.mark.asyncio
    async def test_episodes_for_nonexistent_season(self):
        season_number = 99
        response = self.send_command(f'/odcinki {season_number}')
        self.assert_response_contains(
            response,
            [msg.get_no_episodes_found_message(season_number)],
        )

    @pytest.mark.asyncio
    async def test_episodes_without_season_shows_season_list(self):
        response = self.send_command('/odcinki')
        self.assert_message_hash_matches(response, expected_key="season_list.message")

    @pytest.mark.asyncio
    async def test_episodes_too_many_arguments(self):
        response = self.send_command('/odcinki 1 2')
        self.assert_response_contains(
            response,
            [msg.get_invalid_args_count_message()],
        )

    @pytest.mark.asyncio
    async def test_episodes_long_list(self):
        season_number = 3
        response = self.send_command(f'/odcinki {season_number}')
        self.assert_message_hash_matches(response, expected_key=f"episode_list_season_{season_number}_long.message")

    @pytest.mark.asyncio
    async def test_episodes_for_season_zero(self):
        season_number = 0
        response = self.send_command(f'/odcinki {season_number}')
        self.assert_message_hash_matches(response, expected_key=f"episode_list_season_{season_number}.message")
