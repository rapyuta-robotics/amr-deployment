AMR Deployment
=====================

These instructions are for launching IO-AMR using the ansible deployment system.
Before you start you must make sure you have the following

- A linux/windows computer for running the deployment
- rapyuta.io account and credentials for deploying instances
- docker credentials for io_amr (ioamrreadonly)

Installing Prerequisites
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. tabs::

   .. tab:: Linux

        .. code-block:: console

            sudo apt update
            sudo apt install software-properties-common
            sudo add-apt-repository --yes --update ppa:ansible/ansible
            sudo apt install python3.6 python3-pip ansible
            ansible-galaxy collection install rapyutarobotics.rr_io -f
            git clone https://github.com/rapyuta-robotics/amr-deployment/

   .. tab:: Windows

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
            ansible-galaxy collection install rapyutarobotics.rr_io


Deployment
^^^^^^^^^^^
Open deploy_configs.yaml and enter your docker username and password (once you obtain access) and fill in the information of the image version that you want, there are more configurations listed in the deploy_configs.yaml file

.. code-block:: console

    # Get the Project ID by going to https://console.rapyuta.io, clocking on the project name and copying the ID
    export RIO_PROJECT_ID=PROJECT_ID

    # Get the Authentication token from https://auth.rapyuta.io/authToken/, or clicking the Get Auth Token under your name on the menu
    export RIO_AUTH_TOKEN=AUTH_TOKEN

    # To Deploy
    ansible-playbook playbooks/deploy.yaml -vvv --extra-vars "@deploy_configs.yaml" --extra-vars "present=true"

    # To Deprovision
    ansible-playbook playbooks/deploy.yaml -vvv --extra-vars "@deploy_configs.yaml" --extra-vars "present=false"

- Once IO-AMR is deployed, you can go to rapyuta.io > Deployments and click the UI deployment, scroll down to NETWORK ENDPOINTS, copy the GMW_UI Value and enter the fleet UI. Initial username and password is autobootstrap
- You can also go to rapyuta.io > Deployments and click the GWM deployment, croll down to NETWORK ENDPOINTS, copy the GWM_CORE_URL and append /swagger/ to the URL and enter the GWM. On the top you can click ReDOC to enter detailed API description