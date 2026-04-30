import aiohttp
import logging

from fancy_logger import fancy_logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from api_handler import RegionSettingsAPIClient
from scheduler_api import get_regions_for_target_date 

@fancy_logger
async def update_settings(api_client: RegionSettingsAPIClient, settings: List[Dict[str, Any]]) -> None:
    async with aiohttp.ClientSession() as session:
        await api_client.set_settings(session, settings)

# caching in order to aviod UI API
time_offsets = dict()

@fancy_logger
async def schedule_jobs(api_client: RegionSettingsAPIClient, scheduler: AsyncIOScheduler, minutes_before_midnight: int, target_date: Optional[str] = None) -> None:
    # UTC for convienience
    target_date = target_date or (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')

    regions_to_schedule = await get_regions_for_target_date(target_date)

    async with aiohttp.ClientSession() as session:
        for row in regions_to_schedule:
            region_id, is_test, test_rule_group_id, control_rule_group_id, experiment_name, experiment_date_start, experiment_date_end = row

            if region_id not in time_offsets:
                current_settings = await api_client.get_settings(session, region_id)
                time_offsets[region_id] = current_settings['data']['offset'] + 3 # since it's UTC+3 Moscow timezone
            time_offset = time_offsets[region_id]

            # making settings
            even_group_settings = [{'regionId': region_id, 'autoPlanning': {'ruleGroupId': control_rule_group_id, 'ruleGroupTodayId': test_rule_group_id}}]
            odd_group_settings = [{'regionId': region_id, 'autoPlanning': {'ruleGroupId': test_rule_group_id, 'ruleGroupTodayId': control_rule_group_id}}]

            experiment_settings = [even_group_settings, odd_group_settings][is_test]

            # time of settings change
            tommorow_start_utc = datetime.strptime(f'{target_date} 00:00:00', '%Y-%m-%d %H:%M:%S')
            tommorow_start_utc = tommorow_start_utc - timedelta(hours=time_offset, minutes=minutes_before_midnight)

            # swap to test settings 
            scheduler.add_job(
                update_settings, 
                'date', 
                run_date=tommorow_start_utc, 
                args=[api_client, experiment_settings], 
                timezone='UTC'
            )
            logging.info(f'Scheduled job for experiment {experiment_name} in region {region_id} at {tommorow_start_utc} setting to {experiment_settings}')

            # don't forget to put it all back
            if target_date < experiment_date_end:
                continue

            control_settings = [{'regionId': region_id, 'autoPlanning': {'ruleGroupId': control_rule_group_id, 'ruleGroupTodayId': control_rule_group_id}}]
            day_after_tommorow_start_utc = tommorow_start_utc + timedelta(days=1)

            scheduler.add_job(
                update_settings, 
                'date', 
                run_date=day_after_tommorow_start_utc, 
                args=[api_client, control_settings], 
                timezone='UTC'
            )
            logging.info(f'Scheduled revert job for experiment {experiment_name} in region {region_id} at {day_after_tommorow_start_utc} setting to {control_settings}')

