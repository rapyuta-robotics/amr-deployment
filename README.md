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
sudo apt install git
git clone https://github.com/rapyuta-robotics/amr-deployment.git
cd amr-deployment
sudo apt-get install python3.6
sudo apt install python3-pip
pip3 install https://storage.googleapis.com/rio-sdk-python/rapyuta_io-0.26.0-py2.py3-none-any.whl
ansible-galaxy collection install rapyutarobotics.rr_io
```

## MAC instructions
```
brew install git
git clone https://github.com/rapyuta-robotics/amr-deployment.git
cd amr-deployment
brew install python3.6
brew install python3-pip
pip install https://storage.googleapis.com/rio-sdk-python/rapyuta_io-0.26.0-py2.py3-none-any.whl
ansible-galaxy collection install rapyutarobotics.rr_io
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
ansible-playbook playbooks/deploy_10_amr.yaml -vvv --extra-vars "@deploy_configs.yaml"
```

Once all robots are up in the UI, please verify that you can properly send an adhoc move to robot 10.
If an error arises please run the `fix` files by doing
```
./fix <prefix_name> <number_of_deployed_robot>
```

# deploy_configs Parameters:

```present```\
Whether the deployment artifacts should be present in your project.\
```forklift_docker_read_password```\
The password of a read only account to reach the Forklift image repo. This is needed to pull the IO AMR images for the simulation\
```dockerhub_read_password```\
The password of ioamrreadonly dockerhub account. This is needed to pull the IO AMR images for the simulation\
```rio_amr_pa_image```\
amr_pa docker image to be used for the simulation.\
```rio_gwm_ui_image```\
gwm_ui docker image to be used for the simulation.\
```rio_db_image```\
db docker image to be used for the simulation.\
```rio_gazebo_image```\
gazebo docker image to be used for the simulation.\
```rio_gbc_image```\
gbc docker image to be used for the simulation.\
```prefix_name```\
name to prefix all deployments by.\
```site_name```\
name of the site.\
```amr_idle_timeout```\
Timeout until the amrs go idle.\
```amr_charge_time```\
Charge time for the amrs.\
```tracing```\
Set to True to enable tracing to be setup on the GBC and AMRs for debugging.\
```agent_list```\
List of agents to deploy, removing or adding an agent to this list will deploy less or more agents, please provide initial x,y and yaw, as well as map location.

# FAQ
- authorization failed: update AUTH_TOKEN in config/basic_user_config.yaml. [ref](https://userdocs.rapyuta.io/3_how-tos/35_tooling_and_debugging/rapyuta-io-python-sdk/#auth-token)
- The Gazebo password is `rapyuta`
- The amr ui username and password is `autobootstrap`
