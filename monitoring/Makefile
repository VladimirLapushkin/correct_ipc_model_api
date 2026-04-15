apply:
	terraform apply -auto-approve

destroy:
	terraform destroy -auto-approve

deploy_config:
	kubectl apply -f config/prometheusrule-correct-ipc-api.yaml
	kubectl apply -f config/servicemonitor-correct-ipc-api.yaml
	kubectl apply -f config/alertmanager-config.yaml
	kubectl apply -f config/ipc-model-api-scaling-dashboard.yaml
	

