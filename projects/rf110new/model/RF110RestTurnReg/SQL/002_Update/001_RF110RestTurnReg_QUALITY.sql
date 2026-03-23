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