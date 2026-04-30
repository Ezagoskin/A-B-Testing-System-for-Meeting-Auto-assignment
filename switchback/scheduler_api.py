import aiosqlite

from datetime import datetime
from pydantic import BaseModel
from quart import Quart, request, jsonify, Response
from typing import List, Tuple
from fancy_logger import fancy_api_logger
from fancy_decorators import fancy_validate_request

app = Quart(__name__)

async def init_db() -> None:
    async with aiosqlite.connect('experiment_schedule.db') as db:
        await db.execute(
            '''
            CREATE TABLE IF NOT EXISTS experiment_schedule (
                region_id INT,
                control_rule_group_id INT,
                test_rule_group_id INT,
                group_id INT,
                experiment_date_start DATE,
                experiment_date_end DATE,
                experiment_name TEXT
            )
            '''
        )

        await db.commit()

async def insert_into_db(rows: List[Tuple]) -> None:
    async with aiosqlite.connect('experiment_schedule.db') as db:
        await db.executemany('INSERT INTO experiment_schedule VALUES (?, ?, ?, ?, ?, ?, ?)', rows)

        await db.commit()

async def get_regions_for_target_date(target_date: str) -> List[Tuple]:
    days_since_epoch = (datetime.strptime(target_date, '%Y-%m-%d') - datetime(1970,1,1)).days
    request = f'''
        SELECT 
            region_id,
            (group_id + {days_since_epoch}) % 2 as is_test,
            test_rule_group_id,
            control_rule_group_id,
            experiment_name,
            experiment_date_start,
            experiment_date_end
            FROM experiment_schedule 
            WHERE experiment_date_start <= ? AND experiment_date_end >= ?
    '''

    async with aiosqlite.connect('experiment_schedule.db') as db:
        async with db.execute(request, (target_date, target_date)) as cursor:
            return [tuple(row) for row in await cursor.fetchall()]

async def change_experiment_dates(experiment_name: str, new_start_date: str, new_end_date: str) -> None:
    async with aiosqlite.connect('experiment_schedule.db') as db:
        await db.execute(
            'UPDATE experiment_schedule SET experiment_date_start = ?, experiment_date_end = ? WHERE experiment_name = ?', 
            (new_start_date, new_end_date, experiment_name)
        )

        await db.commit()

class ScheduleExperimentsItem(BaseModel):
    region_id: int
    control_rule_group_id: int
    test_rule_group_id: int
    group_id: int
    experiment_date_start: str
    experiment_date_end: str
    experiment_name: str

class ScheduleExperimentsDataModel(BaseModel):
    items: List[ScheduleExperimentsItem]

@app.route('/schedule_experiments', methods=['POST'])
@fancy_api_logger
@fancy_validate_request(ScheduleExperimentsDataModel)
async def api_schedule_experiment() -> Response:
    data = await request.get_json()

    rows = [
        (
            item["region_id"], 
            item["control_rule_group_id"], 
            item["test_rule_group_id"], 
            item["group_id"], 
            item["experiment_date_start"], 
            item["experiment_date_end"], 
            item["experiment_name"]
        ) for item in data['items']
    ]

    await init_db()
    await insert_into_db(rows)

    response = jsonify({'success': True})
    response.status_code = 200

    return response

class GetRegionsDataModel(BaseModel):
    target_date: str

@app.route('/get_regions_for_target_date', methods=['POST'])
@fancy_api_logger
@fancy_validate_request(GetRegionsDataModel)
async def api_get_regions_for_target_date() -> Response:
    data = await request.get_json()
    
    await init_db()

    regions = await get_regions_for_target_date(data['target_date'])
    
    response = jsonify(regions)
    response.status_code = 200

    return response

class ChangeExperimentDatesDataModel(BaseModel):
    experiment_name: str
    new_start_date: str
    new_end_date: str

@app.route('/change_experiment_dates', methods=['POST'])
@fancy_api_logger
@fancy_validate_request(ChangeExperimentDatesDataModel)
async def api_change_experiment_dates() -> Response:
    data = await request.get_json()

    await init_db()
    await change_experiment_dates(data['experiment_name'], data['new_start_date'], data['new_end_date'])

    response = jsonify({'success': True})
    response.status_code = 200

    return response
