#!/bin/bash -ex

# Define variables for repository URL and directory
REPO_URL="https://github.com/containers/qm.git"
REPO_DIR="qm"

# Step 1: Clone the repository
rm -rf "$REPO_DIR"
echo "Cloning the repository..."
git clone "$REPO_URL" "$REPO_DIR"
cd "$REPO_DIR" || exit 1

# Step 2: Build the RPM package
echo "Building the RPM package..."
if ! make rpm; then
  echo "RPM build failed."
  exit 1
fi

# Optional: Install the RPM package to test it fully
echo "Installing the RPM package..."
if ! sudo dnf install -y rpmbuild/RPMS/noarch/qm*.rpm; then
  echo "RPM installation failed."
  exit 1
fi

# Step 3: Run the setup script and check its exit status
echo "Running /usr/share/qm/setup..."
if /usr/share/qm/setup; then
  echo "Setup script ran successfully."
  rm -rf qm && exit 0
else
  echo "Setup script failed."
  rm -rf qm && exit 1
fi
