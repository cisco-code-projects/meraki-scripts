import meraki
import os
import json

from dotenv import load_dotenv
import meraki.exceptions

load_dotenv()

MERAKI_API_KEY = os.getenv("MERAKI_API_KEY")
RADIUS_SERVERS = json.loads(os.getenv("RADIUS_SERVERS"))

# get new secret
# new_secret = "123123123123"
new_secret = input("Enter new radius secret: ")

confirm_secret = input("Confirm new radius secret: ")

if new_secret != confirm_secret:
    print("Secrets do not match")
    exit()

re_confirm_secret = input(f"New radius secret to be used: {new_secret}  (y/n)")

if re_confirm_secret.lower() != "y":
    print("Exiting")
    exit()

# ask to confirm all changes or not
# confirm_all = True
confirm_everything_input = input("Do you want to confirm all updates?  (y/n)")

if confirm_everything_input.lower() == "y":
    confirm_all = True
else:
    confirm_all = False

dashboard = meraki.DashboardAPI(MERAKI_API_KEY, output_log=False, print_console=False)

meraki_orgs = dashboard.organizations.getOrganizations()

marki_org = None


print(f"You have access to {len(meraki_orgs)} organizations")

if len(meraki_orgs) == 1:
    meraki_org = meraki_orgs[0]
    print(f"Only 1 organization, using org {meraki_org['name']}")

else:
    for org in meraki_orgs:

        use_org = input(f"Use this org?  {org['name']}  (y/n)  ")

        if use_org.lower() == "y":
            meraki_org = org
            break

if meraki_org is None:
    print("No organization selected")
    exit()

print(f'Using org {meraki_org["name"]}')

networks = dashboard.organizations.getOrganizationNetworks(
    organizationId=meraki_org["id"]
)

print(f"You have access to {len(networks)} networks")

switch_policy_update_count = 0
switch_radius_server_update_count = 0
wireless_ssid_update_count = 0
wireless_radius_server_update_count = 0

for n in networks:
    print(f'Network: {n["name"]}')

    if confirm_all:
        check_network = input(f"Check network {n['name']}?  (y/n)  ").lower() == "y"
    else:
        check_network = True

    if not check_network:
        continue

    # get the switching access policies and update them
    try:
        switch_access_policies = dashboard.switch.getNetworkSwitchAccessPolicies(
            networkId=n["id"]
        )
    except meraki.exceptions.APIError as e:
        if e.status == 400:
            print(f"Network: {n['name']} -- No switch access policies found")
            switch_access_policies = []
        else:
            raise e

    print(f"Found {len(switch_access_policies)} switch access policies")

    for policy in switch_access_policies:
        need_to_update = False

        try:
            for radius_server in policy["radiusServers"]:
                if radius_server["host"] in RADIUS_SERVERS:
                    radius_server["secret"] = new_secret
                    switch_radius_server_update_count += 1
                    need_to_update = True
        except Exception as e:
            print(f"Error processing radiusServers: {e}")

        try:
            for radius_server in policy["radiusAccountingServers"]:
                if radius_server["host"] in RADIUS_SERVERS:
                    radius_server["secret"] = new_secret
                    switch_radius_server_update_count += 1
                    need_to_update = True
        except Exception as e:
            print(f"Error processing radiusAccountingServers: {e}")

        if need_to_update:
            print(f"Network: {n['name']} -- Need to update policy: {policy['name']}")

            if confirm_all:
                confirm = input("Confirm update?  (y/n)  ").lower() == "y"
            else:
                confirm = True

            if confirm:
                update_resp = dashboard.switch.updateNetworkSwitchAccessPolicy(
                    networkId=n["id"],
                    **policy,
                )
                print(f"Updated policy: {policy['name']}")
                switch_policy_update_count += 1
            else:
                print(f"Not updating policy: {policy['name']}")

    # get the wireless policies and update them
    try:
        wireless_ssids = dashboard.wireless.getNetworkWirelessSsids(networkId=n["id"])
    except meraki.exceptions.APIError as e:
        if e.status == 400:
            print(f"Network: {n['name']} -- No wireless ssids found")
            wireless_ssids = []
        else:
            raise e

    for ssid in wireless_ssids:
        need_to_update = False
        if "radiusServers" in ssid:
            for radius_server in ssid["radiusServers"]:
                if radius_server["host"] in RADIUS_SERVERS:
                    radius_server["secret"] = new_secret
                    wireless_radius_server_update_count += 1
                    need_to_update = True

        if "radiusAccountingServers" in ssid:
            for radius_server in ssid["radiusAccountingServers"]:
                if radius_server["host"] in RADIUS_SERVERS:
                    radius_server["secret"] = new_secret
                    wireless_radius_server_update_count += 1
                    need_to_update = True

        if need_to_update:
            print(f"Network: {n['name']} -- Need to update ssid: {ssid['name']}")

            if confirm_all:
                confirm = input("Confirm update?  (y/n)  ").lower() == "y"
            else:
                confirm = True

            if confirm:
                update_resp = dashboard.wireless.updateNetworkWirelessSsid(
                    networkId=n["id"],
                    **ssid,
                )
                print(f"Updated ssid: {ssid['name']}")
                wireless_ssid_update_count += 1
            else:
                print(f"Not updating ssid: {ssid['name']}")

print(f"Updated switch access policies: {switch_policy_update_count}")
print(f"Updated switch radius servers: {switch_radius_server_update_count}")
print(f"Updated wireless ssids: {wireless_ssid_update_count}")
print(f"Updated wireless radius servers: {wireless_radius_server_update_count}")
