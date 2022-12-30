'''Script to process paypal shipments'''

from os import listdir, path
import traceback
import click
import pdftotext
from itertools import groupby
from copy import deepcopy
from difflib import SequenceMatcher


class PaypalOrder():
    '''A Paypal order.'''
    order_code = None
    num_penny_placemats = 0
    num_nickel_placemats = 0
    num_silver_stacking_placemats = 0
    num_hats = 0
    customer_name = None
    email_address = None
    mailing_address = None
    country = None

    retail_price = 0
    paypal_fees = 0
    net_income = 0

class Package():
    '''A single package.'''
    order_code = None
    num_penny_placemats = 0
    num_nickel_placemats = 0
    num_silver_stacking_placemats = 0
    num_hats = 0
    num_total_placemats = 0
    customer_name = None
    email_address = None
    mailing_address = None
    country = None

    shipping_cost = 0
    shipping_class = None

# the cost to ship a single hat varies, but is typically around $4
# FIXME: not accounting for Canadian shipping rates!
SINGLE_HAT_SHIPPING_COST_USA = 4.00
# NOTE: I do not know if the below price is actually accurate. I will need to ship one of these
# from the post office before I know for sure. This is pretty pricey!
SINGLE_HAT_SHIPPING_COST_CANADA = 14.85
NUM_PLACEMATS_TO_SHIPPING_COST = {
    'USA': {
        '1': 1.92,
        '2': 2.64,
        '3': 3.12,
        '4': 3.84,
        # packages of 5 or 6 placemats must be sent via priority which doesn't
        # have a set price, but can cost up to $10
        '5': 10.00,
        '6': 10.00,
    },
    'Canada': {
        '1': 3.52,
        '2': 4.29,
        '3': 5.80,
        '4': 5.80,
        '5': 7.05,
        # 6 or more placemats to Canada cannot be done
    }
}


def get_address_similarity_ratio(a1, a2):
    return SequenceMatcher(None, a1, a2).ratio()


