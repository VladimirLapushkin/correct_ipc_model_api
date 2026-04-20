# Проект коррекции IPC (МПК)

Проект реализован в инфраструктуре Yandex Cloud и состоит из нескольких сервисов:
- пайплайн очистки данных, обучения моделей и выбора champion-варианта;
- кластер Airflow/MLflow для оркестрации экспериментов;
- API-сервис модели в Kubernetes с мониторингом в стеке Prometheus + Grafana;
- утилита нагрузочного тестирования.

## Репозитории проекта

Для развёртывания проекта необходимо клонировать три репозитория:

1. **API модели в Kubernetes (correct_ipc_model_api)**  
   Реализует HTTP API модели, а также мониторинг в стеке Prometheus–Grafana.  
   Репозиторий:  
   <https://github.com/VladimirLapushkin/correct_ipc_model_api.git>

2. **Очистка данных и обучение модели (correct_ipc_airflow)**  
   Содержит код подготовки данных, обучения кандидатов и выбора champion-модели (Airflow, MLflow).  
   Репозиторий:  
   <https://github.com/VladimirLapushkin/correct_ipc_airflow.git>

3. **DAG-скрипты для Airflow (airflow_dags)**  
   Отдельный репозиторий с DAG’ами, которые подтягивает Airflow.  
   Репозиторий:  
   <https://github.com/VladimirLapushkin/airflow_dags.git>


---

## Общие предварительные шаги

1. **Установка Terraform**  
   Установить Terraform и выполнить `terraform init`:
   - для репозитория **correct_ipc_model_api** – в каталогах `infra` и `monitoring`;
   - для репозитория **correct_ipc_airflow** – в каталоге `infra`.

2. **Настройка Yandex Cloud**
   - Создать сервисный аккаунт.
   - Выдать ему права на:
     - управление Kubernetes-кластером;
     - доступ к объектным бакетам;
     - операции с container registry.

3. **Локальное окружение**
   - Установить Python 3.8 на локальную машину.
   - Python нужен для создания виртуального окружения (venv), которое будет загружено в Airflow.

4. **Подготовка Object Storage (S3)**
   - Создать S3-бакет для данных.
   - Загрузить исходные данные в структуру:
     - `ipc/data/lst` — данные с предсказанными IPC-кодами базовой моделью;
     - `ipc/data/pub` — данные публикаций по месяцам; сюда же будут ежемесячно добавляться новые публикации для переобучения модели.

5. **Создание Container Registry**
   - Создать registry командой:
     ```bash
     yc container registry create --name fraud-registry
     ```

6. **Доступ Airflow к репозиторию DAG’ов**
   - Создать SSH-ключ для доступа к репозиторию `airflow_dags`.
   - Открытый ключ добавить в настройку репозитория GitHub, приватный ключ использовать в конфигурации Airflow.


---

## Репозиторий correct_ipc_airflow

### Конфигурация Terraform

В файле `/infra/terraform.tfvars` указать значения:

```hcl
yc_config = {
  token     = ""
  cloud_id  = ""
  folder_id = ""
  zone      = "ru-central1-a"
}

admin_password          = "Пароль администратора Airflow (заглавная буква, строчные, цифра и спецсимвол)"
public_key_path         = "Путь к публичному SSH-ключу"
private_key_path        = "Путь к приватному SSH-ключу"

yc_ipc_bucket_ak        = "Access key для IPC-бакета"
yc_ipc_bucket_sk        = "Secret key для IPC-бакета"
yc_ipc_bucket_path      = "s3a://ipc/data"

yc_mlflow_instance_name = "mlflow-server"

git_repo                = "git@github.com:.../airflow_dags.git"
git_ssh_private_key     = "~/.ssh/github_deploy_dags"

traininq_num_month      = "Число месяцев для обучения, например: 10"
traininq_last_month     = "Крайняя дата обучения: 'last' или конкретный месяц, например 20260303"
```

### Запуск кластера Airflow + MLflow и обучения

В корне клонированного репозитория **correct_ipc_airflow** выполнить:

```bash
make create-venv-archive
make apply
```

При этом:
- разворачивается кластер с Airflow и MLflow;
- в бакет Airflow загружаются:
  - Python-скрипты;
  - архив venv;
  - `environment.json` для задач Airflow;
