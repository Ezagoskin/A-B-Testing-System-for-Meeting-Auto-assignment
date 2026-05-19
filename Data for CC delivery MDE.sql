drop table if exists meetings;
create table meetings as
select d.meeting_id
, d.meeting_rk
, d.final_planned_start_dttm::date as start_dt
, d.meeting_region_dk as region_id
from prod_v_sse_orig.delivery d
    join usr_deliv.switchback_regions r3 
        on d.meeting_region_dk = r3.region_id
        and r3.test = $region_groups_name
    left join prod_v_chrono_delivery_ags.regions_ags_prod r
        on d.meeting_region_dk = r.id
where d.meeting_region_dk is not null
    and d.meeting_status_dttm + r.offset * interval '1 hour' > d.final_planned_start_dttm::date + interval '8 hours'
    and d.source_system_cd in ('MEE','SBL')
    and d.final_planned_start_dttm::date between $end_date - $exp_length - $start_dates_length + 2 and $end_date
    and d.final_planned_start_dttm::date not between '2025-05-01' and '2025-05-11'
    and not (d.initial_planned_start_dttm = d.task_create_dttm and d.meeting_region_dk not in (8, 12, 13, 44, 46, 47, 61, 62, 67, 71, 75, 76, 98, 102, 105, 108, 110, 130, 386, 398, 403, 411, 8501, 10181, 10446))
group by 1,2,3,4
;

drop table if exists all_meetings;
create table all_meetings as
select region_id
, start_dt
, count(*) as meeting_cnt
from meetings
group by 1, 2
;

select * from all_meetings limit 7
;

DROP TABLE IF EXISTS schedule;
CREATE TABLE schedule AS
SELECT das.delivery_district_dk
, das.schedule_dt 
, das.delivery_agent_rk
, a.id AS agent_id
, EXTRACT(EPOCH FROM (das.interval_end_tm - das.interval_start_tm)/3600.0) AS work_hours
FROM prod_v_sse_orig.delivery_agent_schedule das
JOIN prod_v_chrono_delivery_ags.agents_ags_prod a
ON das.delivery_agent_rk = a.employee_id
WHERE das.schedule_dt BETWEEN $end_date - $exp_length - $start_dates_length + 2 and $end_date
    and interval_code not like ('%Неподтверждено%')
    and interval_start_tm not in ('00:00:00', '00:01:00')
    and (
        lower(interval_code) like '%мск_%'
        or lower(interval_code) like '%полный%'
        or lower(interval_code) like '%самозанятый%'
        or lower(interval_code) like '%другое%'
        or lower(interval_code) like '%партнер%'
        or lower(interval_code) like '%совместитель%'
        or lower(interval_code) like '%свободный%'
        or lower(interval_code) like '%интервал%'
        or lower(interval_code) like '%утро%'
        or interval_code like '%Тест 13-19%'
        or lower(interval_code) like '%полевой%'
        or lower(interval_code) like '10%'
    --    or das.interval_code like '%АТМ%'
        or lower(interval_code) like '9%'
        or lower(interval_code) like '8%'
        or lower(interval_code) like '11%'
        or lower(interval_code) like '12%'
        or lower(interval_code) like '13%'
        or lower(interval_code) like '18%'
        or lower(interval_code) like '16%'
        or lower(interval_code) like '5/2%'
        or lower(interval_code) like 'вечер%'
        or lower(interval_code) like 'custom%'
        or lower(interval_code) like 'довозы'
        or lower(interval_code) like 'выборгская'
    )
    AND EXTRACT(EPOCH FROM (das.interval_end_tm - das.interval_start_tm)/3600.0) >= 1
GROUP BY 1,2,3,4,5
;

DROP TABLE IF EXISTS work_hours;
CREATE TABLE work_hours AS
select delivery_district_dk as region_id
, schedule_dt as start_dt
, sum(work_hours) as work_hours
from schedule
group by 1, 2
;

select * from work_hours limit 7
;

