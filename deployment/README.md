# Prerequisites
- python 2.7
# Dependency install
`pip install -r requirements.txt`
# Deploy simulation on rapyuta.io
`python deploy.py --config config/rr.yaml`
# Create zip file for client
1. create <client_name>.yaml under config
2. `./generate_deployment_package.sh <client_name>`
# FAQ
- authorization failed: update AUTH_TOKEN in config.yaml. [ref](https://userdocs.rapyuta.io/3_how-tos/35_tooling_and_debugging/rapyuta-io-python-sdk/#auth-token)
