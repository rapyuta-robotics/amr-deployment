# About
This repo is for deploying io-amr simulation on rapyuta.io 

# Prerequisites
- python 3

# Clone Repo, Install dependencies
## Linux Instructions
```
sudo apt install git
git clone https://github.com/rapyuta-robotics/amr-deployment.git
cd amr-deployment
sudo apt-get install python3.6
sudo apt install python3-pip
pip install https://storage.googleapis.com/rio-sdk-python/rapyuta_io-0.21.0-py2.py3-none-any.whlv
ansible-galaxy collection install abhinavg97.rr_io
```

## MAC instructions
```
brew install git
git clone https://github.com/rapyuta-robotics/amr-deployment.git
cd amr-deployment
brew install python3.6
brew install python3-pip
pip install https://storage.googleapis.com/rio-sdk-python/rapyuta_io-0.21.0-py2.py3-none-any.whl
ansible-galaxy collection install abhinavg97.rr_io
```

# Steps to follow *before* deploying
1. Find Project ID from the drop down in top left corner of [here](https://console.rapyuta.io)
2. Find the Authentication token from [here](https://auth.rapyuta.io/authToken/)
3. Find the ioamrreadonly dockerhub account password sent to your email address and edit deploy_configs.json to enter Dockerhub account password.
4. Run the below code in your terminal.

```
export RIO_PROJECT_ID=PROJECT_ID
export RIO_AUTH_TOKEN=AUTH_TOKEN
```

# Deploy simulation on rapyuta.io

*Navigate to the root of the repository.* 
```
ansible-playbook playbooks/test.yaml -vvv --extra-vars "@deploy_configs.json"
```

# Basic User Config Parameters:
```PROJECT_ID```\
Project ID in which you want to create the deployment\
```AUTH_TOKEN```\
The Auth token to authenticate the script to your project\
```DOCKER_PASSWORD```\
The password of ioamrreadonly dockerhub account. This is needed to pull the IO AMR images for the simulation

# FAQ
- authorization failed: update AUTH_TOKEN in config/basic_user_config.yaml. [ref](https://userdocs.rapyuta.io/3_how-tos/35_tooling_and_debugging/rapyuta-io-python-sdk/#auth-token)
- The Gazebo password is `rapyuta`
- The amr ui username and password is `autobootstrap`
