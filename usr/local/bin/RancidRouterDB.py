#!/usr/bin/env python
"""
    Simple wrapper for creating a rancid routers.db file
"""
import argparse
import sys
sys.path.append('/usr/local/rancid-tools')
import NetdiscoDB

if __name__ == '__main__':
    parser = argparse.ArgumentParser()    
    parser.add_argument('-f', required = True,
                        help='File location of the router.db to create')
    args = parser.parse_args()

    connect = NetdiscoDB.NetdiscoDB()
    connect.PrintRancidDB(args.f)
    connect.GenerateClogin()

