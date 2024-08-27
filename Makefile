.PHONY : build_infra build_app start_app stop_app destroy_app destroy_infra destroy_all

build_infra:
	terraform -chdir=./infra init 
	terraform -chdir=./infra apply -auto-approve

build_app:
	docker build -t gradio-app -f app/Dockerfile app

start_app:
	docker run -d -p 7860:7860 --env-file=./.env gradio-app

stop_app:
	docker stop $(shell docker ps -a -q --filter "ancestor=gradio-app") || true

destroy_app: stop_app
	docker rmi $(shell docker images -a -q "gradio-app") -f || true

destroy_infra:
	terraform -chdir=./infra destroy -auto-approve

destroy_all: destroy_app destroy_infra
