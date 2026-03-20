WITH base AS (
  SELECT *
  FROM _w.001_Load.001_LoadSales
),
agg AS (
  SELECT
    clientid,
    SUM(amount) AS total_amount,
    MAX(created_at) AS created_at
  FROM base
  GROUP BY clientid
)
SELECT
  CAST(NULL AS NUMBER) AS dealid,
  a.clientid,
  a.total_amount AS amount,
  a.created_at,
  a.total_amount
FROM agg a
