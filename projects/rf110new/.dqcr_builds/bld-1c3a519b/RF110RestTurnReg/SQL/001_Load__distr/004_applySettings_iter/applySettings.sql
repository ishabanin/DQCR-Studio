-- build_id: bld-1c3a519b
-- generated_at: 2026-04-11T14:32:23.121830+00:00
-- engine: dqcr
-- context: default
select dealid, {{sett.strnum}}
from register
where account2 = {{sett.account2}}