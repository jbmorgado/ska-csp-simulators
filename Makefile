#
# Project makefile for a Tango project. You should normally only need to modify
# PROJECT below.
#

#
# CAR_OCI_REGISTRY_HOST and PROJECT are combined to define
# the Docker tag for this project. The definition below inherits the standard
# value for CAR_OCI_REGISTRY_HOST = artefact.skao.int and overwrites
#
PROJECT = ska-csp-simulators

# KUBE_NAMESPACE defines the Kubernetes Namespace that will be deployed to
# using Helm.  If this does not already exist it will be created
KUBE_NAMESPACE ?= simul

# UMBRELLA_CHART_PATH Path of the umbrella chart to work with
HELM_CHART ?= test-parent
UMBRELLA_CHART_PATH ?= charts/$(HELM_CHART)/

# RELEASE_NAME is the release that all Kubernetes resources will be labelled
# with
RELEASE_NAME = $(HELM_CHART)

# Fixed variables
# Timeout for gitlab-runner when run locally
TIMEOUT = 86400
# Helm version
HELM_VERSION = v3.3.1
# kubectl version
KUBERNETES_VERSION = v1.19.2

CI_PROJECT_DIR ?= .

KUBE_CONFIG_BASE64 ?=  ## base64 encoded kubectl credentials for KUBECONFIG
KUBECONFIG ?= /etc/deploy/config ## KUBECONFIG location

XAUTHORITY ?= $(HOME)/.Xauthority
THIS_HOST := $(shell ip a 2> /dev/null | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){3}[0-9]*).*/\2/p' | head -n1)
DISPLAY ?= $(THIS_HOST):0
JIVE ?= false# Enable jive
TARANTA ?= false# Enable Taranta
MINIKUBE ?= true ## Minikube or not
EXPOSE_All_DS ?= true ## Expose All Tango Services to the external network (enable Loadbalancer service)
SKA_TANGO_OPERATOR ?= true

NOTEBOOK_IGNORE_FILES = not notebook.ipynb

#
# include makefile to pick up the standard Make targets, e.g., 'make build'
# build, 'make push' docker push procedure, etc. The other Make targets
# ('make interactive', 'make test', etc.) are defined in this file.
#

# include OCI Images support
include .make/oci.mk

# include k8s support
include .make/k8s.mk

# include Helm Chart support
include .make/helm.mk

# Include Python support
include .make/python.mk

# include raw support
include .make/raw.mk

# include core make support
include .make/base.mk

# include your own private variables for custom deployment configuration
-include PrivateRules.mak

# Chart for testing
K8S_CHART = $(HELM_CHART)
K8S_CHARTS = $(K8S_CHART)

CI_JOB_ID ?= local##pipeline job id
TANGO_HOST ?= tango-databaseds:10000## TANGO_HOST connection to the Tango DS
TANGO_SERVER_PORT ?= 45450## TANGO_SERVER_PORT - fixed listening port for local server
CLUSTER_DOMAIN ?= cluster.local## Domain used for naming Tango Device Servers
K8S_TEST_RUNNER = test-runner-$(CI_JOB_ID)##name of the pod running the k8s-test

# Single image in root of project
OCI_IMAGES = ska-csp-simulators

ITANGO_ENABLED ?= true## ITango enabled in ska-tango-base

COUNT ?= 1

MARK_UN ?= unit
PYTHON_VARS_AFTER_PYTEST = -k $(MARK_UN) -m 'not post_deployment' --forked --disable-pytest-warnings --count=$(COUNT)

ifeq ($(strip $(firstword $(MAKECMDGOALS))),k8s-test)
# need to set the PYTHONPATH since the ska-cicd-makefile default definition 
# of it is not OK for the alpine images
PYTHON_VARS_BEFORE_PYTEST = PYTHONPATH=/app/src:/usr/local/lib/python3.10/site-packages TANGO_HOST=$(TANGO_HOST)
PYTHON_VARS_AFTER_PYTEST := -m 'post_deployment' --disable-pytest-warnings \
	--count=1 --timeout=300 --forked --true-context
endif

HELM_CHARTS_TO_PUBLISH = ska-csp-simulators
HELM_CHARTS ?= $(HELM_CHARTS_TO_PUBLISH)

PYTHON_BUILD_TYPE = non_tag_setup

PYTHON_SWITCHES_FOR_FLAKE8=--ignore=F401,W503 --max-line-length=180

VALUES_FILE ?= charts/test-parent/values.yaml
CUSTOM_VALUES =

ifneq ($(VALUES_FILE),)
CUSTOM_VALUES := --values $(VALUES_FILE) 
else
endif

