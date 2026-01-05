import pytest

from bot.database.response_keys import ResponseKey as RK
from bot.tests.base_test import BaseTest


@pytest.mark.usefixtures("db_pool")
class TestDeleteClipHandler(BaseTest):

    @pytest.mark.asyncio
    async def test_delete_existing_clip(self):
        await self.send_command('/klip cytat')
        await self.send_command('/zapisz test_clip')
        await self.expect_command_result_contains(
            '/usunklip 1',
            [
                await self.get_response(
                    RK.CLIP_DELETED,
                    args=["test_clip"],
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_delete_nonexistent_clip(self):
        clip_id = 1337
        response = await self.send_command(f'/usunklip {clip_id}')
        await self.assert_response_contains(
            response,
            [
                await self.get_response(
                    RK.CLIP_NOT_EXIST,
                    args=[str(clip_id)],
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_delete_clip_no_arguments(self):
        response = await self.send_command('/usunklip')
        await self.assert_response_contains(
            response,
            [
                await self.get_response(
                    RK.INVALID_ARGS_COUNT,
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_delete_clip_invalid_argument_format(self):
        response = await self.send_command('/usunklip abc')
        await self.assert_response_contains(
            response,
            [
                await self.get_response(
                    RK.INVALID_ARGS_COUNT,
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_delete_multiple_clips(self):
        for clip_name in ("geniusz", "kozioł"):
            await self.send_command(f"/klip {clip_name}")
            await self.send_command(f"/zapisz {clip_name}")

        for clip_name in ("geniusz", "kozioł"):
            await self.expect_command_result_contains(
                "/usunklip 1",
                [
                    await self.get_response(
                        RK.CLIP_DELETED,
                        args=[clip_name],
                    ),
                ],
            )

    @pytest.mark.asyncio
    async def test_delete_clip_with_special_characters(self):
        special_clip_name = "spec@l_clip!"
        await self.send_command('/klip cytat specjalny')
        await self.send_command(f'/zapisz {special_clip_name}')

        await self.expect_command_result_contains(
            '/usunklip 1',
            [
                await self.get_response(
                    RK.CLIP_DELETED,
                    args=[special_clip_name],
                ),
            ],
        )

    @pytest.mark.asyncio
    async def test_delete_clip_invalid_index(self):
        clip_id = 999
        response = await self.send_command(f'/usunklip {clip_id}')
        await self.assert_response_contains(
            response,
            [
                await self.get_response(
                    RK.CLIP_NOT_EXIST,
                    args=[str(clip_id)],
                ),
            ],
        )
