# Проект коррекции IPC (МПК)

## Вводная часть

**Улучшение результатов автоматической классификации заявок на изобретения по МПК**

Для поддержки экспертов в патентной экспертизе ранее была разработана система
многоклассовой классификации патентных заявок по МПК*.
Базовая модель обучена на большом массиве патентных текстов и обеспечивает
точность порядка 70–85%, в зависимости от конкретных классов.

В рамках данного проекта предлагается разработать дополнительную модель,
которая корректирует предсказания базовой модели и повышает итоговую
точность классификации.
Обучение новой модели основано на сравнении автоматически назначенных
классов с классами, присвоенными экспертами в ходе реальной экспертизы
заявок.

Планируется, что модель будет регулярно переобучаться (например, ежемесячно)
на данных очередного патентного бюллетеня. Такой подход позволяет учитывать
новые публикации, изменения в распределении тематик и постепенно улучшать
качество автоматической классификации.

* МПК (IPC — International Patent Classification) — международная патентная классификация, иерархическая система кодов, используемая патентными ведомствами для отнесения изобретений к техническим областям. [Подробнее на Википедии]
[mpk-wiki]: https://ru.wikipedia.org/wiki/%D0%9C%D0%B5%D0%B6%D0%B4%D1%83%D0%BD%D0%B0%D1%80%D0%BE%D0%B4%D0%BD%D0%B0%D1%8F_%D0%BF%D0%B0%D1%82%D0%B5%D0%BD%D1%82%D0%BD%D0%B0%D1%8F_%D0%BA%D0%BB%D0%B0%D1%81%D1%81%D0%B8%D1%84%D0%B8%D0%BA%D0%B0%D1%86%D0%B8%D1%8F

---

## Задача и общая идея

Проект решает задачу ранжирования IPC-кодов (МПК) для патентных заявок.
На вход подаются кандидаты IPC, сгенерированные базовой моделью, на выходе —
более точный рейтинг этих кандидатов и выбор лучшего набора кодов для эксперта.

Мы реализовали полностью автоматизированный контур для обучения, отбора и
развёртывания модели ранжирования IPC-кодов, включающий:

- инфраструктуру как код (Terraform);
- CI/CD на GitHub Actions;
- мониторинг (Prometheus + Grafana);
- нагрузочное тестирование;
- регулярное переобучение и выбор champion‑модели.

Архитектура строится вокруг Kubernetes-кластера в Yandex Cloud, в котором
крутится HTTP API с моделью, сервисы мониторинга и отдельное нагрузочное
приложение для проверки производительности.

---

## Общая архитектура

Высокоуровневая схема выглядит так:

- **Object Storage (S3)**  
  Хранит:
  - исходные и подготовленные датасеты (parquet);
  - артефакты кандидатов (модели, метрики);
  - production champion‑модель и её метаданные.

- **Airflow + Dataproc + MLflow**  
  - Airflow оркестрирует подготовку данных, обучение нескольких кандидатов
    и выбор champion-модели.
  - Dataproc запускает training jobs.
  - MLflow используется как tracking и registry-слой: параметры, метрики,
    версии моделей, alias для production.

- **Kubernetes + API модели**  
  - Kubernetes-кластер в Yandex Cloud.
  - Deployment с API (FastAPI/аналог), который читает champion‑модель
    из prod‑бакета.
  - Service типа LoadBalancer для внешнего доступа.

- **Мониторинг и нагрузка**  
  - Prometheus + Grafana для метрик и дашбордов в YC.
  - Отдельный Python-скрипт для нагрузочного тестирования API.

---

## Репозитории

Для развёртывания проекта необходимы три репозитория:

1. **API модели в Kubernetes (correct_ipc_model_api)**  
   HTTP API модели, развёртывание в Kubernetes и мониторинг в стеке
   Prometheus–Grafana.  
   Репозиторий:  
   <https://github.com/VladimirLapushkin/correct_ipc_model_api.git>

2. **Очистка данных и обучение модели (correct_ipc_airflow)**  
   Код подготовки данных, обучения кандидатов и выбора champion-модели
   (Airflow, MLflow).  
   Репозиторий:  
   <https://github.com/VladimirLapushkin/correct_ipc_airflow.git>

3. **DAG-скрипты для Airflow (airflow_dags)**  
   Отдельный репозиторий DAG’ов, которые Airflow подтягивает из Git.  
   Репозиторий:  
   <https://github.com/VladimirLapushkin/airflow_dags.git>

---

