#!/bin/bash

# Move the SSH key files from /workspace/Scarab-infra to ~/.ssh directory
mv /workspace/Scarab-infra/id_ed25519 ~/.ssh/id_ed25519
mv /workspace/Scarab-infra/id_ed25519.pub ~/.ssh/id_ed25519.pub

# Set appropriate permissions for the SSH key files
chmod 600 ~/.ssh/id_ed25519
chmod 600 ~/.ssh/id_ed25519.pub

# Start the SSH agent and add the private key
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# Test SSH connection to GitHub
ssh -T git@github.com

