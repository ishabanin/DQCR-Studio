# Sample DQCR Project

Этот пример проекта создан по `User_guide.md` и `Admin_guide.md`.

## Структура

- `project.yml` — конфигурация проекта
- `contexts/` — контексты `default` и `vtb`
- `parameters/` — глобальные параметры
- `model/SalesReport/` — модель с SQL-шагами и локальным параметром

## Быстрый старт (если FW доступен в окружении)

```bash
python -m FW.cli build "./sample" "SalesReport" -o output.json
python -m FW.cli validate "./sample" "SalesReport"
python -m FW.cli generate "./sample" "SalesReport" -w dqcr
```