## Контракты между компонентами

### Формат данных в Object Storage

- **Исходные-датасеты** в `ipc/data/`:
  - pub - ежемесячные бюллетени публикаций в zip архивах;
  - lst - рефераты заявок со списком ранее предсказанных IPC кодов базовой моделью.
    
- **Parquet-датасеты** в `ipc/dataprep`:
  - `patent_id` — идентификатор заявки;
  - дата / месяц публикации;
  - список экспертных IPC-кодов;
  - список IPC-кодов, предложенных базовой моделью;
  - score и rank каждого кандидата.

- **Long-format датасет** для обучения:
  - одна строка — пара «патент — кандидатный IPC-код»;
  - сохраняются: сам IPC-код, main group, subgroup, позиция в рейтинге, score
    базовой модели;
  - из кода дополнительно извлекаются `section`, `class2`, `subclass`,
    `main_group`, `subgroup`.

- **Production-модель**:
  - champion-модель: `prod/champion/model.cbm`;
  - метаданные champion: `prod/champion/meta.json`;
  - предыдущий champion: `prod/previous/...`.

### Контракт Airflow → API

- Airflow гарантирует, что в prod‑бакете всегда лежит:
  - текущий champion (model.cbm + meta.json);
  - предыдущая версия модели (для rollback).
- API сервис при старте:
  - читает модель и метаданные только из фиксированного S3-пути;
  - не обращается напрямую к MLflow Registry.

---

## Предварительные шаги

### 1. Terraform

Установить Terraform и выполнить `terraform init`:

- для репозитория **correct_ipc_model_api**:
  - каталоги `infra` и `monitoring`;
- для репозитория **correct_ipc_airflow**:
  - каталог `infra`.

### 2. Настройка Yandex Cloud

- Создать сервисный аккаунт.
- Выдать права на:
  - управление Kubernetes-кластером;
  - доступ к S3-бакетам;
  - операции с Container Registry (push/pull образов).

### 3. Локальное окружение

- Установить Python 3.8.
- Создать виртуальное окружение, которое будет упаковано и загружено в Airflow
  (делается через `make create-venv-archive`).
- Установить s3cmd

### 4. Object Storage

- Создать S3-бакет с данными.
- Загрузить данные:
  - `ipc/data/lst` — предсказания базовой модели;
  - `ipc/data/pub` — месячные публикации, которые будут пополняться для
    регулярного переобучения.

### 5. Container Registry

Создать registry для образов модели:

```bash
yc container registry create --name ipc-registr
```

### 6. Доступ Airflow к DAG’ам

- Создать SSH-ключ для доступа к `airflow_dags`.
- Добавить публичный ключ в GitHub-репозиторий DAG’ов.
- Приватный ключ указать в конфигурации Airflow (см. `git_ssh_private_key`).

---

## correct_ipc_airflow: настройка и запуск

### Конфигурация Terraform

В `/infra/terraform.tfvars`:

```hcl
yc_config = {
  token     = ""
  cloud_id  = ""
  folder_id = ""
  zone      = "ru-central1-a"
}

admin_password          = "Пароль администратора Airflow"
public_key_path         = "Путь к публичному SSH-ключу"
private_key_path        = "Путь к приватному SSH-ключу"

yc_ipc_bucket_ak        = "Access key для IPC-бакета"
yc_ipc_bucket_sk        = "Secret key для IPC-бакета"
yc_ipc_bucket_path      = "s3a://ipc/data"

yc_mlflow_instance_name = "mlflow-server"

git_repo                = "git@github.com:...../airflow_dags.git"
git_ssh_private_key     = "~/.ssh/github_deploy_dags"

traininq_num_month      = "Количество месяцев для обучения, например: 10"
traininq_last_month     = "Крайняя точка обучения: 'last' или, например, 20260303"
```

### Пайплайн подготовки данных и обучения

Пайплайн делится на несколько этапов:

1. **Подготовка данных**

   - Исходный набор сохраняется в Parquet в S3.
   - Формируется target:
     - 1.0 — exact match с экспертным IPC;
     - 0.5 — совпадает только main group;
     - 0.0 — совпадений нет.
   - Дополнительно извлекаются структурные признаки IPC-кода.

