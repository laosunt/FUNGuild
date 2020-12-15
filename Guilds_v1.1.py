#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (C) 2014-2015 Zewei Song

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

This script assigns functional information to the OTUs in the user's OTU table. The OTU table needs to have a column named 'taxonomy', which contains information from a reference database (such as UNITE - https://unite.ut.ee/). It is required that the first line of the OTU table to be the header, without any additional comments. Some programs, such as QIIME will add an additional row of comments before the header, and this has to be removed before using the FunGuild script. The script will try to recognized the delimiter in the user's OTU table, but comma (.csv) or tab (.txt) delimiter formats are recommended.

The functional databases are fetched from http://www.stbates.org/funguild_db.php or http://www.stbates.org/nemaguild_db.php

Script usage: Guilds_v1.0.py [-h] [-otu OTU_file] [-db] [-m] [-u]

optional arguments:
  -h, --help       Show this help message and exit
  -otu OTU         Path and file name of the OTU table. The script will try to
                   detect the delimiters in the file, but tab or csv are
                   preferred formats.
  -db              Database to use ('fungi' or 'nematode') [default:fungi]
  -m, --matched    Ask the script to output an otu table containing only OTUs
  		   for which functional assignments have been made
  -u, --unmatched  Ask the script to output an otu table containing only OTUs
  		   for which functional assignments could not be made

This is an example command to run this script:
python Guilds_v1.0.py -otu user_otu_table.txt

The script will have one output file with suffix on the input file: user_otu_table.function.txt

By using -m and -u, the script will produce two additional files:
-m will output a file containing only OTUs that have been assigned a function: user_otu_table.matched.txt
-u will output a file containing only OTUs that were not matched in the database: user_otu_table.unmatched.txt

Care should be taken in managing directories as existing files will be overwritten without notice if matching file names (e.g., user_otu_table.matched.txt) are generated by the script.

By using the -db option, you will call the database for your group of organism. Currently 'fungi' and 'nematode'. The default is 'fungi'.

All output tables are sorted according to the sum total number of sequences corresponding to each OTU (rank OTU abundance).

###################################################################################
Development history:

The idea of parsing OTUs into functions originated from an python script by Sara Branco that segregated Ectomycorrhizal (EM), potential EM, and non-EM fungal OTUs (Branco et al. 2013. PLoS One 8: 1–10).

The algorithm used by FunGuild was first developed by Scott T. Bates in R to assign functions to any fungal taxon and to indicate a probability for the assignment.

The current FunGuild script has been developed by Zewei Song in python in order to improve functionality, performance and cross-platform compatibility.
###################################################################################

