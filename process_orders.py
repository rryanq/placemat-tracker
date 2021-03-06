# Script to organize and account for paypal orders of
# Quin's Coins Coin Roll Hunting Placemats

from os import listdir, path
import subprocess
import click

@click.command()
@click.option('--verbose', '-v', is_flag=True, help="use this option to print more information for accounting purposes")
def main(verbose):
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
    order_types = {
        "p1": 0, 
        "p2": 0, 
        "p3": 0, 
        "n1": 0, 
        "n2": 0, 
        "n3": 0, 
        "p1n1": 0,
        "s1": 0
    }
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
                elif "Silver Stacking Placemat" in text:
                    # process S1
                    order_types['s1'] = order_types['s1'] + 1
                    order_type = 'S1'
                elif "$15" in text:
                    if "nickel" in text or "Nickel" in text:
                        raise Exception()
                    # This is probably a P1 purchase from paypal.me. This is how I accepted payment early on
                    order_types['p1'] = order_types['p1'] + 1
                    order_type = "P1"
                elif "$25" in text:
                    # This is probably a P2 purchase from paypal.me. This is how I accepted payment early on
                    if "nickel" in text or "Nickel" in text:
                        raise Exception()
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
                    raise Exception('unprocessable order')

                # Retrieve addresses
                name_text = text.split("Ship to:", 1)[1]
                name = name_text.split("Ship from:", 1)[0].strip()
                name = name.title()
                email = text.split('Quinlan Productions LLC')[1].split('quinscoins@gmail.com')[0].strip()
                emails.append(email)
                split_text = text.split('Address:', 1)
                if 'United States' in split_text[1]:
                    address = split_text[1].split('United States', 1)[0].strip().replace("  ", "")
                elif 'Canada' in split_text[1]:
                    address = split_text[1].split('Canada', 1)[0].strip().replace("  ", "")
                    address = address + "\nCanada"
                    if order_type == "P1" or order_type == "N1" or order_type == "S1":
                        fees["f1ca"] = fees["f1ca"] + 1
                    elif order_type == "P2" or order_type == "N2" or order_type == "P1N1":
                        fees["f2ca"] = fees["f2ca"] + 1
                    else:
                        raise Exception()
                else:
                    raise Exception()
                address = address.replace("\n ", "\n")
                orders.append({"name": name, "address": address, "order_type": order_type})
                total_packages = total_packages + 1
            except Exception as e:
                print("Unable to process the following file: {}".format(file))
                if verbose:
                    print(e)

    fees["f1us"] = order_types['p1'] + order_types['n1'] + order_types['s1'] - fees['f1ca']
    fees['f2us'] = order_types['p2'] + order_types['n2'] + order_types['p1n1'] - fees['f2ca']
    revenue = 15 * (order_types["p1"] + order_types["n1"] + order_types["s1"]) + 25 * (order_types["p2"] + order_types["n2"] + order_types["p1n1"]) + 30 * order_types["p3"]
    revenue_after_fees = revenue - (FEE1_US * fees['f1us']) - (FEE2_US * fees['f2us']) - (FEE1_CA * fees['f1ca']) - (FEE2_CA * fees['f2ca'])
    penny_placemats_needed = int(order_types['p1'] + (2 * order_types['p2']) + (3 * order_types['p3']) + order_types['p1n1'])
    nickel_placemats_needed = order_types['n1'] + (2 * order_types['n2']) + order_types['p1n1']
    silver_stacking_placemats_needed = order_types['s1']
    orders = sorted(orders, key=lambda k: (k['address'][-6:] == 'Canada', k['order_type']))

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
S1: {}

TOTAL REVENUE: ${:,.2f}
REVENUE AFTER PAYPAL FEES: ${:,.2f}

IMPORTANT STATS
=============================
Penny Placemats Needed: {}
Nickel Placemats Needed: {}
Silver Stacking Placemats Needed: {}
Total Packages: {}
=============================
""".format(order_types["p1"], order_types["p2"], order_types["p3"],
           order_types["n1"], order_types["n2"], order_types["p1n1"], order_types["s1"],
           revenue, revenue_after_fees, penny_placemats_needed, nickel_placemats_needed, 
           silver_stacking_placemats_needed, total_packages)
    )
    if verbose:
        penny_reg_price = order_types["p1"]
        nickel_reg_price = order_types["n1"]
        silver_stacking_reg_price = order_types["s1"]
        penny_deal_price = (2 * order_types["p2"]) + order_types["p1n1"]
        nickel_deal_price = (2 * order_types["n2"]) + order_types["p1n1"]
        print(
"""
ADDITIONAL STATS
===========================================
Penny placemats sold at regular price: {}
Penny placemats sold at deal price: {}
Nickel placemats sold at regular price: {}
Nickel placemats sold at deal price: {}
Silver Stacking placemats sold at regular price: {}
===========================================
""".format(penny_reg_price, penny_deal_price, nickel_reg_price, nickel_deal_price, silver_stacking_reg_price)
        )

    emails = list(dict.fromkeys(emails))
    emails_string = ','.join(emails)
    # FIXME: there are more unicode characters that I am missing- I just haven't got them all documented yet
    emails_string = emails_string.replace('ﬀ', 'ff')
    emails_string = emails_string.replace('ﬁ', 'fi')
    emails_string = emails_string.replace('ﬂ', 'fl')

    print('emails: %s' % emails_string)

if __name__ == "__main__":
    main()
