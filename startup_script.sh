#!/bin/bash

USER_HOME="/home/$(whoami)"
REPO_DIR="$USER_HOME/quo-repo"
BUCKET_DIR="$USER_HOME/quo-bucket"
FINAL_DIR="$USER_HOME/quo"
BUCKET_NAME="quo-trial"

# Update and install necessary packages
sudo apt-get update -y
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release python3-pip python3.11-venv git-all

# Install gcsfuse
# echo "deb http://packages.cloud.google.com/apt gcsfuse-stable main" | tee -a /etc/apt/sources.list.d/gcsfuse.list
# curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key add -
# apt-get update -y
# apt-get install -y gcsfuse

export GCSFUSE_REPO=gcsfuse-`lsb_release -c -s`
echo "deb [signed-by=/usr/share/keyrings/cloud.google.asc] https://packages.cloud.google.com/apt $GCSFUSE_REPO main" | sudo tee /etc/apt/sources.list.d/gcsfuse.list
curl -s https://packages.cloud.google.com/apt/doc/apt-key.gpg | sudo tee /usr/share/keyrings/cloud.google.asc
sudo apt-get update -y
sudo apt-get install -y  gcsfuse


# Clone the GitHub repository into a separate directory
git clone https://github.com/klaurens/quo.git $REPO_DIR

# Mount the Google Cloud Storage bucket to a separate directory
mkdir -p $BUCKET_DIR
gcsfuse --implicit-dirs $BUCKET_NAME $BUCKET_DIR

# Create a Python virtual environment in the final directory (not in the repo dir)
python3 -m venv $FINAL_DIR/venv
source $FINAL_DIR/venv/bin/activate

# Install dependencies from the cloned repository
cd $REPO_DIR
pip install -r requirements.txt

# Combine the contents of the repo and the GCS bucket into the final directory
mkdir -p $FINAL_DIR
cp -r $REPO_DIR/* $FINAL_DIR/
cp -r $BUCKET_DIR/* $FINAL_DIR/

# Clean up temporary directories
# rm -rf $REPO_DIR
# rm -rf $BUCKET_DIR

# Modify .bashrc to activate the virtual environment on SSH login
echo 'VENV_DIR="$HOME/quo/venv"' >> $USER_HOME/.bashrc
echo 'if [ -d "$VENV_DIR" ]; then' >> $USER_HOME/.bashrc
echo '    source "$VENV_DIR/bin/activate"' >> $USER_HOME/.bashrc
echo 'fi' >> $USER_HOME/.bashrc

echo "Startup script completed successfully."