2. **Обучение кандидатов**

   - Train-скрипт читает Parquet из S3 и преобразует его в long-format: одна строка = «патент — кандидатный IPC.
   - Деление на train/validation идёт по временной границе (месяцам публикации).
   - Используется CatBoostRegressor с признаками:
     - `ai_score`, `rank`;
     - категории `section`, `class2`, `subclass` и др.
   - На выходе один кандидат даёт:
     - `val_rmse`, `val_mae`;
     - модель `.cbm`;
     - `meta.json` (конфигурация и метрики);
     - `result.json` (используется при сравнении кандидатов).
   - Все параметры и метрики логируются в MLflow.

3. **Набор кандидатов**

   - baseline-регрессионная версия;
   - упрощённая shallow-модель;
   - модель без структурных признаков IPC.
   - Каждый кандидат обучается как отдельный job и пишет свои артефакты и
     `result.json`.

### Оркестрация в Airflow

Airflow DAG разбит на задачи:

- подготовка train-ready данных (создание Parquet и long-format);
- запуск обучения отдельных кандидатов;
- отдельная задача для выбора champion-модели.

В задачи обучения передаются:

- имя бакета;
- ключ Parquet-файла;
- префикс для model artifacts;
- имя кандидата;
- адрес MLflow tracking server;
- имя registered model в registry;
- `prod_bucket` и `prod_prefix` для публикации champion.

Важно различать:

- **pipeline-artifacts** (кандидаты и champion в выделенных S3-путях);
- **MLflow artifact store** (артефакты, которыми управляет сам MLflow).

### Champion–challenger логика

- Скрипт `select_champion.py` читает `result.json` всех кандидатов из
  training bucket.
- Лучший кандидат выбирается по минимальному `val_rmse`.
- Если champion отсутствует — новый кандидат автоматически становится
  production-моделью.
- Если champion существует — применяется champion–challenger схема:
  - новая модель продвигается только при улучшении на заданный `promote_margin`;
  - это защищает production от случайных колебаний метрик.

При успешном продвижении:

- в MLflow переключается alias на новую production-версию;
- файл champion-модели копируется в `prod/champion/model.cbm`;
- метаданные — в `prod/champion/meta.json`;
- предыдущий champion переносится в `prod/previous/` для rollback.

Inference-сервис читает модель не по MLflow URI, а из стабильного S3-пути;
ему не нужно знать внутреннюю структуру Registry.

## Запуск кластера и обучения

В корне **correct_ipc_airflow**:

```bash
make create-venv-archive
make apply
```

При этом:

- разворачивается кластер Airflow + MLflow;
- в S3-бакет Airflow копируются Python-скрипты, venv и `environment.json`;
- DAG’и подтягиваются из github `airflow_dags`.

После развёртывания:

1. Перейти в Airflow UI, войти под `admin` / `admin_password`.
2. Запустить DAG `init_variables` (инициализация переменных и подключений).
3. Запустить DAG обучения/обновления модели `training_pipeline`, который:
   - очищает и подготавливает данные;
   - обучает набор моделей-кандидатов;
   - выбирает лучшую;
   - сравнивает её с текущим champion в prod-бакете;
   - при улучшении обновляет champion и переносит пред. модель в `prod/previous`.

### Удаление кластера Airflow

После успешного выполнения DAG `training_pipeline` удалить кластер:
```bash
make destroy
```

---

## airflow_dags: обновление DAG’ов

- Airflow получает DAG’и из Git-репозитория `airflow_dags`.
- При изменении кода и `git push` Airflow автоматически перечитывает DAG’и
  и применяет изменения.

---

## correct_ipc_model_api: API + инфраструктура

### Инфраструктура: Terraform + Kubernetes

Вся облачная инфраструктура для API описана в Terraform:

- сеть;
- Managed Kubernetes-кластер;
- группы узлов;
- необходимые IAM-ресурсы.

Для Kubernetes-объектов (Deployment, Service, HPA, ServiceMonitor, PrometheusRule)
используются Terraform-ресурсы и/или YAML-манифесты, которые применяются через
провайдер `kubernetes` и `kubectl` из CI.

Это даёт:

- воспроизводимость окружений;
- понятный `terraform plan` перед изменениями;
- возможность отката и аудита инфраструктурных изменений.

### CI/CD: GitHub Actions + шаблонные манифесты

Пайплайн GitHub Actions отвечает за:

- сборку Docker-образа API и модели;
- прогон тестов;
- деплой в Kubernetes-кластер.

Сборка:

- при ручном запуске (`workflow_dispatch`) выполняется тестовый прогон;
- образ с тегом по коммиту (`cr.yandex/<registry>/correct-ipc:<sha>`) пушится
  в Container Registry.

Деплой:

