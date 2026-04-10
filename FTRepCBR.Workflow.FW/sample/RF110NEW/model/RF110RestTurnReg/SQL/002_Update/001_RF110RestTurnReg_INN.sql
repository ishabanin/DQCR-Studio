select /*@config(constraints: [PRIMARY_KEY])*/c.clientid,
       c.inn as clientinn
from _m.dwh.client c
where c.clienttype = 'ЮЛ'