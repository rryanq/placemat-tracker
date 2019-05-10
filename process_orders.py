# Script to organize and account for paypal orders of
# Quin's Coins Coin Roll Hunting Placemats

from os import listdir, path
import subprocess

# convert pdf paypal receipts into .txt files so that we can work with them
print("Converting paypal order receipts to txt...")
subprocess.call("./convert_orders_to_txt")
print("Done")

# specify the folder where the .txt paypal orders can be found
PAYPAL_ORDERS_TXT_DIR = "paypal_orders_txt"

# Process the orders
emails = []
num_emails_initial = 0
num_emails_final = 0
order_types = {"p1": 0, "p2": 0, "p3": 0, "n1": 0, "n2": 0, "p1n1": 0}
orders = []
total_packages = 0
order_type = ""
for order in listdir("./" + PAYPAL_ORDERS_TXT_DIR):
    file = path.dirname(path.realpath(__file__)) + '/' + PAYPAL_ORDERS_TXT_DIR + '/' + order
    with open(file, 'r') as f:
        try:
            text = f.read()
            if "American Cent Laminated Placemat" in text and "Buy 1 Placemat" in text:
                # process P1
                order_types['p1'] = order_types['p1'] + 1
                order_type = "P1"
            elif "American Cent Laminated Placemat" in text and "Buy 2 Placemats" in text:
                # process P2
                order_types['p2'] = order_types['p2'] + 1
                order_type = "P2"
            elif "American Nickel Laminated Placemat" in text and "Buy 1 Nickel Placemat" in text:
                # process N1
                order_types['n1'] = order_types['n1'] + 1
                order_type = "N1"
            elif "American Nickel Laminated Placemat" in text and "Buy 2 Nickel Placemats" in text:
                # process N2
                order_types['n2'] = order_types['n2'] + 1
                order_type = "N2"
            elif "1 Small Cent + 1 Nickel Placemat" in text:
                # process P1N1
                order_types['p1n1'] = order_types['p1n1'] + 1
                order_type = "P1N1"
            elif "$15" in text:
                # This is probably a P1 purchase from paypal.me. This is how I accepted payment early on
                order_types['p1'] = order_types['p1'] + 1
                order_type = "P1"
            elif "$25" in text:
                # This is probably a P2 purchase from paypal.me. This is how I accepted payment early on
                order_types['p2'] = order_types['p2'] + 1
                order_type = "P2"
            elif "$30" in text:
                # special case: order of 3 placemats
                order_types['p3'] = order_types['p3'] + 1
                order_type = "P3"
            elif "$10" in text:
                # special case: order of 1 placemat at special $10 price
                order_types['p3'] = order_types['p3'] + (1/3)
                order_type = "P3 special"
            else:
                raise exception()

            name_text = text.split("Ship to:", 1)[1]
            name = name_text.split("Ship from:", 1)[0].strip()
            name = name.title()
            split_text = text.split('Address:', 1)
            if 'United States' in split_text[1]:
                address = split_text[1].split('United States', 1)[0].strip().replace("  ", "")
            elif 'Canada' in split_text[1]:
                address = split_text[1].split('Canada', 1)[0].strip().replace("  ", "")
            else:
                raise exception()
            address = address.replace("\n ", "\n")
            orders.append({"name": name, "address": address, "order_type": order_type})

            total_packages = total_packages + 1
        except:
            print("Unable to process the following file: {}".format(file))

revenue = 15 * (order_types["p1"] + order_types["n1"]) + 25 * (order_types["p2"] + order_types["n2"] + order_types["p1n1"]) + 30 * order_types["p3"]
penny_placemats_needed = int(order_types['p1'] + (2 * order_types['p2']) + (3 * order_types['p3']) + order_types['p1n1'])
nickel_placemats_needed = order_types['n1'] + (2 * order_types['n2']) + order_types['p1n1']
orders = sorted(orders, key=lambda k: k['order_type'])

"""Print out all addresses."""
print("\nADDRESSES\n=============================")
for order in orders:
    print(
"""
Order Type: {}
{}
{}
""".format(order["order_type"], order["name"], order["address"])
    )
print("=============================")

"""Print out all important stats."""
print(
"""
ORDER TYPES:
P1: {}
P2: {}
P3: {}
N1: {}
N2: {}
P1N1: {}

TOTAL REVENUE: ${:,.2f}

IMPORTANT STATS
=============================
Penny Placemats Needed: {}
Nickel Placemats Needed: {}
Total Packages: {}
=============================
""".format(order_types["p1"], order_types["p2"], order_types["p3"],
           order_types["n1"], order_types["n2"], order_types["p1n1"],
           revenue, penny_placemats_needed, nickel_placemats_needed, total_packages)
)