- манифест Deployment хранится как шаблон с `IMAGE_PLACEHOLDER`;
- в CI подставляется реальное имя образа и генерируется
  `deployment.rendered.yaml`;
- далее выполняются `kubectl apply` и `kubectl rollout status` для контроля
  обновления.

Секреты доступа GitHub Actions к S3, YC и контейнерному реестру создаются при создании кластера,
что исключает ручные операции `kubectl create secret`

### Автоматизация развёртывания: один `make apply`

Поверх Terraform и GitHub Actions реализован единый сценарий автоматического
развёртывания, который сводится к запуску одной команды:

```bash
make apply
```

Этот шаг выполняет цепочку действий:

1. Запускает `terraform apply`, который:
   - создаёт  Kubernetes-кластер в Yandex Cloud;
   - поднимает все необходимые облачные ресурсы (VPC, node groups и т.п.);

2. После успешного применения Terraform:
   - настраивается `kubeconfig` для доступа к новому кластеру;
   - применяются базовые Kubernetes-манифесты:
     - мониторинг (Prometheus, ServiceMonitor, PrometheusRule);
     - Grafana;
     - вспомогательные namespaces и RBAC-настройки.

3. В кластер загружаются runtime-секреты:
   - ключи доступа к S3-совместимому хранилищу;
   - учётные данные для Container Registry и сервисных аккаунтов.

4. Затем автоматически триггерится GitHub Actions workflow деплоя приложения:
   - сборка и публикация Docker-образа с моделью;
   - рендер манифеста Deployment с подстановкой текущего образа;
   - `kubectl apply`  для API-сервиса.

В результате один вызов `make apply` поднимает «с нуля» полностью рабочий
контур: кластер, мониторинг, секреты и актуальную версию API с моделью,
готовую к нагрузочному тестированию и эксплуатации.

### Настройка Terraform (infra/monitoring)

В `/infra/terraform.tfvars`:

```hcl
c_config = {
  token     = ""
  cloud_id  = ""
  folder_id = ""
  zone      = "ru-central1-a"
}

public_key_path         = "Путь к публичному SSH-ключу"
private_key_path        = "Путь к приватному SSH-ключу"

c_ssh_public_key_path   = "~/.ssh/mlops_vlad.pub"
```

В `/monitoring/terraform.tfvars` задать:
  - `grafana_admin_password` — пароль администратора Grafana.

В `monitoring/config/alertmanager-config.yaml` настроить нотификации
(в проекте реализована Telegram-нотификация).

---

## API с моделью IPC-классификации

Приложение представляет собой HTTP API (FastAPI или аналог) c эндпоинтом
`/predict`, принимающим:

- `patent_id` — идентификатор патента/заявки;
- `ai_ipc` — строку с наборами IPC-кодов и весов, например:  
  `A61K31/00 (20.03%);A61K31/497 (5.22%);...`.

Внутри API:

- строка `ai_ipc` парсится в структуру кандидатов с нормализацией формата
  (поддерживаются полные и сокращённые записи IPC);
- из кандидатов формируется датафрейм с числовыми и категориальными признаками;
- модель CatBoost, загруженная из Object Storage, предсказывает рейтинг
  кандидатов;
- на выходе возвращаются отсортированные кандидаты, top-prediction и метаданные
  модели (версия, метрики, источник).

API развёрнуто в Kubernetes как Deployment с:

- двумя репликами;
- сервисом типа LoadBalancer;
- `readiness`, `liveness` и `startup` probes по `/health` для контроля
  живучести и корректной инициализации модели.

Пример вызова:
  
  - получение IP balancer:
  
    make get_balancer_id 

```bash
curl -s -X POST "http://81.26.188.138/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "patent_id": "RU-123",
    "ai_ipc": "AI_IPC:A61K31/00 (20.03%);A61K31/497 (5.22%);A61P35/00 (13.87%);C07D249/00 (8.4%);C17D249/08 (6.57%);"
  }' | jq
```

Пример ответа:

