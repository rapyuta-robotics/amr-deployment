AMR Deployment
=====================

These instructions are for launching IO-AMR using the ansible deployment system.
Before you start you must make sure you have the following

- A linux/windows computer for running the deployment
- rapyuta.io account and credentials for deploying instances
- docker credentials for io_amr (ioamrreadonly)
- Note: rapyutarobotics.rr_io==2.0 has breaking changes and the newer version of the playbook will not support the older version (1.0.13)
- Please use the older version if you get the error: `"msg": "missing required arguments: type"`
- Installation command for the older version is `ansible-galaxy collection install 'rapyutarobotics.rr_io:<2' --upgrade`


Installing Prerequisites
^^^^^^^^^^^^^^^^^^^^^^^^^^^
###Linux

.. code-block:: console

    sudo apt update
    sudo apt install software-properties-common
    curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
    sudo python3 get-pip.py
    sudo python3 -m pip install ansible rapyuta-io
    ansible-galaxy collection install 'rapyutarobotics.rr_io:<3' --upgrade
    git clone https://github.com/rapyuta-robotics/amr-deployment/

###Windows

Using WSL2 or a VM is the easiest. If these are not an option, then ansible can be run through cygwin.

- Download `cygwin <https://cygwin.com/install.html>`_ and run the .exe

Option to select during the installation:

- Install from internet
- Specify your folder (ex C:\tools\cygwin64)
- Specify the local package directory (ex C:\tools)
- Select Direct connection
- Select a server (https://ftp.jaist.ac.jp for Japan is fast)
- At the package selection change View to Full and search for wget. Under the `New` section, choose the latest version
- Press Next and wait for the installation

Run C:\\tools\\cygwin64\\Cygwin.bat and run the below commands in the terminal

.. code-block:: console

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
      # Then we can install rapyuta libs
      apt-cyg install python3 python3-pip
      pip3 install rapyuta-io
      ansible-galaxy collection install 'rapyutarobotics.rr_io:<3' --upgrade


Deployment
^^^^^^^^^^^
To quickly get a running version, Open deploy_configs.yaml and enter your docker username and password (once you obtain access) and fill in the information of the image version that you want, there are more configurations listed in the deploy_configs.yaml file and are explained further in a latter section of this document

.. code-block:: console

    # Get the Project ID by going to https://console.rapyuta.io, clocking on the project name and copying the ID
    export RIO_PROJECT_ID=PROJECT_ID

    # Get the Authentication token from https://auth.rapyuta.io/authToken/, or clicking the Get Auth Token under your name on the menu
    export RIO_AUTH_TOKEN=AUTH_TOKEN

    # To Deploy (For device deployment use deploy_cloud.yaml if deploying on cloud and deploy_local.yaml if deploying on local device)
    ansible-playbook playbooks/deploy_simulation.yaml --extra-vars "@deploy_configs.yaml" --extra-vars "prefix_name=(insert prefix) present=true"

    # To Deprovision
    ansible-playbook playbooks/deploy_simulation.yaml --extra-vars "@deploy_configs.yaml" --extra-vars "present=false"
    

- Once IO-AMR is deployed, you can go to rapyuta.io > Deployments and click the UI deployment, scroll down to NETWORK ENDPOINTS, copy the GMW_UI Value and enter the fleet UI. Initial username and password is autobootstrap
- You can also go to rapyuta.io > Deployments and click the GWM deployment, croll down to NETWORK ENDPOINTS, copy the GWM_CORE_URL and append /swagger/ to the URL and enter the GWM. On the top you can click ReDOC to enter detailed API description
- The cloud deployment is for the setup where you want to deploy (postgres, gwm, user interface, server on the cloud and device_amr on the AMR)
- The local deployment is for the setup where you want to deploy (postgres, gwm, user interface, server on an NUC and device_amr on the AMR)
- The simulation deployment is for the setup where you want to deploy all components (postgres, gwm, user_interface, simulator on the cloud)
- If you wish to update the manifests run manifest updater from amr_deployment as such: scripts/manifest_updater.py -p <project_id> -a <auth_token> with <project_id> being the IO-AMR Project
- Consider using the `-vvv` flag in the above command for a verbose output

deploy_configs Parameters:
^^^^^^^^^^^
``present``
 Whether the deployment artifacts should be present in your project, this is controlled by the ``--extra-vars`` passed in the commandline, as such there is no need to change this value
``prefix_name``
 prefix to name all components of the simulation by. Please ensure that this value is not the default name ``prefix`` and only contains letters and numbers
``docker_password``
 The password of ioamrreadonly dockerhub account. This is needed to pull the IO AMR images for the simulation\
``rio_db_image``
 db docker image to be used rapyuta.io for the simulation. Default image should be sim_stable
``rio_gwm_image``
 gwm docker image to be used rapyuta.io for the simulation. Default image should be sim_stable
``rio_gwm_ui_image``
 gwm_ui docker image to be used rapyuta.io for the simulation. Default image should be sim_stable
``rio_amr_pa_image``
 amr_pa docker image to be used on rapyuta.io for the simulation. Default image should be sim_stable
``site_name``
 site to be used in the simulation.
``network_type``
 determines which network is used on rapyuta.io options are routed or native. **Warning** if this is set to routed, please remember to go to Networks on rapyuta.io and manually remove the created routed network after you deprovision the deployment
``ansible_async``
 sets whether async is used by the deployment playbook or not, running asynchronously will allow the deployment to complete faster, if set to true, playbook will attempt to run all the steps together as soon as dependencies allow and will only poll for results after all steps are started. If false, playbook will proceed step by step default is 'true'
``ros_distro``
 select ros distro, currently supported are melodic and noetic
``robot_device_name``:
The name of the robot device onboarded to rapyuta.io when device_deploy.yaml is being used.
``nuc_device_name``:
The name of the NUC device onboarded to rapyuta.io when device_deploy.yaml is being used.
``nuc_device_network_interface``:
The network interface to be used when native network is used in device_deploy.yaml and native network is deployed on NUC device.
``robot_device_network_interface``:
The network interface to be used when native network is used in device_deploy.yaml and native network is deployed on Robot device.

Troubleshooting Tips:
^^^^^^^^^^^
AMRs don't show
 - Restart GWM deployment on rapyuta.io
 - Redeploy the deployment
 - Redeploy using ansible_async = false

