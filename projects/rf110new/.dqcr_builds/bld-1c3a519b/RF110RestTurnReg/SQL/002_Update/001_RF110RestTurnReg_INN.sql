-- build_id: bld-1c3a519b
-- generated_at: 2026-04-11T14:32:23.121830+00:00
-- engine: dqcr
-- context: default
select c.clientid,
       c.inn as clientinn
from _m.dwh.client c
where c.clienttype = 'ЮЛ'