```json
{
  "patent_id": "RU-123",
  "model_meta": {
    "model_name": "correct_ipc_v1_reg",
    "model_version": "7",
    "run_id": "5b3b306bb53e4d5d9bbb543923aacd1a",
    "val_rmse": 0.2588601990865989,
    "val_mae": 0.1657458509181336,
    "input_key": "dataprep/ipc_with_ai_202603_last_12.parquet",
    "source_model_key": "models/correct_ipc_v1_reg/candidates/v1_reg_base.cbm",
    "promoted_at_utc": "2026-04-15T16:39:32.607345+00:00"
  },
  "parsed_candidates": [
    {
      "ipc_code": "A61K 31/00",
      "ai_score": 20.03,
      "rank": 1
    },
    {
      "ipc_code": "A61K 31/497",
      "ai_score": 5.22,
      "rank": 2
    },
    {
      "ipc_code": "A61P 35/00",
      "ai_score": 13.87,
      "rank": 3
    },
    {
      "ipc_code": "C07D 249/00",
      "ai_score": 8.4,
      "rank": 4
    },
    {
      "ipc_code": "C17D 249/08",
      "ai_score": 6.57,
      "rank": 5
    }
  ],
  "predictions": [
    {
      "ipc_code": "A61P 35/00",
      "ai_score": 13.87,
      "rank": 3,
      "score": 0.7760160649471507
    },
    {
      "ipc_code": "A61K 31/497",
      "ai_score": 5.22,
      "rank": 2,
      "score": 0.525706033458363
    },
    {
      "ipc_code": "A61K 31/00",
      "ai_score": 20.03,
      "rank": 1,
      "score": 0.39036078404340774
    },
    {
      "ipc_code": "C17D 249/08",
      "ai_score": 6.57,
      "rank": 5,
      "score": 0.19452647242992166
    },
    {
      "ipc_code": "C07D 249/00",
      "ai_score": 8.4,
      "rank": 4,
      "score": 0.10696233998843246
    }
  ],
  "top_prediction": {
    "ipc_code": "A61P 35/00",
    "ai_score": 13.87,
    "rank": 3,
    "score": 0.7760160649471507
  }
}
```

---



## Мониторинг и наблюдаемость

Для сбора метрик используется Prometheus, который через ServiceMonitor
собирает:

- HTTP-метрики API (статус-коды, latency, RPS);
- метрики ресурсов (CPU, память);
- показатели HPA (автоматический масштаб).

Визуализация метрик в Grafana:

- состояние API (доли 2xx/4xx/5xx, p95/p99 задержки);
- нагрузка на кластер и отдельные pod’ы;
- реакция Horizontal Pod Autoscaler на нагрузку.

PrometheusRule описывает алерты (например, рост доли 5xx или падение RPS),
что позволяет оперативно реагировать на деградацию сервиса.

доступ к prometheus и grafana можно получить через port forwarding kubectl:

kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090
kubectl port-forward -n monitoring svc/kube-prometheus-stack-grafana 3000:80
соответственно, используя http://localhost:9090 и http://localhost:3000

---

## Нагрузочное приложение

Нагрузочный клиент реализован как отдельный Python-скрипт:

- использует асинхронные запросы через `aiohttp`;
- читает датасет IPC-кандидатов из текстового файла (~8000 строк);
- циклически использует датасет (после конца файла возвращается к началу);
- позволяет настроить число параллельных воркеров, общую нагрузку и задержку
  между запросами.

Пример запуска:

```bash
python3 ipc_load_test.py \
  --host 127.0.0.1:8081 \
  --path /predict \
  --dataset txt/ai-ipc.txt \
  --threads 20 \
  --delay_ms 10 \
  --total 100000 \
  --responses_file responses.log
```

Клиент собирает статистику:

- сколько запросов отправлено;
- сколько успешных (2xx) и сколько с ошибками (4xx/5xx);
- суммарное время и фактический RPS;
- тела ответов и ошибки логируются для последующего анализа поведения модели
  и API под нагрузкой.

---

## Удаление компонентов

- Удаление кластера Airflow/MLflow:

  ```bash
  (из корня correct_ipc_airflow)
  make destroy
  ```

- Удаление кластера API:

  ```bash
  (из корня correct_ipc_model_api)
  make destroy
  ```

---

## Результат

В итоге получилась связанная система:

- Terraform создаёт и поддерживает инфраструктуру Kubernetes-кластера
  и сопутствующих ресурсов.
- GitHub Actions обеспечивает непрерывную доставку: от сборки образа до
  применения отрендеренных манифестов в кластер.
- API-приложение с моделью IPC работает в Kubernetes с корректными
  health-check’ами, автоскейлингом и внешним доступом через LoadBalancer.
- Мониторинг (Prometheus/Grafana) даёт видимость по состоянию модели
  и инфраструктуры.
- Специализированный нагрузочный клиент позволяет проверять производительность
  и устойчивость модели на реальных данных и находить проблемы до выхода в прод.
