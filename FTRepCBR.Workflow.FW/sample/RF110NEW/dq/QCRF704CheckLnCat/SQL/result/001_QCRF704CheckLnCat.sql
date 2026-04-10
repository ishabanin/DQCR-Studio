/*
@config(
  description: Загрузка результата контроля категории кредита, кода актива и кода валюты по данным RF704TotalReg
)
*/
select /*+ parallel({{CPU_CORES}}) */
    /* порядок полей задается моделью */
    BranchCode,
    DealID,
    ContractNumber,
    CurrencyCode,
    ClientID,
    ClientName,

    DateDebt,
    DateAddContract,

    CodeLoanCategory,
    CodeAsset,

    Amount,
    AmountLong,

    MileageLess1000,
    GoodsPayment,
    IndivCondLoan,
    AcquirPropPledge,
    LimitExists,
    LoanTermDays,
    LoanPurpose,

    RecID,
    BranchID,
    DepartmentID,
    'Код катеригории кредита и код актива противоречат друг другу' as Description,
    1 as IsError,
    _p.props.repsysname as RepCode /* repsysname из Form0409704_WF/project.yml */
from (
        select r.ID as RecID,
            r.BranchID,
            br.BranchCode,
            0 as DepartmentID,
            r.DealID,
            r.ContractNumber,
            r.CurrencyCode,
            r.ClientID,
            r.ClientName,

            r.DateDebt,
            r.DateAddContract,

            r.CodeLoanCategory,
            r.CodeAsset,

            /* для get_enum_by_refrcode workflow добавит декодирование через case, чтобы не читать таблицы при каждом вызове функции
            *  например: case p.MileageLess1000 :RTC_CMN_BIN: end MileageLess1000
            *            где :RTC_CMN_BIN: это when...then...
            * wf_ - признак принадлежность к workflow
            */
            wf_get_enum_by_refrcode(r.MileageLess1000,'CMN_BIN')  MileageLess1000,
            wf_get_enum_by_refrcode(r.GoodsPayment,'CMN_BIN') as GoodsPayment,
            wf_get_enum_by_refrcode(r.IndivCondLoan,'CMN_BIN') as IndivCondLoan,
            wf_get_enum_by_refrcode(r.AcquirPropPledge,'CMN_BIN') as AcquirPropPledge,
            wf_get_enum_by_refrcode(r.LimitExists,'CMN_BIN') as LimitExists,
            r.AmountLong,
            r.LoanTermDays,
            wf_get_enum_by_refrcode(r.LoanPurpose,'LOAN_AIM') as LoanPurpose,
            r.Amount,

            row_number() over(partition by r.DealID order by 1) as rn
        from _m.Report-CBR-0409704.rf704totalreg r /* наименование таблицы/представления опредееляем через макрос model_ref/table.py*/

        left join dwr_tvBranch br
            on br.id = r.branchid
            and br.datebegin <= {{date_begin}}
            and br.dateend > {{date_end}}

        where r.CalcID = {{CALC_ID}}
            and r.RowStatus = 'A'
            and not r.SectionNum is null
            and r.LoanStatus != 'F704_DS_PD'
            and r.LoanPurpose != 'LOAN_AIM_IPTMIL'
            and r.LoanPurpose126 != 'LOAN_AIM_IPTMIL'
            and (r.DateAddContract >= {{Filter_DateAddContract}} or r.DateDebt >= {{Filter_DateDebt}})
            and (
                    (r.CodeLoanCategory in ('1.1','1.2') and r.CodeAsset != '6001')
                    or
                    (not r.CodeLoanCategory in ('1.1','1.2') and r.CodeAsset = '6001')
                    or
                    (r.CodeAsset = '6002' and r.CodeLoanCategory != 'Прочее')
                    or
                    (r.CodeAsset = '6003' and not r.CodeLoanCategory like '4%')
                    or
                    (r.CodeAsset = '7001' and r.CurrencyCode = '810')
                )
    ) rr
where rn = 1


    
