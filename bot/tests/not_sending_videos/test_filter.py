import pytest

import bot.responses.not_sending_videos.filter_handler_responses as msg
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestFilterHandlerBasic(BaseTest):

    @pytest.mark.asyncio
    async def test_filter_no_args(self):
        response = self.send_command('/filtr')
        self.assert_response_contains(response, [msg.get_no_args_message()])

    @pytest.mark.asyncio
    async def test_filter_no_args_alias_filter(self):
        response = self.send_command('/filter')
        self.assert_response_contains(response, [msg.get_no_args_message()])

    @pytest.mark.asyncio
    async def test_filter_no_args_alias_f(self):
        response = self.send_command('/f')
        self.assert_response_contains(response, [msg.get_no_args_message()])

    @pytest.mark.asyncio
    async def test_filter_reset(self):
        response = self.send_command('/filtr reset')
        self.assert_response_contains(response, [msg.get_filter_reset_message()])

    @pytest.mark.asyncio
    async def test_filter_info_no_filters(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr info')
        self.assert_response_contains(response, ["Brak aktywnych filtrów"])

    @pytest.mark.asyncio
    async def test_filter_info_after_set(self):
        self.send_command('/filtr reset')
        self.send_command('/filtr sezon:3')
        response = self.send_command('/filtr info')
        self.assert_response_contains(response, ["Sezony"])

    @pytest.mark.asyncio
    async def test_filter_reset_clears_filters(self):
        self.send_command('/filtr sezon:1')
        self.send_command('/filtr reset')
        response = self.send_command('/filtr info')
        self.assert_response_contains(response, ["Brak aktywnych filtrów"])

    @pytest.mark.asyncio
    async def test_filter_set_combined(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr sezon:2 postac:Pawlak emocja:radosny')
        assert response.status_code == 200
        self.assert_response_contains(response, ["Sezony", "Postaci", "Emocje"])


@pytest.mark.usefixtures("db_pool")
class TestFilterHandlerSetFilters(BaseTest):

    @pytest.mark.asyncio
    async def test_filter_set_season(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr sezon:1')
        self.assert_response_contains(response, ["Sezony"])

    @pytest.mark.asyncio
    async def test_filter_set_season_range(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr sezon:1-3')
        self.assert_response_contains(response, ["Sezony"])

    @pytest.mark.asyncio
    async def test_filter_set_season_list(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr sezon:1,2,3')
        self.assert_response_contains(response, ["Sezony"])

    @pytest.mark.asyncio
    async def test_filter_set_episode(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr odcinek:S01E05')
        self.assert_response_contains(response, ["Odcinki"])

    @pytest.mark.asyncio
    async def test_filter_set_episode_range(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr odcinek:S01E03-S01E07')
        self.assert_response_contains(response, ["Odcinki"])

    @pytest.mark.asyncio
    async def test_filter_set_character(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr postac:Pawlak')
        self.assert_response_contains(response, ["Postaci"])

    @pytest.mark.asyncio
    async def test_filter_set_multiple_characters(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr postac:Pawlak,Kusy')
        self.assert_response_contains(response, ["Postaci"])

    @pytest.mark.asyncio
    async def test_filter_set_emotion(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr emocja:radosny')
        self.assert_response_contains(response, ["Emocje"])

    @pytest.mark.asyncio
    async def test_filter_set_object(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr obiekt:krzeslo')
        self.assert_response_contains(response, ["Obiekty"])

    @pytest.mark.asyncio
    async def test_filter_set_object_with_operator(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr obiekt:krzeslo>3')
        self.assert_response_contains(response, ["Obiekty"])


@pytest.mark.usefixtures("db_pool")
class TestFilterHandlerAliasesAndErrors(BaseTest):

    @pytest.mark.asyncio
    async def test_filter_alias_s_for_season(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr s:2')
        self.assert_response_contains(response, ["Sezony"])

    @pytest.mark.asyncio
    async def test_filter_alias_ep_for_episode(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr ep:S02E01')
        self.assert_response_contains(response, ["Odcinki"])

    @pytest.mark.asyncio
    async def test_filter_alias_p_for_character(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr p:Pawlak')
        self.assert_response_contains(response, ["Postaci"])

    @pytest.mark.asyncio
    async def test_filter_alias_e_for_emotion(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr e:radosny')
        self.assert_response_contains(response, ["Emocje"])

    @pytest.mark.asyncio
    async def test_filter_alias_o_for_object(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr o:krzeslo')
        self.assert_response_contains(response, ["Obiekty"])

    @pytest.mark.asyncio
    async def test_filter_alias_t_for_title(self):
        self.send_command('/filtr reset')
        response = self.send_command('/filtr t:testowy')
        self.assert_response_contains(response, ["Tytuł"])

    @pytest.mark.asyncio
    async def test_filter_invalid_token_no_colon(self):
        response = self.send_command('/filtr nieznany')
        self.assert_response_contains(response, ["BŁĄD"])

    @pytest.mark.asyncio
    async def test_filter_unknown_key(self):
        response = self.send_command('/filtr nieznany:wartosc')
        self.assert_response_contains(response, ["BŁĄD"])

    @pytest.mark.asyncio
    async def test_filter_invalid_season_format(self):
        response = self.send_command('/filtr sezon:abc')
        self.assert_response_contains(response, ["BŁĄD"])

    @pytest.mark.asyncio
    async def test_filter_invalid_episode_format(self):
        response = self.send_command('/filtr odcinek:nieParsuje')
        self.assert_response_contains(response, ["BŁĄD"])
