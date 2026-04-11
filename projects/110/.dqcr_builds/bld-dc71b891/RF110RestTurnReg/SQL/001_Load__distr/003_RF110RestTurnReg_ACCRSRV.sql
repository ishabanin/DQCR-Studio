-- build_id: bld-dc71b891
-- generated_at: 2026-04-10T21:42:10.107770+00:00
-- engine: dqcr
-- context: default
with b as (
  select config_type from config_table where config_group = 'reports'
),
a as (
  select max(config_type) as config_max_type
  from b
)
select 1 as test
from test_table t
    cross join a
where t.config_type in (select config_type from b)