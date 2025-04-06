#!/bin/sh

# author: martin@affolter.net

red() { printf "\e[31m$*\e[0m\n"; }
yellow() { printf "\e[33m$*\e[0m\n"; }
green() { printf  "\e[32m$*\e[0m\n"; }

touch __secrets.sh
. __secrets.sh

# base settings
export TF_VAR_subscription_id="d5d5550b-8c21-407e-afb1-521e10206d9d"
export TF_VAR_base_name="manona"
export TF_VAR_location="switzerlandnorth"
export TF_VAR_restart_var="RESTART_VAR"

# cloudflare
export TF_VAR_cloudflare_api_token="$CLOUDFLARE_API_TOKEN"
export TF_VAR_cloudflare_zone_id="$CLOUDFLARE_ZONE_ID"
