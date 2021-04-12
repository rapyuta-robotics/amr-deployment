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
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

## MAC instructions
```
brew install git
git clone https://github.com/rapyuta-robotics/amr-deployment.git
cd amr-deployment
brew install python3.6
brew install python3-pip
python3 -m venv venv
source venv/bin/activate
pip3 install -r requirements.txt
```

# Steps to follow *before* deploying
1. Find Project ID from the drop down in top left corner of [here](https://console.rapyuta.io)
2. Find the Authentication token from [here](https://auth.rapyuta.io/authToken/)
3. Find the ioamrreadonly dockerhub account password sent to your email address
4. Edit config/basic_user_config.yaml to enter Project ID, Authentication token and Dockerhub account password

# Deploy simulation on rapyuta.io

*Navigate to the root of the repository.* 
```
python3 deploy.py
```

# Basic User Config Parameters:
```deployment_prefix```\
The artifacts created using the script will be prefixed with this variable's value\
```deprovision_routed_network```\
Whether or not to deprovsion routed network (default=yes)\
```deprovision_db```\
Whether or not to deprovsion db (default=yes)\
```deprovision_gwm```\
Whether or not to deprovsion gwm (default=yes)\
```PROJECT_ID```\
Project ID in which you want to create the deployment\
```AUTH_TOKEN```\
The Auth token to authenticate the script to your project\
```DOCKER_PASSWORD```\
The password of ioamrreadonly dockerhub account. This is needed to pull the IO AMR images for the simulation

## Set Autocreated Credential settings
Set the following in the `GWM_PARAMS` to determine their value on auto-bootstrapping of the GWM 
```AUTO_ROOT_USER```: autobootstrap
```AUTO_ROOT_PASS```: autobootstrap
```AUTO_AUTH_TOKEN```: autobootstrap


# FAQ
- authorization failed: update AUTH_TOKEN in config/basic_user_config.yaml. [ref](https://userdocs.rapyuta.io/3_how-tos/35_tooling_and_debugging/rapyuta-io-python-sdk/#auth-token)
- The Gazebo password is `rapyuta`
- The amr ui username and password is `autobootstrap`