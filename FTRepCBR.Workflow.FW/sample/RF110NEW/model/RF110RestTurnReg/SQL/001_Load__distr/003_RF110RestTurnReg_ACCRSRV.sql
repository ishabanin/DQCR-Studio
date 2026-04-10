with b as (
  select config_type from config_table where config_group = 'reports'
),
a as (
  select max(config_type) as config_max_type
  from b
)
select 1 as accountid, 2 as dealid, 3 as objectid, 4 as calcid
from test_table t
    cross join a
where t.config_type in (select config_type from b)