@click.command()
@click.option('--verbose', '-v', is_flag=True, help="use this option to print more information for accounting purposes")
def main(verbose):

    paypal_orders = []
    packages = []
    total_revenue = 0
    total_net_income = 0

    PAYPAL_ORDERS_PDF_DIR = "current_paypal_orders_pdf"
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
                orders_text = [o for o in text.split('Ship to') if o]
                orders_text = orders_text[1:]
                for order in orders_text:
                    Order = PaypalOrder()
                    order_items = order.split("Amount", 1)[1].split("Shipping & Handling", 1)[0].strip()
                    for item in order_items.splitlines():
                        item_details = item.strip().split()
                        item_code = item_details[0]
                        item_quantity = int(item_details[-3])
                        Order.order_code = item_code if not Order.order_code else Order.order_code + item_code
                        if item_code == 'P1':
                            Order.num_penny_placemats += item_quantity
                        elif item_code == 'N1':
                            Order.num_nickel_placemats += item_quantity
                        elif item_code == 'S1':
                            Order.num_silver_stacking_placemats += item_quantity
                        elif item_code == 'M1':
                            Order.num_penny_placemats += item_quantity
                            Order.num_nickel_placemats += item_quantity
                            Order.num_silver_stacking_placemats += item_quantity
                        elif item_code == 'H1':
                            Order.num_hats += item_quantity
                        else:
                            raise Exception()

                    # Retrieve customer name, address, and email for each order
                    customer_name = order.split("Ship from", 1)[0].strip()
                    Order.customer_name = customer_name.title()
                    email_address = order.split('Quinlan Productions LLC')[1].split('quinscoins@gmail.com')[0].strip()
                    if '@' not in email_address:
                        print('WARNING: email address could not be parsed from file %s. Got: "%s"' % (file, email_address))
                        Order.email_address = None
                    else:
                        Order.email_address = email_address
                    split_order = order.split('Address', 1)
                    addresses = [l.lstrip() for l in split_order[1].split('Transaction ID', 1)[0].split('\n')]
                    buyer_address = '\n'.join([l.split('     ')[0] for l in addresses])
                    if 'United States' in buyer_address:
                        address = buyer_address.split('United States', 1)[0].strip().replace("  ", "")
                        Order.country = 'USA'
                    elif 'Canada' in buyer_address:
                        address = buyer_address.split('Canada', 1)[0].strip().replace("  ", "")
                        address = address + "\nCanada"
                        Order.country = 'Canada'
                    else:
                        raise Exception('Unknown Country')
                    Order.mailing_address = address.replace("\n ", "\n").strip()

                    # Calculate costs
                    num_total_placemats = Order.num_penny_placemats + Order.num_nickel_placemats + Order.num_silver_stacking_placemats
                    # total retail price is the 4th value from the end minus the dollar sign
                    Order.retail_price = float(order.split()[-4][1:])
                    if Order.country == 'USA':
                        Order.paypal_fees = (49 + round(0.0349 * Order.retail_price * 100)) / 100
                    if Order.country == 'Canada':
                        # Paypal fee for orders to Canada (3.49% of transaction amount (in USD) + $0.59 CAD,
                        # rounded to nearest cent). Note: $0.59 CAD may correspond to a different USD value
                        # depending on the exchange rate at the time of the transaction, but assuming that
                        # the exchange rate is roughly 1 USD to 1.20 CAD results in a fee that is identical to
                        # the U.S. fees: 3.49% of transaction amount + $0.49 USD
                        # FIXME: now, it appears that Canadian fees will be more like this: 3.49% + $0.59 CAD + additional 1.50% international commericial transaction fee
                        # but even with this, it seems to be off by a few cents and I'm not sure why
                        Order.paypal_fees = (49 + round(0.0349 * Order.retail_price * 100)) / 100
                    Order.net_income = Order.retail_price - Order.paypal_fees
                    total_revenue += Order.retail_price
                    total_net_income += Order.net_income
                    # add the paypal order to the list of orders
                    paypal_orders.append(Order)
            except Exception as e:
                print("Unable to process the following file: {}".format(file))
                if verbose:
                    print(traceback.format_exc(e))

    # FIXME: consider grouping by name instead because grouping by address is 
    # looking like it will be too complicated
    # group paypal orders by address
    grouped_paypal_orders = groupby(
        sorted(paypal_orders, key = lambda p: p.mailing_address),
        key = lambda p: p.mailing_address,
    )

    # debug
    #for mailing_address, orders in grouped_paypal_orders:
    #    print(mailing_address)
    #    print(list(orders))

    for mailing_address, orders in grouped_paypal_orders:
        orders = list(orders)
        package = Package()
        package.mailing_address = mailing_address
        for o in orders:
            package.country = o.country
            package.customer_name = o.customer_name
            package.email_address = o.email_address
            package.num_penny_placemats += o.num_penny_placemats
            package.num_nickel_placemats += o.num_nickel_placemats
            package.num_silver_stacking_placemats += o.num_silver_stacking_placemats
            package.num_hats += o.num_hats
        num_total_placemats = package.num_penny_placemats + package.num_nickel_placemats + package.num_silver_stacking_placemats
        package.num_total_placemats = num_total_placemats
        # hats get shipped in packages that are separate from placemats
        if package.num_hats > 0:
            # each hat needs its own package because the boxes are too small
            # to fit more than one in a box
            hat_package = deepcopy(package)
            hat_package.num_penny_placemats = 0
            hat_package.num_nickel_placemats = 0
            hat_package.num_silver_stacking_placemats = 0
            hat_package.num_total_placemats = 0
            hat_package.order_code = 'H1'
            if hat_package.country == 'USA':
                hat_package.shipping_cost = SINGLE_HAT_SHIPPING_COST_USA
            elif hat_package.country == 'Canada':
                hat_package.shipping_cost = SINGLE_HAT_SHIPPING_COST_CANADA
            else:
                raise Exception('Unknown Country: %s' % hat_package.country)
            num_hats = hat_package.num_hats
            hat_package.num_hats = 1
            # FIXME: untested so far since no one has bought two hats at once
            for i in range(num_hats):
                packages.append(hat_package)
        if package.num_total_placemats > 0:
            placemat_package = deepcopy(package)
            placemat_package.num_hats = 0
            if placemat_package.country == 'USA' and placemat_package.num_total_placemats > 6:
                # FIXME: what to do in this scenario? Need to divide placemats
                # into separate packages in this case
                raise Exception('unable to ship more than 6 placemats in a single package within USA')
            if placemat_package.country == 'Canada' and placemat_package.num_total_placemats > 5:
                # FIXME: handle this situation better by splitting the shipment up
                raise Exception('unable to ship more than 5 placemats in a single package to Canada')
            placemat_package.shipping_cost = NUM_PLACEMATS_TO_SHIPPING_COST.get(placemat_package.country, {}).get(str(placemat_package.num_total_placemats))
            if placemat_package.shipping_cost is None:
                raise Exception('Unable to retrieve shipping cost for %s placemats to %s' % (
                    placemat_package.num_total_placemats, placemat_package.country
                ))
            placemat_package.order_code = '%s%s%s' % (
                ('P' + str(placemat_package.num_penny_placemats)) if placemat_package.num_penny_placemats else '',
                ('N' + str(placemat_package.num_nickel_placemats)) if placemat_package.num_nickel_placemats else '',
                ('S' + str(placemat_package.num_silver_stacking_placemats)) if placemat_package.num_silver_stacking_placemats else '',
            )
            if placemat_package.num_total_placemats > 4 and placemat_package.num_total_placemats < 7:
                # priority mail
                placemat_package.shipping_class = 'priority'
            else:
                # first class mail
                placemat_package.shipping_class = 'first_class'
            packages.append(placemat_package)

    untracked_emails = [p.email_address for p in packages if (p.shipping_class == 'first_class' and p.num_hats == 0)]
    tracked_emails = [p.email_address for p in packages if p.shipping_class == 'priority' or p.num_hats > 0]

    # calculate numbers of items needed
    penny_placemats_needed = sum([p.num_penny_placemats for p in packages])
    nickel_placemats_needed = sum([p.num_nickel_placemats for p in packages])
    silver_stacking_placemats_needed = sum([p.num_silver_stacking_placemats for p in packages])
    hats_needed = sum([p.num_hats for p in packages])

    # approximate cost of shipping
    shipping_cost = sum([p.shipping_cost for p in packages])

    # sort packages primarily by number of placemats in ascending order, then by alphebtical order
    sorted_packages = sorted(packages, key = lambda p: (p.num_total_placemats, p.order_code))

    # debug
    #for p in sorted_packages:
    #    print(p.__dict__)

    duplicate_name_packages = {}
    for i in sorted_packages:
        for j in sorted_packages:
            if i.customer_name == j.customer_name and i.mailing_address != j.mailing_address:
                if duplicate_name_packages.get(i.customer_name):
                    duplicate_name_packages[i.customer_name].extend([i.mailing_address, j.mailing_address])
                else:
                    duplicate_name_packages[i.customer_name] = [i.mailing_address, j.mailing_address]
    for name in duplicate_name_packages.keys():
        duplicate_name_packages[name] = list(set(duplicate_name_packages[name]))

    print("\nADDRESSES\n=============================")
    for p in sorted_packages:
        print(  
"""
Order Type: %s%s
%s
%s
""" %       (
                p.order_code,
                ' (tracked)' if (p.shipping_class == 'priority' or p.num_hats > 0) else '',
                p.customer_name,
                p.mailing_address
            )
        )
    print("=============================\n")

    # print out all important stats
    print(
"""
TOTAL REVENUE: ${:,.2f}
ESTIMATED REVENUE AFTER PAYPAL FEES: ${:,.2f}

IMPORTANT STATS
=============================
Penny Placemats Needed: {}
Nickel Placemats Needed: {}
Silver Stacking Placemats Needed: {}
Hats Needed: {}
Total Packages: {}

Shipping Cost: ${:,.2f}
=============================
""".format(total_revenue, total_net_income, penny_placemats_needed, nickel_placemats_needed, 
           silver_stacking_placemats_needed, hats_needed, len(packages), shipping_cost)
    )

    print('untracked emails: %s\n' % ', '.join(untracked_emails))
    print('tracked emails: %s\n' % ', '.join(tracked_emails))

    if duplicate_name_packages:
        for name, mailing_addresses in duplicate_name_packages.items():
            if len(mailing_addresses) == 2:
                address_similarity_ratio = get_address_similarity_ratio(mailing_addresses[0], mailing_addresses[1])
                if address_similarity_ratio > 0.7:
                    print(f"WARNING: mailing addresses for customer '{name}' have a high similarity ratio ({address_similarity_ratio:.2f}) indicating that these orders may need to be combined into a single package.")
            else:
                print(f"WARNING: customer '{name}' has more than 2 mailing addresses that are different. Be sure to analyze this case carefully.")


if __name__ == "__main__":
    main()