- DAG’и подтягиваются из Git-репозитория `airflow_dags`.

После успешного разворачивания:

1. Перейти в интерфейс Yandex Cloud → веб-интерфейс Airflow.
2. Войти под пользователем `admin` и паролем `admin_password`.
3. Перейти к списку DAG’ов и:
   - запустить DAG `init_variables` (инициализация переменных).
   - после успешного выполнения запустить DAG обучения и обработки (в исходном тексте он ошибочно повторно назван `init_variables.py` — фактически это DAG, который:
     - очищает и подготавливает данные;
     - обучает три варианта моделей;
     - выбирает лучшую;
     - сравнивает её с текущей production-моделью во внешнем бакете;
     - при улучшении обновляет champion в prod-бакете и переносит предыдущую модель в `prod/previous`.

### Удаление кластера Airflow

Из корневого каталога **correct_ipc_airflow**:

```bash
make destroy
```


---

## Репозиторий airflow_dags

- Airflow получает DAG’и напрямую из Git-репозитория.
- После изменения кода DAG’а и `git push` в `airflow_dags`:
  - Airflow автоматически подтянет изменения и обновит определение DAG’ов.


---

## Репозиторий correct_ipc_model_api

### Назначение

Репозиторий содержит:
- Terraform-конфигурацию Kubernetes-кластера и мониторинга.
- Манифесты API-сервиса модели.
- Настройку мониторинга (Prometheus, Grafana).
- CI/CD на базе GitHub Actions для авто-деплоя.

### Конфигурация Terraform (infra)

В файле `/infra/terraform.tfvars` указать:

```hcl
c_config = {
  token     = ""
  cloud_id  = ""
  folder_id = ""
  zone      = "ru-central1-a"
}

yc_instance_user        = "ubuntu"
yc_storage_endpoint_url = "https://storage.yandexcloud.net"

admin_password          = "Пароль администратора (заглавная буква, строчные, цифры и спецсимвол)"

public_key_path         = "Путь к публичному SSH-ключу"
private_key_path        = "Путь к приватному SSH-ключу"

c_ssh_public_key_path   = "~/.ssh/mlops_vlad.pub"
```

### Конфигурация мониторинга

В файле `/monitoring/terraform.tfvars` задать:

- `grafana_admin_password` — пароль администратора Grafana.

В файле `monitoring/config/alertmanager-config.yaml` настроить нотификации под свои креды (в проекте реализована Telegram-уведомление).

### Развёртывание API и мониторинга

В корне репозитория **correct_ipc_model_api**:

```bash
make apply
```

При этом:
- Terraform развернёт Kubernetes-кластер, Prometheus и Grafana.
- Будут созданы и отправлены в GitHub необходимые секреты для CI/CD.
- GitHub Actions автоматически выполнит сборку образа и деплой API в кластер.

В API реализованы две ручки:
- `GET /health` — проверка готовности сервиса;
- `POST /predict` — получение предсказания.

Примеры проверки:

```bash
kubectl get svc -A
kubectl get svc

curl http://<BALANCER-EXTERNAL-IP>/health
```

### Пример запроса к /predict

```bash
curl -s -X POST "http://127.0.0.1:8081/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "patent_id": "RU-123",
    "ai_ipc": "AI_IPC:A61K31/00 (20.03%);A61K31/497 (5.22%);A61P35/00 (13.87%);C07D249/00 (8.4%);C17D249/08 (6.57%);"
  }' | jq
```

---

## Нагрузочное тестирование

Для нагрузочного тестирования используется утилита из каталога `load_test/ipc_load_test` (в репозитории API):

- `ai-ipc.txt` содержит набор IPC-предсказаний базовой модели.
- Тестовый набор можно сформировать из LST-файлов утилитой `load_test/ipc_list_prep.py`.

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

Утилита:
- генерирует запросы к `/predict` с патентными ID и строками IPC-кандидатов;
- считает количество успешных и ошибочных ответов;
- замеряет фактический RPS и задержки;
- пишет результаты и ошибки в лог.

---

## Удаление кластера API

Из корневого каталога **correct_ipc_model_api**:

```bash
make destroy
```
