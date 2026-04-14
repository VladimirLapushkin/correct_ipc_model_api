
git_secrets:
	yc iam key create --service-account-name admin --output ./secrets/sa-key.json && \
	sed -i '/^YC_SA_JSON_CREDENTIALS=/d' .env && \
	jq -c . ./secrets/sa-key.json | sed "s/^/YC_SA_JSON_CREDENTIALS=/" >> .env

push_secrets:
	python3 ./utils/push_secrets_to_github_repo.py

deploy_api:
	python3 ./utils/deploy_correct_ipc.py


kubeconf:
	rm ~/.kube/config
	yc managed-kubernetes cluster get-credentials mlops-k8s --external
	
k8s_deploy:	
	kubectl apply -f k8s/deployment.yaml
	kubectl apply -f k8s/prometheusrule.yaml
	kubectl apply -f k8s/servicemonitor.yaml

k8s_balancer_to_vars_airflow:
	BALANCER_IP=$$(kubectl get svc correct-ipc -n default -o json | jq -r '.status.loadBalancer.ingress[0].ip'); \
	PARENT_ENV_FILE="$$(cd ../correct_ipc_airflow/infra && pwd)/terraform.tfvars"; \
	sed -i '/^k8s_balancer_ip[[:space:]]*=/d' "$$PARENT_ENV_FILE"; \
	echo "k8s_balancer_ip = \"$$BALANCER_IP\"" >> "$$PARENT_ENV_FILE"


deploy_all: kubeconf k8s_deploy git_secrets push_secrets k8s_balancer_to_vars_airflow deploy_api

apply:
	$(MAKE) -C infra apply
	$(MAKE) kubeconf
	$(MAKE) -C monitoring apply
	$(MAKE) deploy_all

destroy:
	$(MAKE) -C monitoring destroy
	$(MAKE) -C infra destroy
