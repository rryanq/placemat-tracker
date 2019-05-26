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
# Paypal fee for $15, $25 orders within the U.S. (2.9% of transaction amount + $0.30)
FEE1_US = 0.74
FEE2_US = 1.03
# Paypal fee for $15, $25 orders to Canada (4.4% of transaction amount + $0.30)
FEE1_CA = 0.96
FEE2_CA = 1.40

# Process the orders
emails = []
num_emails_initial = 0
num_emails_final = 0
fees = {"f1us": 0, "f2us": 0, "f1ca": 0, "f2ca": 0}
order_types = {"p1": 0, "p2": 0, "p3": 0, "n1": 0, "n2": 0, "n3": 0, "p1n1": 0}
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
                if "nickel" in text or "Nickel" in text:
                    raise exception()
                # This is probably a P1 purchase from paypal.me. This is how I accepted payment early on
                order_types['p1'] = order_types['p1'] + 1
                order_type = "P1"
            elif "$25" in text:
                # This is probably a P2 purchase from paypal.me. This is how I accepted payment early on
                if "nickel" in text or "Nickel" in text:
                    raise exception()
                order_types['p2'] = order_types['p2'] + 1
                order_type = "P2"
            elif "$30" in text:
                # special case: order of 3 placemats
                if "small cent" in text:
                    order_types['p3'] = order_types['p3'] + 1
                    order_type = "P3"
                    break
                if "nickel" in text:
                    order_types['n3'] = order_types['n3'] + 1
                    order_type = "N3"
                    break
            # Unprocessable order
            else:
                raise exception()

            # Retrieve addresses
            name_text = text.split("Ship to:", 1)[1]
            name = name_text.split("Ship from:", 1)[0].strip()
            name = name.title()
            split_text = text.split('Address:', 1)
            if 'United States' in split_text[1]:
                address = split_text[1].split('United States', 1)[0].strip().replace("  ", "")
            elif 'Canada' in split_text[1]:
                address = split_text[1].split('Canada', 1)[0].strip().replace("  ", "")
                if order_type == "P1" or order_type == "N1":
                    fees["f1ca"] = fees["f1ca"] + 1
                elif order_type == "P2" or order_type == "N2" or order_type == "P1N1":
                    fees["f2ca"] = fees["f2ca"] + 1
                else:
                    raise exception()
            else:
                raise exception()
            address = address.replace("\n ", "\n")
            orders.append({"name": name, "address": address, "order_type": order_type})

            total_packages = total_packages + 1
        except:
            print("Unable to process the following file: {}".format(file))

fees["f1us"] = order_types['p1'] + order_types['n1'] - fees['f1ca']
fees['f2us'] = order_types['p2'] + order_types['n2'] + order_types['p1n1'] - fees['f2ca']
revenue = 15 * (order_types["p1"] + order_types["n1"]) + 25 * (order_types["p2"] + order_types["n2"] + order_types["p1n1"]) + 30 * order_types["p3"]
revenue_after_fees = revenue - (FEE1_US * fees['f1us']) - (FEE2_US * fees['f2us']) - (FEE1_CA * fees['f1ca']) - (FEE2_CA * fees['f2ca'])
penny_placemats_needed = int(order_types['p1'] + (2 * order_types['p2']) + (3 * order_types['p3']) + order_types['p1n1'])
nickel_placemats_needed = order_types['n1'] + (2 * order_types['n2']) + order_types['p1n1']
orders = sorted(orders, key=lambda k: k['order_type'])

print(fees)

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
REVENUE AFTER PAYPAL FEES: ${:,.2f}

IMPORTANT STATS
=============================
Penny Placemats Needed: {}
Nickel Placemats Needed: {}
Total Packages: {}
=============================
""".format(order_types["p1"], order_types["p2"], order_types["p3"],
           order_types["n1"], order_types["n2"], order_types["p1n1"],
           revenue, revenue_after_fees, penny_placemats_needed, nickel_placemats_needed, total_packages)
)
