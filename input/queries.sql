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
select
 date(d.killmail_time),
 e.main_pilot_name,
 t.typename,
 v.ship_type_id,
 t.mass,
 -- m.average_price,
 d.solar_system_id 
from seat.qview_employment_interval e
  left outer join seat.killmail_victims v on (v.character_id=e.pilot_id)
  left outer join seat.killmail_details d on (v.killmail_id=d.killmail_id)
  left outer join seat.invTypes t on (t.typeid=v.ship_type_id)
  -- left outer join seat.market_prices m on (m.type_id=v.ship_type_id)
where
 e.enter_time <= d.killmail_time and
 (e.gone_time is null or d.killmail_time <= e.gone_time)
order by d.killmail_time;
-- 2021-09-27	Zorky Graf Tumidus	Rhea	28844	960000000	30000168
-- 2021-09-27	Zorky Graf Tumidus	Capsule	670	32000.0	30000168