ifneq ($(CI_REGISTRY),)
K8S_TEST_TANGO_IMAGE_PARAMS = --set ska-csp-simulators.simul.image.tag=$(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA) \
	--set ska-csp-simulators.simul.image.registry=$(CI_REGISTRY)/ska-telescope/ska-csp-simulators \
K8S_TEST_IMAGE_TO_TEST=$(CI_REGISTRY)/ska-telescope/ska-csp-simulators/ska-csp-simulators:$(VERSION)-dev.c$(CI_COMMIT_SHORT_SHA)
else
K8S_TEST_TANGO_IMAGE_PARAMS = --set ska-csp-simulators.simul.image.tag=$(VERSION) \
	--set ska-csp-simulators.vaultAddress="http://vault.default:8200"
K8S_TEST_IMAGE_TO_TEST = artefact.skao.int/ska-csp-simulators:$(VERSION)
endif

TARANTA_PARAMS = --set ska-taranta.enabled=$(TARANTA) \
				 --set ska-taranta-auth.enabled=$(TARANTA) \
				 --set ska-dashboard-repo.enabled=$(TARANTA)

ifneq ($(MINIKUBE),)
ifneq ($(MINIKUBE),true)
TARANTA_PARAMS = --set ska-taranta.enabled=$(TARANTA) \
				 --set ska-taranta-auth.enabled=false \
				 --set ska-dashboard-repo.enabled=false
endif
endif


K8S_EXTRA_PARAMS ?=
K8S_CHART_PARAMS = --set global.minikube=$(MINIKUBE) \
	--set global.exposeAllDS=$(EXPOSE_All_DS) \
	--set global.tango_host=$(TANGO_HOST) \
	--set global.cluster_domain=$(CLUSTER_DOMAIN) \
	--set global.device_server_port=$(TANGO_SERVER_PORT) \
	--set global.operator=$(SKA_TANGO_OPERATOR) \
	--set ska-tango-base.display=$(DISPLAY) \
	--set ska-tango-base.xauthority=$(XAUTHORITY) \
	--set ska-tango-base.jive.enabled=$(JIVE) \
	--set ska-tango-base.itango.enabled=$(ITANGO_ENABLED) \
	$(TARANTA_PARAMS) \
	${K8S_TEST_TANGO_IMAGE_PARAMS} \
	$(K8S_EXTRA_PARAMS) \
	$(CUSTOM_VALUES)


# override python.mk python-pre-test target
python-pre-test:
	@echo "python-pre-test: running with: $(PYTHON_VARS_BEFORE_PYTEST) $(PYTHON_RUNNER) pytest $(PYTHON_VARS_AFTER_PYTEST) \
	 --cov=src --cov-report=term-missing --cov-report xml:build/reports/code-coverage.xml --junitxml=build/reports/unit-tests.xml $(PYTHON_TEST_FILE)"

k8s-pre-test: python-pre-test

oci-pre-build:
	@if [[ ! -z "$(PYTANGO_VERSION)"  ]]; then \
		echo "Received pytango version: $(PYTANGO_VERSION)" ; \
		poetry add --lock pytango==$(PYTANGO_VERSION); \
	fi

k8s-pre-template-chart: k8s-pre-install-chart

local-k8s-test: 
	@pytest -m 'post_deployment' --disable-pytest-warnings --count=1 --timeout=300 --forked --true-context  \
		--cov=src --cov-report=term-missing --cov-report xml:build/reports/code-coverage.xml \
		--junitxml=build/reports/unit-tests.xml tests/

requirements: ## Install Dependencies
	poetry install

start_pogo: ## start the pogo application in a docker container; be sure to have the DISPLAY and XAUTHORITY variable not empty.
	docker run --network host --user $(shell id -u):$(shell id -g) --volume="$(PWD):/home/tango/ska-csp-simulators" --volume="$(HOME)/.Xauthority:/home/tango/.Xauthority:rw" --env="DISPLAY=$(DISPLAY)" $(CAR_OCI_REGISTRY_HOST)/ska-tango-images-tango-pogo:9.6.35

# k8s-wait:
# 	@deviceServers=$$(kubectl get deviceservers.tango.tango-controls.org -n $(KUBE_NAMESPACE) -o jsonpath='{.items[*].metadata.name}') && \
# 	kubectl wait -n $(KUBE_NAMESPACE) --for=jsonpath='{.status.state}'=Running  --timeout=$(K8S_TIMEOUT) deviceservers.tango.tango-controls.org $$deviceServers

.PHONY: pipeline_unit_test requirements


########################
# DOCS
########################

DOCS_SPHINXOPTS=-W --keep-going

docs-pre-build:
	poetry config virtualenvs.create false
	poetry install --no-root --only docs

.PHONY: docs-pre-build
