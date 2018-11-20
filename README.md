# psr-application
AWS, Django, Node based web application


## Set a virtual environment / Get the PSR code:

#### Prepare your local env

`$ virtualenv -p /usr/local/bin/python3.4/ psr`

`$ cd psr/`

`$ source bin/activate`

`$ git clone git@github.com:poundandgrain/psr-application.git`

`$ cd psr-application/`

#### Run the fabric automation script to set up your localenv (only on ubuntu at the moment)

`$ fab set_local_env `

#### 


## Ebeanstalk (only for production!!!)
- Install EB CLI on your local dev environment (http://docs.aws.amazon.com/elasticbeanstalk/latest/dg/eb-cli3-install.html)

`$ pip install --upgrade awsebcli`

- Init EB CLI (on your local dev env)

`$ eb init`

    Select a default region == **ca-central-1 : Canada (Central)**

    Enter Application Name: == **psr**

    It appears you are using Python. Is this correct? (Y/n) == **Y**

    Select a platform version. ==  **Python 3.4**

    Do you want to set up SSH for your instances? (Y/n) == **Y**

    Select a keypair == **psr**

- Create a new AWS environment from your local dev env (if not existing)

`$ eb create psr-dev`

- Deploy a new code version to an AWS environment (eg. psr-dev)

`$ eb deploy psr-dev`