Zewei Song
2/14/2015
songzewei@outlook.com
'''
from __future__ import print_function
from __future__ import division
#Import modules#################
import argparse
import os
import timeit
import sys
#import urllib
from operator import itemgetter
import csv

start = timeit.default_timer()
################################

#Command line parameters#####################################################################
parser = argparse.ArgumentParser()

parser.add_argument("-otu", help="Path and file name of the OTU table. The script will try to detect the delimiter"
					"in the file, but tab or csv are preferred formats.")
parser.add_argument("-m", "--matched", action="store_true", help="Ask the script to output a otu table with function assigned OTUs")
parser.add_argument("-u", "--unmatched", action="store_true", help="Ask the script to output a otu table with function assigned OTUs")
parser.add_argument("-db", choices=['fungi','nematode'], default='fungi', help="Assign a specified database to the script")
args = parser.parse_args()

#input files
otu_file = args.otu

#Detect delimiter in the input file
with open(otu_file, 'rU') as f1:
    dialect = csv.Sniffer().sniff(f1.read())
    otu_delimiter = dialect.delimiter

#output files
dot_position = [i for i in range(len(otu_file)) if otu_file.startswith('.', i)] #Get the position of . in the input filename

if not dot_position: #the file does not have extension
	matched_file = args.otu + '.guilds_matched.txt'
	unnmatched_file = args.otu + '.guilds_unmatched.txt'
	total_file = args.otu + '.guilds.txt'
else:
	matched_file = args.otu[:dot_position[-1]] + '.guilds_matched.txt'
	unmatched_file = args.otu[:dot_position[-1]] + '.guilds_unmatched.txt'
	total_file = args.otu[:dot_position[-1]] + '.guilds.txt'
###########################################################################################

# Import Function Database from GitHub, and get it ready.##################################
print("FunGuild v1.0 Beta")

database_name = args.db
if database_name == 'fungi':
    url = 'http://www.stbates.org/funguild_db_2.php'
elif database_name == 'nematode':
    url = 'http://www.stbates.org/nemaguild_db.php'

import requests
import json

print('Connecting with FUNGuild database ...')
db_url = requests.get(url)
#db_url = db_url.content.decode('utf-8').split('\n')[6].strip('[').strip(']</body>').replace('} , {', '} \n {').split('\n')
db_url = db_url.content.decode('utf-8')
db_url = db_url.split('\n')[6].strip('</body>')
db_url = json.loads(db_url)
db = []
# For all species key works (replace space with underscore)
for record in db_url:
    # current_record = json.loads(record)
    current_record = record
    if current_record['taxonomicLevel'] == 20: # If species level
        current_record['taxon'] = current_record['taxon'].replace(' ', '_')
    try:
        current_record['trophicMode'] = current_record['TrophicMode']
    except KeyError:
        pass
    try:
        current_record['growthForm'] = current_record['growthMorphology']
    except KeyError:
        pass
    db.append(current_record)

#Preparing the database for keyword search
f_database = []
lookup_terms = ['taxon','taxonomicLevel','trophicMode','guild','growthForm','trait','confidenceRanking','notes','citationSource']
for item in db:
    current_rec = []
    for term in lookup_terms:
        try:
            current_rec.append(item[term])
        except KeyError:
            print(item['taxon'])
            print(term)
    f_database.append(current_rec)

funguild_header = "Taxon\tTaxon Level\tTrophic Mode\tGuild\tGrowth Morphology\tTrait\tConfidence Ranking\tNotes\tCitation/Source"
funguild_header = funguild_header.split('\t')

total_length = len(f_database) #length of the database

p = range(1,11)
way_points = [int(total_length*(x/10.0)) for x in p]
############################################################################################

# Open the OTU table and read in the header ################################################
print("")
print("Reading in the OTU table: '%s'" %(args.otu))
print("")

#load the header
with open(otu_file, 'r') as otu:
	header = otu.readline().strip('\n').strip('\r').split(otu_delimiter)

#Attach all columns of database file to the header of the new OTU table
for item in funguild_header:
	header.append(item)
lookup = 'taxonomy'
#look for Taxonomy or taxonomy
if 'taxonomy' in header:
    lookup = 'taxonomy'
elif 'Taxonomy' in header:
    lookup = 'Taxonomy'

# get the positions of the taxonomy column and Notes column
#print(header)
index_tax = header.index(lookup)
index_notes = header.index('Notes')

#Abort if the column 'taxonomy' is not found
if index_tax == -1:
	print("Column 'taxonomy' not found. Please check you OTU table %s." %(otu_file))
	sys.exit(0)
############################################################################################

#Search in function database################################################################
# Read the OTU table into memory, and separate taxonomic levels with '@'.
with open(otu_file, 'r') as otu:
	otu_tab = []
	for record in otu:
		otu_current = record.strip('\n').strip('\r').split(otu_delimiter)
		otu_taxonomy = otu_current[index_tax]
		replace_list = ['_', ' ', ';', ',', ':']
		for symbol in replace_list:
			otu_taxonomy = otu_taxonomy.replace(symbol, '@')
		otu_taxonomy = otu_taxonomy + '@'
		otu_current[index_tax] = otu_taxonomy
		otu_tab.append(otu_current)
	otu_tab = otu_tab[1:] # remove the header line

# Start searching the database
## Each record in the Fungal Guild Database is searched in the user's OTU table.
count = 0 # count of matching records in the OTU table
percent = 0 # line number in the database

otu_redundant = []
otu_new = []

print("Searching the FUNGuild database...")

#f_database = open(function_file, 'rU')
for function_tax in f_database:
    # report the progress
    percent += 1

    if percent in way_points:
        progress = (int(round(percent/total_length*100.0)))
        print('{}%'.format(progress))
    else: t = 0

    # Compare database with the OTU table
    #function_tax = record.split('\t')
    search_term = function_tax[0].replace(' ', '@') #first column of database, contains the name of the species
    search_term = '@' + search_term + '@' #Add @ to the search term

    for otu in otu_tab:
        otu_tax = otu[index_tax] # Get the taxonomy string of current OTU record.
        if otu_tax.find(search_term) >= 0: #found the keyword in this OTU's taxonomy
            count += 1 # Count the matching record
            otu_new = otu[:]

            # Assign the matching functional information to current OTU record.
            for item in function_tax:
                otu_new.append(item)
            otu_redundant.append(otu_new)

# Finish searching, delete the temp function database file

print("")
print("Found %i matching taxonomy records in the database."%(count))
print("Dereplicating and sorting the result...")

#Dereplicate and write to output file##########################################################
#Sort by OTU names and Level. Level is sorted from species to kingdom.
otu_sort = otu_redundant[:]
otu_sort.sort(key = itemgetter(index_tax), reverse = True) # Sort the redundant OTU table by Taxonomic Level.
otu_sort.sort(key = itemgetter(0)) # Sort the redundant OTU table by OTU ID.

#Dereplicate the OTU table, unique OTU ID with lowest taxonomic level will be kept.
otu_id_list = []
unique_list = []
count = 0

for item in otu_sort:
    if item[0] not in otu_id_list:
        count += 1
        otu_id_list.append(item[0])
        unique_list.append(item)

#Copy the original taxonomy string (without @) to the unique OTU table
otu_tax = []
with open(otu_file, 'r') as f_otu:
    for otu in f_otu:
        temp = otu.rstrip('\n').split(otu_delimiter)
        otu_tax.append(temp)
    otu_tax = otu_tax[1:]

for new_rec in unique_list:
    for rec in otu_tax:
        if new_rec[0] == rec[0]:
            new_rec[index_tax] = rec[index_tax]
#Sort the new otu table by the total sequence number of each OTU.
unique_list.sort(key=lambda x: float(sum(map(float,x[1:index_tax]))), reverse=True)
################################################################################################

#Write to output files##############################################################################
#Output matched OTUs to a new file
if args.matched:
    if os.path.isfile(matched_file) == True:
        os.remove(matched_file)
    output = open(matched_file,'a')
	#Write the matched list header
    output.write('%s' % ('\t'.join(header))) #Header

	#Write the matched OTU table
    for item in unique_list:
        item[-1] = item[-1].encode('utf-8')
        rec = '\t'.join([str(i) for i in item])
        output.write('%s' % rec)
    output.close()

#Output unmatched OTUs to a new file
unmatched_list = []

for rec in otu_tax:
	count2 = 0
	for new_rec in unique_list:
		if rec[0] == new_rec[0]: #Check if the current record is in the unique_list (has been assigned a function)
			count2 += 1
	if count2 == 0:
		unmatched_list.append(rec)

count_unmatched = 0

#Add 'Unassigned' to the 'Notes' column
for item in unmatched_list:
	l = len(header) - len(item)
	for i in range(l):
		item.extend('-')
	item[index_notes] = 'Unassigned'

if args.unmatched:
	if os.path.isfile(unmatched_file) == True:
		os.remove(unmatched_file)
	output_unmatched = open(unmatched_file, 'a')
	output_unmatched.write('%s' % ('\t'.join(header)))
	for item in unmatched_list:
		rec = '\t'.join(item)
		output_unmatched.write('%s\n' % rec)
		count_unmatched += 1
	output_unmatched.close()

#Output the combined matched and unmatched OTUs to a new file
if os.path.isfile(total_file) == True:
	os.remove(total_file)

total_list = unique_list + unmatched_list #Combine the two OTU tables
total_list.sort(key=lambda x: float(sum(map(float,x[1:index_tax]))), reverse=True) #Sorted the combined OTU table

count_total = 0
#print(total_list)
with open(total_file, 'w') as f:
    f.write('%s\n' % ('\t'.join(header)))
    for line in total_list:
        try:
            #line[-1] = line[-1].encode('utf-8')
            output_line = '\t'.join([str(i) for i in line])
        except UnicodeEncodeError:
            #print("This record has unsupported Unicode, please report to the develop team.")
            output_line = '\t'.join([str(i) for i in line[:-1]])
        except AttributeError:
            output_line = '\t'.join([str(i) for i in line[:-1]])
        count_total += 1
        f.write('%s\n' % output_line)

####################################################################################################################

#print(report on the screen#########################################################################################
print("FunGuild tried to assign function to %i OTUs in '%s'."  %(count_total, otu_file))
print("FUNGuild made assignments on %i OTUs." %(count))
print("Result saved to '%s'" %(total_file))

if args.matched or args.unmatched:
	print('\nAdditional output:')
	if args.matched:
		print("FUNGuild made assignments on %i OTUs, these have been saved to %s." %(count, matched_file))
	if args.unmatched:
		print("%i OTUs were unassigned, these are saved to %s." %(count_unmatched, unmatched_file))

# Finish the program
stop = timeit.default_timer()
runtime = round((stop-start),2)
print("\nTotal calculating time: {} seconds.".format(runtime))
####################################################################################################################
