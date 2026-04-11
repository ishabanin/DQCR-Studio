-- build_id: bld-dc71b891
-- generated_at: 2026-04-10T21:42:10.107770+00:00
-- engine: dqcr
-- context: default
with /* Если клиент является адвокатом или нотариусом И одновременно управляющим, оставляем только одну запись */
                       ClientChr1_34 as 
                       (select distinct 
                               /* @config(distribution_key: 1) */                         
                               ClientID as ClientID 
		                      from _m.dwh.ClientChr
                         where DateBegin <= {{date_end}}
		                       and DateEnd > {{date_end}}
                           and {{clientchr_sql_filter}}
		                       and ClientCharacter in (1,34) --адвокат/нотариус, арбитражный управляющий 
                       )
                  select _m.RF110.RF110RestTurnReg.seq as ID,
                         {{calc_id}} as CalcID,
                         reg.BranchID as BranchID,
                         reg.ExternalClientID as ExternalClientID,
                         reg.RowStatus as RowStatus,
                         reg.VIP as VIP,
                         reg.AccountID as AccountID,
                         nvl(reg.ContractNumber,'test') as ContractNumber,
                         reg.DealID as DealID,
                         reg.AccountNumber as AccountNumber,
                         reg.Account2ID as Account2ID,
                         reg.Account2Number as Account2Number,
                         reg.CorrectObjectID as ObjectID,
                         reg.SumType as SumType,
                         reg.CorrectObjectBrief as ObjectBrief,
                         reg.CorrectObjectID as CorrectObjectID,
                         reg.CurrencyID as CurrencyID,
                         null as SecCategory,
                         reg.ClientID as ClientID,
                         coalesce(cjr.ClientType,reg.ClientType) as ClientType,
                         reg.Resident as ClientIsResident,
                         cjr.OwnershipFormID as ClientOwnershipFormID,
                         cjr.Authority as ClientAuthority,
                         case
                           when chr.ClientID is not null
                             then 'CMN_BIN_YES'
                           else 'CMN_BIN_NO'
                         end as IsLawyerNotary,
                         cjr.OffshoreResident as MinusLevy,
                         case
                         when coalesce(cjr.IsFinancial,'CMN_BIN_NULL') = 'CMN_BIN_NULL'
                           then 'CMN_BIN_NO'
                             else cjr.IsFinancial
                         end as IsFinOrg,
                         cjr.IsClearingMember as IsClearingMember,
                         reg.PaymentDelay as PaymentDelay,
                         reg.PaymentSumRur as OutRestRub,
                         reg.PaymentSumVal as OutRestVal,
                         reg.AccountName as AccountName,
                         reg.ClientName as ClientName,
                         NULL as LinkAccountID,
                         NULL as LinkAccountNumber,
                         NULL as LinkAccount2Number,
                         NULL as LinkCurrencyCode,
                         reg.SecurityID as SecurityID,
                         enum2str(sdr.DealKind) as LoanREPOKind,
                         null as SecKind,
                         reg.SecPortfolioID as SecPortfolioID,
                         case 
                           when reg.ClientID != acc.ClientID then 'CMN_BIN_YES'
                           else 'CMN_BIN_NO'
                         end as IsLoanGuarantor,
                         decode(cur.Type,:CUR_TP_ET_NUM:)  as CurrencyType,
                         cur.Code as CurrencyCode,
                         enum2str(acc.openingreason) as AccountOpeningReason,
                         NULL as DepositKind,
                         decode(cjr.COUNTRYCODE,'996','CMN_BIN_YES','CMN_BIN_NO') as IsInternational290FZ,
                         reg.ParentDealID,
                         reg.ParentContractNumber,
                         reg.AccountRole as AccountRole
                    from _m.AssetReg.AssetRegisterCor reg
                   inner join _w.001_Load_distr.RF110_Reg_Acc2 a
                           on a.Account2Number = reg.Account2Number
                   inner join _m.dwh.Account acc
                           on acc.ID = reg.AccountID 
                          and acc.DateBegin <= {{date_end}}
                          and acc.DateEnd > {{date_end}}
                    left join _m.ClientJurReg.ClientJurRegister cjr
                           on cjr.CalcID = {{calc_clientjurreg_id}}
                          and cjr.ClientID = reg.ClientID 
                    left join ClientChr1_34 chr
                           on chr.ClientID = reg.ClientID
                    left join _m.dwh.SecDealREPO sdr
                           on sdr.DateBegin <= {{date_end}}
                          and sdr.DateEnd > {{date_end}}
                          and sdr.RowStatus = 'A'
                          and sdr.MainDealID = reg.DealID
                    left join _m.dwh.Currency cur 
                           on cur.ID = acc.CurrencyID
                   where reg.CalcID = {{calc_astreg_id}}
                     and reg.LevelGroup = 0
                     and reg.RowStatus = 'A'
                     and (substr(reg.Account2Number,1,3) = '706' or abs(reg.ParentAccountID) != 1 )