from __future__ import annotations

from typing import Dict, Any, List
import discord
from discord.ui import View, Button

from bot.embeds.profile_embeds import (
    profile_embed,
    stats_embed,
    achievements_embed,
)
from database.database import db_manager
from database.repositories.achievement_repository import AchievementRepository
from services.study_service import study_service


class ProfileNavigationView(View):
    def __init__(self, target_user: discord.User | discord.Member, viewer_id: int):
        super().__init__(timeout=180)
        self.target_user = target_user
        self.viewer_id = viewer_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.viewer_id:
            await interaction.response.send_message("❌ This profile control is for someone else!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="👤 Overview", style=discord.ButtonStyle.primary, emoji="📋")
    async def btn_overview(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        profile_data = await study_service.get_user_profile(self.target_user.id, self.target_user.display_name)
        embed = profile_embed(profile_data, self.target_user)
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="📊 Stats", style=discord.ButtonStyle.secondary, emoji="📈")
    async def btn_stats(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        profile_data = await study_service.get_user_profile(self.target_user.id, self.target_user.display_name)
        embed = stats_embed(profile_data, self.target_user)
        await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="🏆 Badges", style=discord.ButtonStyle.secondary, emoji="✨")
    async def btn_achievements(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer()
        async with db_manager.session() as sess:
            ach_repo = AchievementRepository(sess)
            all_ach = await ach_repo.get_all_achievements()
            profile_data = await study_service.get_user_profile(self.target_user.id, self.target_user.display_name)
            unlocked_slugs = {item[0].slug for item in profile_data["achievements"]}

        embed = achievements_embed(all_ach, unlocked_slugs, self.target_user.display_name)
        await interaction.edit_original_response(embed=embed, view=self)
