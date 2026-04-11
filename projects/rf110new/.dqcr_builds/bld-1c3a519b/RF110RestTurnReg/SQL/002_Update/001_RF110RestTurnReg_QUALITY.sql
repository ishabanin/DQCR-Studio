-- build_id: bld-1c3a519b
-- generated_at: 2026-04-11T14:32:23.121830+00:00
-- engine: dqcr
-- context: default
/*
@config(
  description: обновление категории качества
)                   
*/    

with b as (
/*
@config(
              cte_materialization:
                 default: ephemeral
                 by_context: 
                   vtb: stage_calcid                                     
              attributes:
                 - name : t
                   domain_type: number
                   distribution_key: 1
)                   
*/    
    select 1 as t from tbl)
select r.DealID,
       r.FinInstrCategory,
       r.DateFrom
from _m.PSReg.PSRegister r
where r.CalcID = {{calc_psregister_id}}
and r.RowStatus = 'A'
and r.tt in (select 1 from b)