# About
This repo is for deploying io-amr simulation on rapyuta.io

# Prerequisites
- python 3

# Clone Repo, Install dependencies
## Linux Instructions
```
sudo apt update
sudo apt install software-properties-common
sudo add-apt-repository --yes --update ppa:ansible/ansible
sudo apt install ansible
sudo apt-get install python3.6
sudo apt install python3-pip
pip install rapyuta-io
ansible-galaxy collection install rapyutarobotics.rr_io
```


# Steps to follow *before* deploying
1. Find Project ID from the drop down in top left corner of [here](https://console.rapyuta.io)
2. Find the Authentication token from [here](https://auth.rapyuta.io/authToken/)
3. Edit config/default.yaml to set the deployment prefix
4. Set packageVersion in the packages if there are package version errors

# Deploy simulation on rapyuta.io

##  Deployment of Python script via Ansible (autobootstrap)
*Navigate to the root of the repository.*
To deploy:
```
ansible-playbook deploy_python.yaml -vvv --extra-vars "@config/default.yaml"
```
To deprovision:
```
none at the moment
```

# FAQ
- authorization failed: update AUTH_TOKEN in config/basic_user_config.yaml. [ref](https://userdocs.rapyuta.io/3_how-tos/35_tooling_and_debugging/rapyuta-io-python-sdk/#auth-token)
- The Gazebo password is `rapyuta`
- The amr ui username and password is `autobootstrap`
