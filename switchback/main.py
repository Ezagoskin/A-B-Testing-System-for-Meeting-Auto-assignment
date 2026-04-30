import getpass
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from quart import jsonify, request, Response
from api_handler import RegionSettingsAPIClient
from settings_update_scheduler import schedule_jobs, update_settings
from scheduler_api import app
from fancy_logger import fancy_api_logger
from pydantic import BaseModel
from fancy_decorators import fancy_validate_request

# hyperparams
minutes_before_midnight = 2

# ags api intergration 
ui_login = 'e.zagoskin'
ui_password = getpass.getpass(prompt='ui password:')
back_login = 'svc_switchback_prod'
back_password = getpass.getpass(prompt='back password:')

api_client = RegionSettingsAPIClient(ui_login, ui_password, back_login, back_password)

# Scheduler setup
loop = asyncio.get_event_loop()
scheduler = AsyncIOScheduler()
scheduler.configure(event_loop=loop)
scheduler.start()

class TriggerScheduleDataModel(BaseModel):
    target_date: str

@app.route('/trigger_scheduler', methods=['POST'])
@fancy_api_logger
@fancy_validate_request(TriggerScheduleDataModel)
async def trigger_scheduler() -> Response:
    data = await request.get_json()

    await schedule_jobs(api_client, scheduler, minutes_before_midnight, data.get('target_date', None))

    response = jsonify({'success': True})
    response.status_code = 200

    return response

class AutoplanningDataModel(BaseModel):
    ruleGroupId: int
    ruleGroupTodayId: int

class SetRegionSettingsDataModel(BaseModel):
    regionId: int
    autoPlanning: AutoplanningDataModel

@app.route('/set_region_settings', methods=['POST'])
@fancy_api_logger
@fancy_validate_request(SetRegionSettingsDataModel)
async def set_region_settings() -> Response:
    data = await request.get_json()

    await update_settings(api_client, data)

    response = jsonify({'success': True})
    response.status_code = 200

    return response

@app.before_serving
async def startup():
    scheduler.add_job(schedule_jobs, 'cron', hour=0, minute=25, timezone='UTC', args=[api_client, scheduler, minutes_before_midnight])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=False, loop=loop)

