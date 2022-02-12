-- events-utf8.txt
select date(e.dt), e.lvl, e.txt
from (
  select min(enter_time) dt, 0 lvl, concat('Hello, ',main_pilot_name,' !') txt
  from seat.qview_employment_interval
  group by main_pilot_name
  union
  select enter_time, 1, concat(pilot_name, ' has come')
  from seat.qview_employment_interval
  union
  select gone_time, 2, concat(pilot_name, ' gone')
  from seat.qview_employment_interval
  where gone_time is not null
) e
order by e.dt, e.lvl;
-- 2019-10-01	0	Hello, Samurai Fruitblow !
-- 2019-10-01	1	Samurai Fruitblow has come
-- 2019-10-02	0	Hello, Solar Gryph !
-- 2019-10-02	1	Solar Gryph has come
-- 2019-10-03	0	Hello, Kaput RGB !
-- 2019-10-03	1	Kaput RGB has come
-- 2019-10-03	2	Kaput RGB gone

-- killmails-utf8.txt
select date(k.dt), k.victim, k.ship_type_id, k.mass, k.txt, k.solar_system_id
from (
 select
  d.killmail_time dt,
  1 victim,
  v.ship_type_id ship_type_id,
  t.mass mass,
  -- e.main_pilot_name,
  -- t.typename,
  concat(e.main_pilot_name, ' lost ', t.typename) txt,
  -- m.average_price,
  d.solar_system_id solar_system_id
 from seat.qview_employment_interval e
   left outer join seat.killmail_victims v on (v.character_id=e.pilot_id)
   left outer join seat.killmail_details d on (v.killmail_id=d.killmail_id)
   left outer join seat.invTypes t on (t.typeid=v.ship_type_id)
   -- left outer join seat.market_prices m on (m.type_id=v.ship_type_id)
 where
  e.enter_time <= d.killmail_time and
  (e.gone_time is null or d.killmail_time <= e.gone_time)
 union
 select
  d.killmail_time,
  0 victim, -- atacker(s)
  -- a.character_id,
  -- v.killmail_id,
  -- t.typename,
  v.ship_type_id,
  t.mass,
  case when c.cnt=1 then concat(t.typename, ' destroyed by ', e.main_pilot_name)
       else concat(t.typename, ' destroyed by ', c.cnt, ' pilots') -- ?involved?
  end txt,
  d.solar_system_id
  -- c.*
 from seat.killmail_victims v
  left outer join seat.killmail_details d on (v.killmail_id=d.killmail_id)
  left outer join (
    select killmail_id, min(character_id) character_id
    from seat.killmail_attackers
    group by 1) a on (a.killmail_id=v.killmail_id)
  left outer join (
    select a1.killmail_id, count(1) cnt, (
     select count(1)
     from seat.killmail_attackers a2
     where a1.killmail_id=a2.killmail_id and a2.corporation_id IN (98677876,98615601,98650099,98553333)
    ) ri4
    from seat.killmail_attackers a1
    group by 1) c on (c.killmail_id=v.killmail_id and c.ri4>0)
  left outer join seat.qview_employment_interval e on (e.pilot_id=a.character_id)
  left outer join seat.invTypes t on (t.typeid=v.ship_type_id)
 where c.ri4 is not null
) k
order by k.dt;
-- 2021-09-27	1	28844	960000000	Zorky Graf Tumidus lost Rhea	30000168
-- 2021-09-27	1	670	32000.0	Zorky Graf Tumidus lost Capsule	30000168

-- industry_jobs-utf8.txt
select
 j.dt,
 j.sum_jobs,
 j.solar_system_id
from (
 select
  j.ecj_start_date::date as dt,
  s.solar_system_id,
  -- j.ecj_activity_id,
  -- j.ecj_facility_id,
  count(1) sum_jobs
 from qi.esi_corporation_industry_jobs j
  left outer join qi.esi_known_stations s on (j.ecj_facility_id=s.location_id)
 group by 1, 2
) j
order by 1;
-- 2019-11-18	2	30004381
-- 2019-11-18	27	30004391

-- market-utf8.txt
select
 w.dt,
 coalesce(sta.system_id, str.solar_system_id) system_id,
 w.sum_price
from (
 select
  date(w.date) dt,
  w.location_id,
  ceil(sum(w.unit_price * w.quantity)) sum_price
 from seat.corporation_wallet_transactions w
 where corporation_id in (98677876,98615601,98650099,98553333)
 group by 1, 2
) w
 left outer join seat.universe_stations sta on (w.location_id=sta.station_id)
 left outer join seat.universe_structures str on (w.location_id=str.structure_id)
order by 1;
-- 2022-02-05	30045352	12998000
-- 2022-02-05	30000142	11631756263

-- employment_interval-utf8.txt
select
 main_pilot_id,
 pilot_id,
 main_pilot_name,
 pilot_name,
 date(enter_time),
 date(gone_time)
from seat.qview_employment_interval
order by 1, 2;
-- 93362315	91996495	Burenka Ololoev	Lord Brother Captain	2018-03-24	
-- 93362315	92932199	Burenka Ololoev	miztrezz	2018-12-18	


-- bounty_prizes-utf8.txt
select
 w.dt,
 w.system_id,
 w.sum_prizes * 10 -- 10% bounty
from (
 select
  date(w.date) dt,
  w.context_id as system_id,
  ceil(sum(w.amount)) sum_prizes
 from seat.corporation_wallet_journals w
 where corporation_id in (98677876,98615601,98650099,98553333) and w.ref_type='bounty_prizes'
 group by 1, 2
) w
order by 1;
-- 2019-11-08	30004313	24890.0
-- 2019-11-08	30004391	8550100.0