#!/bin/bash

# change permission
chmod 600 id_ed25519*

# Start the SSH agent and add the private key
eval "$(ssh-agent -s)"
ssh-add id_ed25519

# Test SSH connection to GitHub
ssh -T git@github.com
