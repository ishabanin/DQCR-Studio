-- build_id: bld-dc71b891
-- generated_at: 2026-04-10T21:42:10.107770+00:00
-- engine: dqcr
-- context: default
select c.clientid,
       c.inn as clientinn
from _m.dwh.client c
where c.clienttype = 'ЮЛ'