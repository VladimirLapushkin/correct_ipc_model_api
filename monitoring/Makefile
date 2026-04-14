apply:
	terraform apply -auto-approve

destroy:
	terraform destroy -auto-approve

.PHONY: monitoring
monitoring:
	kubectl apply -f config/servicemonitor-correct-ipc-api.yaml
	kubectl apply -f config/prometheusrule-correct-ipc-api.yaml
	kubectl apply -f config/alertmanager-config.yaml
	kubectl apply -f config/ipc-model-api-scaling-dashboard.yaml
	
.PHONY: all
all: monitoring
