System Administrator Tools

This directory contains tools for deploying and managing project components.

Automatic Installation

A specialized script, install.py, has been created for the fully automated installation and configuration of the FPTN server, Telegram bot, and Grafana.

How to Use the Script

Navigate to the script directory:

cd sysadmin-tools


Make the script executable:

chmod +x install.py


Run the script:

sudo ./install.py


Note: The script requires sudo privileges to install the FPTN server and its dependencies.

What the Script Does

Checks for Dependencies: Ensures git, docker, docker-compose, curl, jq, and openssl are installed on your server.

Prompts for Configuration Data: The script will ask you to enter:

Your consent to install the FPTN server.

Your server's public IP address.

The API token for the Telegram bot.

The name of the outgoing network interface (for the FPTN server).

Data to create a new FPTN user (name, password, speed limit).

Installs and Configures the FPTN Server (Optional):

GitHub API Diagnostics: Before downloading, the script checks the GitHub API rate limit to prevent errors associated with exceeding it.

Automatically determines your server's architecture (amd64 or arm64).

Downloads and installs the latest version of the FPTN server .deb package from GitHub.

Note: The script first attempts to find releases in the repository you cloned it from. If no releases are found, it automatically downloads them from the main repository batchar2/fptn.

Generates SSL certificates.

Configures the /etc/fptn/server.conf configuration file.

Creates a new FPTN user.

Installs and configures dnsmasq for correct DNS operation.

Starts and enables autostart for the fptn-server service.

Configures the Telegram Bot:

Creates an .env file with your settings.

Builds and runs the Docker container with the bot.

You may still need to manually edit servers.json and servers_censored_zone.json if you wish to add additional servers.

Configures Grafana:

Creates an .env file with your settings, using the generated PROMETHEUS_SECRET_ACCESS_KEY, which is also written to the FPTN server configuration.

Runs Docker containers for Grafana and Prometheus.

Post-Installation

The FPTN server will be running and ready. At the end of the script, you will see the access token for the new user. Save it, as it is needed to connect to your VPN.

The Telegram bot will be running in the background.

Grafana will be accessible at http://<your_ip>:3000.

Default login and password: admin / admin.

Be sure to change the password after your first login!

Stopping Services

FPTN Server:

sudo systemctl stop fptn-server


Telegram Bot and Grafana: To stop the running Docker services, use the docker-compose down command in the respective directories:

sysadmin-tools/telegram-bot

sysadmin-tools/grafana
