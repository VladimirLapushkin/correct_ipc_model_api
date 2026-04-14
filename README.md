Terraform создаёт kubernates кластер с необходимыми правами /infra
предварительно: созать yc container registry командой
yc container registry create --name fraud-registry
Github Action  разворачивает в облачном кластере Kubernates приложение с api модели. 
Реалтзовано 2 ручки: health и predict. 
Приложение берёт модель из внешнего s3 backet

Для запуска необходимо в Github создать следующие Repository secrets:

YC_CLEAN_BUCKET_AK   - auth key для бакета с моделью

YC_CLEAN_BUCKET_SK   - sekret key для бакета с моделью

YC_K8S_CLUSTER_ID  - ID k8s кластера (yc managed-kubernetes cluster list)

YC_REGISTRY_ID       - id yc registry для рпазмещения образов Docker

YC_SA_JSON_CREDENTIALS - креды для SA

Для локального запуска необходим файл .env c параметрами, собирать образ из файла Dockerfile-local
После выполнения Github Action

kubectl get svc -A

kubectl get svc


curl http://&lt;balancer EXTERNAL-IP&gt;/health


curl -X POST "http://&lt;balancer EXTERNAL-IP&gt;/predict" -H "Content-Type: application/json" \
  -d '{
    "transaction_id": 1,
    "customer_id": 1001,
    "terminal_id": 501,
    "tx_amount": 250.75,
    "tx_time_seconds": 36000,
    "tx_time_days": 12,
    "tx_fraud_scenario": 0
  }'



![alt text](screen/copy_model.png)
![alt text](screen/container_registry.png)
![alt text](screen/github_action.png)
![alt text](screen/k8s_yc.png)
![alt text](screen/deploy.png)
![alt text](screen/balancer.png)
![alt text](screen/health.png)
![alt text](screen/predict.png)

add successful into code

![alt text](screen/vscode.png)
![alt text](screen/new_commit.png)
![alt text](screen/new_health.png)

-----------------------------



Terraform kubernats:

1. ./model-api/infra
  make apply    # deploy kubernates cluster, make .env
  make deploy_secrets   # update kubectl, update secrets .env, deploy secrets to github
2. Terraform monitoring
  ./model-api.monitoring
  make apply
  make all


    
