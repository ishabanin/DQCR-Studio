select distinct a2.ID, a2.AccountNumber
  from DWR_tRF110Settings s
       inner join {{RFAccGroupEl}} a
       inner join {{Account2}} a2
                  on a2.AccountNumber = a.AccountMask
                  and a2.DateBegin <= {{date_end}}
                  and a2.DateEnd > {{date_end}}
                  and a2.RowStatus = 'A'
  where s.RFFormProfileID = {{rfprofile_f110}}
  and s.Algorithm in ('F110_ALG_0','F110_ALG_4')
group by a2.ID, a2.AccountNumber