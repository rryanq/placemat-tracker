# Script to organize and account for paypal orders of
# Quin's Coins Coin Roll Hunting Placemats

from os import listdir, path
import subprocess
import click
import pdftotext

@click.command()
@click.option('--verbose', '-v', is_flag=True, help="use this option to print more information for accounting purposes")
def main(verbose):
    PAYPAL_ORDERS_PDF_DIR = "current_paypal_orders_pdf"
    # Paypal fee for $15, $25, $40 orders within the U.S. (2.9% of transaction amount + $0.30)
    FEE1_US = 0.74
    FEE2_US = 1.03
    FEE3_US = 1.46
    # Paypal fee for $15, $25, $40 orders to Canada (4.4% of transaction amount + $0.30)
    FEE1_CA = 0.96
    FEE2_CA = 1.40
    FEE3_CA = 2.06

    # Process the orders
    emails = []
    num_emails_initial = 0
    num_emails_final = 0
    fees = {"f1us": 0, "f2us": 0, "f3us": 0, "f1ca": 0, "f2ca": 0, "f3ca": 0}
    order_types = {
        "p1": 0, 
        "p2": 0, 
        "p3": 0, 
        "n1": 0, 
        "n2": 0, 
        "n3": 0, 
        "p1n1": 0,
        "s1": 0,
        "s2": 0,
        "p1n1s1": 0,
    }
    orders = []
    total_packages = 0
    order_type = ""

    for filename in [f for f in listdir("./" + PAYPAL_ORDERS_PDF_DIR) if f != '.gitignore']:
        file = path.dirname(path.realpath(__file__)) + '/' + PAYPAL_ORDERS_PDF_DIR + '/' + filename
        with open(file, 'rb') as f:
            if filename[-3:] == 'pdf':
                try:
                    pdf = pdftotext.PDF(f)
                    # remove left-to-right markers after coverting pdf to text
                    text = "\n\n".join(pdf).replace('\u200E', '')
                except pdftotext.Error:
                    print("unable to process file '%s'" % file)
                    continue
            elif filename[-3:] == 'txt':
                text = f.read().decode('utf-8')
            else:
                print("unable to process file '%s' due to unknown extension: '%s'" % (file, filename[-3:]))
                continue
            try:
                orders_text = [o for o in text.split('Ship to:') if o]
                orders_text = orders_text[1:]
                for order in orders_text:
                    if "American Cent Laminated Placemat" in order and ("Buy 1 Placemat" in order or "Buy 1 Small Cent Placemat" in order):
                        # process P1
                        order_types['p1'] = order_types['p1'] + 1
                        order_type = "P1"
                    elif "American Cent Laminated Placemat" in order and ("Buy 2 Placemats" in order or "Buy 2 Small Cent Placemats" in order):
                        # process P2
                        order_types['p2'] = order_types['p2'] + 1
                        order_type = "P2"
                    elif "American Nickel Laminated Placemat" in order and "Buy 1 Nickel Placemat" in order:
                        # process N1
                        order_types['n1'] = order_types['n1'] + 1
                        order_type = "N1"
                    elif "American Nickel Laminated Placemat" in order and "Buy 2 Nickel Placemats" in order:
                        # process N2
                        order_types['n2'] = order_types['n2'] + 1
                        order_type = "N2"
                    elif "1 Small Cent + 1 Nickel Placemat" in order:
                        # process P1N1
                        order_types['p1n1'] = order_types['p1n1'] + 1
                        order_type = "P1N1"
                    elif "Silver Stacking Placemat" in order and "Buy 1 Silver Stacking Placemat" in order:
                        # process S1
                        order_types['s1'] = order_types['s1'] + 1
                        order_type = 'S1'
                    elif "Silver Stacking Placemat" in order and "Buy 2 Silver Stacking Placemats" in order:
                        # process S2
                        order_types['s2'] = order_types['s2'] + 1
                        order_type = 'S2'
                    elif "Placemat Variety Pack" in order:
                        # process P1N1S1
                        order_types['p1n1s1'] = order_types['p1n1s1'] + 1
                        order_type = 'P1N1S1'
                    # Unprocessable order
                    else:
                        print('unprocessable order: %s' % file)
                        print('order: %s' % order)

                    # Retrieve addresses
                    name = order.split("Ship from:", 1)[0].strip()
                    name = name.title()
                    email = order.split('Quinlan Productions LLC')[1].split('quinscoins@gmail.com')[0].strip()
                    if '@' not in email:
                        print('WARNING: email address could not be parsed from file %s. Got: "%s"' % (file, email))
                    else:
                        emails.append(email)
                    split_order = order.split('Address:', 1)
                    if 'United States' in split_order[1]:
                        address = split_order[1].split('United States', 1)[0].strip().replace("  ", "")
                    elif 'Canada' in split_order[1]:
                        address = split_order[1].split('Canada', 1)[0].strip().replace("  ", "")
                        address = address + "\nCanada"
                        if order_type == "P1" or order_type == "N1" or order_type == "S1":
                            fees["f1ca"] = fees["f1ca"] + 1
                        elif order_type == "P2" or order_type == "N2" or order_type == "S2" or order_type == "P1N1":
                            fees["f2ca"] = fees["f2ca"] + 1
                        elif order_type == "P1N1S1":
                            fees["f3ca"] = fees["f3ca"] + 1
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
    fees['f2us'] = order_types['p2'] + order_types['n2'] + order_types['s2'] + order_types['p1n1'] - fees['f2ca']
    fees['f3us'] = order_types['p1n1s1'] - fees['f3ca']
    revenue = 15 * (order_types["p1"] + order_types["n1"] + order_types["s1"]) + 25 * (order_types["p2"] + order_types["n2"] + order_types["s2"] + order_types["p1n1"]) + 30 * order_types["p3"] + 40 * order_types["p1n1s1"]
    revenue_after_fees = revenue - (FEE1_US * fees['f1us']) - (FEE2_US * fees['f2us']) - (FEE3_US * fees['f3us']) - (FEE1_CA * fees['f1ca']) - (FEE2_CA * fees['f2ca']) - (FEE3_CA * fees['f3ca'])
    penny_placemats_needed = int(order_types['p1'] + (2 * order_types['p2']) + (3 * order_types['p3']) + order_types['p1n1']) + order_types['p1n1s1']
    nickel_placemats_needed = order_types['n1'] + (2 * order_types['n2']) + order_types['p1n1'] + order_types['p1n1s1']
    silver_stacking_placemats_needed = order_types['s1'] + (2 * order_types['s2']) + order_types['p1n1s1']
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
S2: {}
P1N1S1: {}

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
           order_types["s2"], order_types["p1n1s1"],
           revenue, revenue_after_fees, penny_placemats_needed, nickel_placemats_needed, 
           silver_stacking_placemats_needed, total_packages)
    )
    if verbose:
        penny_reg_price = order_types["p1"]
        nickel_reg_price = order_types["n1"]
        silver_stacking_reg_price = order_types["s1"]
        penny_deal_price = (2 * order_types["p2"]) + order_types["p1n1"]
        nickel_deal_price = (2 * order_types["n2"]) + order_types["p1n1"]
        silver_stacking_deal_price = (2 * order_types["s2"])
        num_sold_at_variety_price = order_types["p1n1s1"]
        print(
"""
ADDITIONAL STATS
===========================================
Penny placemats sold at regular price: {}
Penny placemats sold at deal price: {}
Penny Placemats sold at variety price: {}
Nickel placemats sold at regular price: {}
Nickel placemats sold at deal price: {}
Nickel Placemats sold at variety price: {}
Silver Stacking placemats sold at regular price: {}
Silver Stacking placemats sold at deal price: {}
Silver Stacking Placemats sold at variety price: {}
===========================================
""".format(penny_reg_price, penny_deal_price, num_sold_at_variety_price, nickel_reg_price, nickel_deal_price,
    num_sold_at_variety_price, silver_stacking_reg_price, silver_stacking_deal_price, num_sold_at_variety_price)
        )

    emails = list(dict.fromkeys(emails))
    emails_string = ','.join(emails)

    # replace latin "f" characters with their intended output strings
    emails_string = emails_string.replace('ﬀ', 'ff')
    emails_string = emails_string.replace('ﬁ', 'fi')
    emails_string = emails_string.replace('ﬂ', 'fl')
    emails_string = emails_string.replace('ﬃ', 'ffi')
    emails_string = emails_string.replace('ﬄ', 'ffl')
    emails_string = emails_string.replace('ﬅ', 'ft')

    print('emails: %s' % emails_string)

if __name__ == "__main__":
    main()
