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
pip install rapyuta-io --upgrade
ansible-galaxy collection install rapyutarobotics.rr_io -f
```

## MAC instructions
```
brew install git
git clone https://github.com/rapyuta-robotics/amr-deployment.git
cd amr-deployment
brew install python3.6
brew install python3-pip
pip install rapyuta-io --upgrade
ansible-galaxy collection install rapyutarobotics.rr_io -f
```

## Windows instructions
Using WSL2 or a VM is the easiest.
If these are not an option, then ansible can be run through cygwin.

Download [cygwin](https://cygwin.com/install.html)
Run the .exe
Option to select during the installation:
 - Install from internet
 - Specify your folder (ex C:\tools\cygwin64)
 - Specify the local package directory (ex C:\tools)
 - Select Direct connection
 - Select a server (https://ftp.jaist.ac.jp for Japan is fast)
 - At the package selection change View to Full and search for wget. Under the `New` section, choose the latest version
 - Press Next and wait for the installation
Run C:\tools\cygwin64\Cygwin.bat and in the terminal
```
wget raw.github.com/transcode-open/apt-cyg/master/apt-cyg
chmod +x apt-cyg
mv apt-cyg /usr/local/bin
which -a apt-cyg >/dev/null 2>&1 && echo ok
apt-cyg install python-{devel,pip,jinja2,six,yaml,crypto,cryptography}
apt-cyg install git curl dos2unix zip unzip openssl openssl-devel libffi-devel vim
mkdir /opt && cd /opt
git clone git://github.com/ansible/ansible
cd ansible && git checkout v2.9.22 # Or any version above
python2.7 setup.py install
```
Then we can install rapyuta libs
```
apt-cyg install python3 python3-pip
pip3 install https://storage.googleapis.com/rio-sdk-python/rapyuta_io-0.26.0-py2.py3-none-any.whl
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
ansible-playbook playbooks/play.yaml -vvv --extra-vars "@deploy_configs.yaml"
```

Once all robots are up in the UI, please verify that you can properly send an adhoc move to robot 10.
If an error arises or gbc crashed. Update deployment of GBC and run the `fix` files by doing
```
./scripts/fix <prefix_name> <number_of_deployed_robot> <gwm_auth_token>
```

# deploy_configs Parameters:

```present```\
Whether the deployment artifacts should be present in your project.\
```docker_password```\
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
```rr_gwm_static_route```\
gwm static route used by the gwm deployment.\
```rr_gbc_static_route```\
gbc static route used by the gbc deployment.\
```amr_ui_static_route```\
amr_ui static route used by the amr_ui deployment.\
```gazebo_ui_static_route```\
gazebo static route used by the gazebo deployment.

# FAQ
- authorization failed: update AUTH_TOKEN in config/basic_user_config.yaml. [ref](https://userdocs.rapyuta.io/3_how-tos/35_tooling_and_debugging/rapyuta-io-python-sdk/#auth-token)
- The Gazebo password is `rapyuta`
- The amr ui username and password is `autobootstrap`