drop table if exists cc_meetings;
create table cc_meetings as
select d.meeting_id
, d.meeting_rk
, d.meeting_task_id
, d.final_planned_start_dttm::date as start_dt
, d.meeting_region_dk as region_id
, max(case 
        when cc.utilization_dt::date - d.final_planned_start_dttm::date <= 30 
            and cc.utilization_dt is not null
            and d.task_success_flg = 1 
            and d.task_status_code = 'Done' then 1
        else 0 end) util30_flg
, max(case 
    when d.task_success_flg = 1 
        and d.task_status_code = 'Done' then 1
    else 0 end) success_flg
, max(case when d.task_subtype_code in ('Primary', 'Soft Reject', 'Installment') then 1 else 0 end) as primary_plus_cc
, max(case when d.task_subtype_code in ('Primary') then 1 else 0 end) as primary_cc
from prod_v_sse_orig.delivery d
    join usr_deliv.switchback_regions r3 
        on d.meeting_region_dk = r3.region_id
        and r3.test = $region_groups_name
    left join prod_v_sse.cc_origination cc
        on d.application_rk = cc.financial_application_rk
    left join prod_v_chrono_delivery_ags.regions_ags_prod r
        on d.meeting_region_dk = r.id
where d.meeting_region_dk is not null
    and d.meeting_status_dttm + r.offset * interval '1 hour' > d.final_planned_start_dttm::date + interval '8 hours'
    and d.source_system_cd in ('MEE','SBL')
    and d.task_type_code in ('Credit Card')
    and d.final_planned_start_dttm::date between $end_date - $exp_length - $start_dates_length - 54 and $end_date
    and d.final_planned_start_dttm::date not between '2025-05-01' and '2025-05-11'
    and d.initial_planned_start_dttm <> d.initial_planned_end_dttm
    -- and not (d.initial_planned_start_dttm = d.task_create_dttm and d.meeting_region_dk not in (8, 12, 13, 44, 46, 47, 61, 62, 67, 71, 75, 76, 98, 102, 105, 108, 110, 130, 386, 398, 403, 411, 8501, 10181, 10446))
group by 1,2,3,4,5
;

select * from cc_meetings limit 7
;

drop table if exists cc_task_primary_56;
create table cc_task_primary_56 as
select region_id
, start_dt
, extract(DOW from start_dt) as weekday
, sum(util30_flg) as util
, sum(success_flg) as success
, count(*) as meeting_cnt
-- , max(size_group) as size_group
-- , max(r3) as r3
from cc_meetings
where primary_cc = 1
group by 1, 2, 3
;

select * from cc_task_primary_56 limit 7
;

drop table if exists usr_deliv.cc_task_primary_56;
create table usr_deliv.cc_task_primary_56 as
select cc.*
, m.meeting_cnt as meeting_cnt_all
, w.work_hours / m.meeting_cnt as workload
from cc_task_primary_56 cc
    join all_meetings m
    using(region_id, start_dt)
    join work_hours w
    using(region_id, start_dt) 

;

select * from usr_deliv.cc_task_primary_56 limit 7
;

drop table if exists usr_deliv.cc_task_primary_pre_56;
create table usr_deliv.cc_task_primary_pre_56 as
select m1.region_id
, m1.start_dt as exp_start_dt
, m2.weekday
, avg(m2.util) as util_pre
, avg(m2.success) as success_pre
, avg(m2.meeting_cnt) as meeting_cnt_pre
, max(sm.success_pre / sm.meeting_cnt_pre) as success_rate_pre_all
from usr_deliv.cc_task_primary_56 m1
    join usr_deliv.cc_task_primary_56 m2
    on m2.region_id = m1.region_id
    and m2.start_dt between m1.start_dt - 56 and m1.start_dt - 1
    join usr_deliv.successful_meetings_pre_56 sm
    on sm.region_id = m1.region_id
    and sm.exp_start_dt = m1.start_dt
where m1.start_dt between $end_date - $exp_length - $start_dates_length + 2 and $end_date - $exp_length + 1
    -- and m1.r3 = 1
group by 1, 2, 3
;

select * from usr_deliv.cc_task_primary_pre_56 limit 7
;

