/*
@config(
  enabled: true
  materialized: insert_fc
)
*/
SELECT
  s.deal_id AS dealid,
  s.client_id AS clientid,
  s.amount,
  s.deal_date AS created_at,
  s.amount AS total_amount
FROM stg_sales s
WHERE s.status = 'APPROVED'
  AND s.deal_date >= {{date_start}}
  AND s.deal_date <= {{date_end}}
  AND s.amount >= {{min_amount}}
