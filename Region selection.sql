drop table if exists meetings_for_agent_cnt;
create table meetings_for_agent_cnt as
    select d.meeting_id
        , d.meeting_rk
        , d.final_planned_start_dttm::date as start_dt
        , d.meeting_region_dk as region_id
        , d.delivery_agent_rk
        , max(d.meeting_task_template_code) as meeting_task_template_code
        , max(d.task_status_code) as task_status_code
        , max(d.source_system_cd) as source_system_cd 
        from prod_v_sse_orig.delivery d
            left join prod_v_chrono_delivery_ags.regions_ags_prod r
                on d.meeting_region_dk = r.id
        where d.meeting_region_dk is not null
            and d.meeting_status_dttm + r.offset * interval '1 hour' > d.final_planned_start_dttm::date + interval '6 hours'
            and d.delivery_agent_rk is not null
            and d.final_planned_start_dttm::date between '2026-03-02'::date - 92 and '2026-03-02'::date - 3
            and (d.source_system_cd in ('MEE') or d.meeting_task_template_code in ('CarSearch', 'apd'))
            and r.auto_planning = true
            AND lower(r.detailed_name) NOT LIKE '%тест%'
            AND lower(r.detailed_name) NOT LIKE '%коллекшн%'
            AND lower(r.detailed_name) NOT LIKE '%биометрия%'
    group by 1,2,3,4,5
;

drop table if exists agents_for_agent_cnt;
create table agents_for_agent_cnt as
select region_id
, start_dt
, delivery_agent_rk
, count(*) as meeting_cnt
, count(*) as client_meeting_cnt
from meetings_for_agent_cnt
where delivery_agent_rk is not null
group by 1,2,3
;

drop table if exists regions_for_agent_cnt;
create table regions_for_agent_cnt as
select start_dt
, region_id
, sum(meeting_cnt) as meeting_cnt
, sum(client_meeting_cnt) as client_meeting_cnt
, count(*) as agent_cnt
from agents_for_agent_cnt
where client_meeting_cnt > 0
group by 1, 2
;

drop table if exists switchback_regions;
create table switchback_regions as
with t1 as (
select m.region_id
, round(avg(meeting_cnt), 2) as meeting_cnt
from regions_for_agent_cnt m
where start_dt between '2026-03-02'::date - 32 and '2026-03-02'::date - 3
group by m.region_id
having median(agent_cnt) >= 2
    and avg(agent_cnt) >= 2
    and count(*) > 10 

)
select 'new density 2026-03-02' as test
, *
, case when ROW_NUMBER() over (order by meeting_cnt desc) % 4 in (0, 1) then 1 else 0 end as group_id
from t1
;

select * , (case when lag(group_id, 1) over (order by meeting_cnt desc) = group_id then 1 end) as same
from switchback_regions
order by meeting_cnt desc
;

INSERT INTO usr_deliv.switchback_regions 
SELECT test::text, region_id, meeting_cnt, group_id 
FROM switchback_regions
;