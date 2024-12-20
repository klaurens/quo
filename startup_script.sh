#!/bin/bash

USER_HOME="/home/$(whoami)"
REPO_DIR="$USER_HOME/quo-repo"
BUCKET_DIR="$USER_HOME/quo"
BUCKET_NAME="quo-trial"

# Update and install necessary packages
sudo apt-get update -y
sudo apt-get install -y apt-transport-https ca-certificates curl gnupg lsb-release python3-pip python3.11-venv git-all libjpeg-dev

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
# Ensure the repository directory exists and reset its state
if [ -d "$REPO_DIR" ]; then
    echo "Repository directory exists. Resetting to source."
    cd $REPO_DIR
    git fetch --all
    git reset --hard origin/main
else
    echo "Cloning repository into new directory."
    git clone https://github.com/klaurens/quo.git $REPO_DIR
fi

cd $USER_HOME

# Mount the Google Cloud Storage bucket to a separate directory
mkdir -p $BUCKET_DIR
gcsfuse --implicit-dirs -file-mode=777 -dir-mode=777 $BUCKET_NAME $BUCKET_DIR
# mount -t gcsfuse -o allow_other $BUCKET_NAME $BUCKET_DIR

# Create a Python virtual environment in the final directory (not in the repo dir)
python3 -m venv venv
source venv/bin/activate

# Install dependencies from the cloned repository
pip install -r $REPO_DIR/requirements.txt

# Combine the contents of the repo and the GCS bucket into the final directory
cp -r $REPO_DIR/* $BUCKET_DIR/

chmod -R 777 "$REPO_DIR"

# Clean up temporary directories
# rm -rf $REPO_DIR
# rm -rf $BUCKET_DIR

echo "Startup script completed successfully."
echo "Attempt script run"

python $BUCKET_DIR/processing/main.py