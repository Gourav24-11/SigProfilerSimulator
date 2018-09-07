#!/usr/bin/env python3

#This file is part of Mutational Signatures Project.

#Mutational Signatures Project: need info on project

#Copyright (C) 2018 Erik Bergstrom

#

#Mutational Signatures is free software: need to include distribtution

#rights and so forth

#

#Mutational Signatures is distributed in the hope that it will be useful,

#but WITHOUT ANY WARRANTY; without even the implied warranty of

#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the

#GNU General Public License for more details [change to whatever group we should include.
 

#Author: Erik Bergstrom

#Contact: ebergstr@eng.ucsd.edu


import time
import sys
import random
import os
import pickle
import subprocess
import argparse


start_run = time.time()


#################################### Functions ###########################################


revcompl = lambda x: ''.join([{'A':'T','C':'G','G':'C','T':'A','N':'N'}[B] for B in x][::-1])

def chrom_proportions (chrom_path, genome, chromosomes):
    '''
    Creates a text file that contains the proportional size of each chromosome in relation to 
    the entire genome. The proportions are saved into a list.

    Parameters:
         chrom_path  -> path to the chromosome string files
             genome  -> name of the genome of interest
        chromosomes  -> list of chromosomes for the species of interest

    Returns:
        None

    Outputs:
        -> a text file saved into the chrom_path with the name:
           genome + _proportions.txt (ex: GRCh37_proportions.txt)
    '''
    chromosome_lengths = []
    chromosomeProbs = []
    total_length = 0
    for chrom in chromosomes:
        with open (chrom_path + chrom + ".txt") as f:
            chromosome = f.readline().strip()
            chromosome_lengths.append(len(chromosome))
            total_length += len(chromosome)

    for lengths in chromosome_lengths:
        chromosomeProbs.append(lengths/total_length)
    print(chromosomeProbs)
    with open (chrom_path + genome + "_proportions.txt", 'wb') as out:
        pickle.dump(chromosomeProbs, out)




def update_chromosome ( chrom, location, bases, context):
    '''
    Updates a given chromosome or sequence based upon a given context.
    
    Parameters:
        chrom => sequence
        location => starting position of desired update in the sequence 
        bases => desired bases to update (del, ins, SNP, Dinuc, etc.)
        context => simulation context (INDEL, DINUC, SNP)
    
    Returns:
        returns => updated chromosome
        
    Example:
        
        update_chromosome (1.txt, 10546, 'ACG', 'Ins')
        output => original chromosome ( ...GAAATCT...) becomes ( ...GAAA[ACG]TCT...)
    '''
    chromosome = chrom

    if context == 'Del':
        chromosome = chrom[:location] + chrom[location+len(bases):]
    elif context == 'Ins':
        chromosome = chrom[:location+1] + bases + chrom[location+1:]
    elif context == 'SNP':
        chromosome = chrom[:location] + bases + chrom[location+1:]
    else:
        chromosome = chrom[:location] + bases + chrom[location+2:]
        
        
    return(chromosome)


def random_base (limit_start, limit_end):
    '''
    Returns a random nucleotide.

    Inputs: None

    Returns: A, C, G, or T
    '''

    return (('ATCG')[random.randint(limit_start,limit_end)])



def mutation_preparation (catalogue_file):
    '''
    Returns a list of all sample names and a dictionary containing the mutation count
        for each mutation type for a given context.
        
    Parameters:
        catalogue_file -> a mutational matrix catalgoue that includes the number of mutations
                          for a given mutation type for a given sample

    Returns:
        sample_names  -> list of all sample names
             samples  -> dictionary containing the mutation count for each mutation type
                         for a given context.

    Example return value:
        sample_names = ['PDXXXX', 'PDYYYY', ...]
        samples = {'PDXXXX':{'A[A>C]A':35, 'A[A>T]A':12, ...}
                   'PDYYYY':{'A[A>C]A':23, 'A[A>T]A':9,  ...}}
    '''
    
    # Obtains all of the samples of interest from the input file
    with open (catalogue_file) as f:
        first_line = f.readline().strip().split('\t')
    sample_names = first_line[1:]
    #sample_names = [first_line[5]]

    # Save the mutation counts for each sample for each nucleotide context
    samples = dict()
    nucleotides = []
    with open (catalogue_file) as f:
        next(f)
        for lines in f:
            line = lines.strip().split()
            nuc = line[0]            
            sample_index = 1
            #sample_index = 5
            for sample in sample_names:
                mutCount = int(line[sample_index])
                if sample not in samples.keys():
                    samples[sample] = {nuc:mutCount}
                else:
                    samples[sample][nuc] = int(mutCount)
                sample_index += 1  

    print("File successfully read and mutations collected. Mutation assignment starting now.")
    return (sample_names, samples)
    
    
    
    
    
    
def mut_tracker (sample_names, samples, reference_sample, nucleotide_context_file, sim, chromosome_string_path, genome, chromosomes):
    '''
    Returns a dictionary that contains the number of mutations allocated to each chromosome
        for a given nucleotide context for a given sample.
        
    Parameters:
                   sample_names  -> list of all samples
                        samples  -> dictionary containing the mutation count for each mutation type
                                    for a given context.
               reference_sample  -> uses the first sample in the list as a reference 
        nucleotide_context_file  -> contains the chromosome proportion for each nucleotide
                            sim  -> context dependent parameter
         chromosome_string_path  -> path to the chromosome reference files
                         genome  -> version of the genome desired as the reference
                    chromosomes  -> list of chromosomes for the species of interest

    Returns:
        mutation_tracker  -> a dictionary that contains the number of mutations allocated to each chromosome
                             for a given nucleotide context for each sample.

    Example return value:
        mutation_tracker = {'PDXXXX':{'A[A>C]A':{'X':2,'Y':1,'1':4,...},
                                     {'A[A>T]A':{'X':2,'Y':1,...}, ...}
                            'PDYYYY':{'A[A>C]A':{'X':1,'Y':3,'1':1,...},
                                     {'A[A>T]A':{'X':3,'Y':2,...}, ...}}
    This function allocates the mutations based upon the size of the chromosome.
    
    '''

    # Allocates mutations differently from INDEL simulation
    if sim != 6:
        mutation_tracker = {}
        nuc_probs = {}

        # Opens and saves the context distribution for each nucleotide
        with open (nucleotide_context_file) as f:
                next(f)
                for lines in f:
                    line = lines.strip().split(',')
                    nuc = line[0]
                    line[1:] = list(map(float, line[1:]))
                    nuc_probs[nuc] = line[1:]



        for sample in sample_names:
            for nuc in samples[reference_sample].keys():
                chrom_index = 0;
                nuc_count = 0;

                # Organizes the nucleotides and context dependent nucleotides
                # for allocation purposes
                if sim == 2: 
                    base_nuc = nuc[0] + nuc[2] + nuc[6]
                elif sim == 4:
                    base_nuc = nuc[0:3] + nuc[4] + nuc[8]
                elif sim == 3:
                    base_nuc = nuc[0:2] + nuc[3] + nuc[7:]
                elif sim == 5:
                    base_nuc = nuc[0:2]

                if sample not in mutation_tracker.keys():
                    mutation_tracker[sample] = {nuc:{}}

                # Allocates mutations proportionaly based upon the context
                # distributions
                for chroms in chromosomes:
                    mutation_count = int(samples[sample][nuc]) * nuc_probs[base_nuc][chrom_index]
                    if mutation_count - int(mutation_count) > 0.5:
                        mutation_count = int(mutation_count) + 1
                        nuc_count += mutation_count
                    else:
                        mutation_count = int(mutation_count)
                        nuc_count += mutation_count
                    if nuc not in mutation_tracker[sample].keys():
                        mutation_tracker[sample][nuc] = {chroms:mutation_count}
                    else:
                        mutation_tracker[sample][nuc][chroms] = mutation_count
                    chrom_index += 1

                # Ensures that the correct number of mutations have been assinged
                if nuc_count != samples[sample][nuc]:
                    while True:
                        if nuc_count == samples[sample][nuc]:
                            break
                        else:
                            l = random.randint(0,23)
                            if nuc_probs[base_nuc][l] > 0:
                                random_chromosome = chromosomes[l]

                                if nuc_count < samples[sample][nuc]:
                                    mutation_tracker[sample][nuc][random_chromosome] += 1
                                    nuc_count += 1
                                else:
                                    if mutation_tracker[sample][nuc][random_chromosome] != 0:
                                        mutation_tracker[sample][nuc][random_chromosome] -= 1
                                        nuc_count -= 1
        

    # Allocates mutations for the INDEL simulation based upon the size
    # of each chromosome in relation to the overall size of the genome.
    else:
        with open (chromosome_string_path + genome + "_proportions.txt", 'rb') as probs:
            chromosomeProbs = pickle.load(probs)

        mutation_tracker = {}
        for sample in sample_names:
            for nuc in samples[reference_sample].keys():
                chrom_index = 0;
                nuc_count = 0;
                if sample not in mutation_tracker.keys():
                    mutation_tracker[sample] = {nuc:{}}

                # Allocates mutations based upong chromosome proportions
                for chroms in chromosomes:
                    mutation_count = int(samples[sample][nuc]) * chromosomeProbs[chrom_index]
                    if mutation_count - int(mutation_count) > 0.5:
                        mutation_count = int(mutation_count) + 1
                        nuc_count += mutation_count
                    else:
                        mutation_count = int(mutation_count)
                        nuc_count += mutation_count
                    if nuc not in mutation_tracker[sample].keys():
                        mutation_tracker[sample][nuc] = {chroms:mutation_count}
                    else:
                        mutation_tracker[sample][nuc][chroms] = mutation_count
                    chrom_index += 1

                # Ensures that the correct number of mutations have been assinged
                if nuc_count != samples[sample][nuc]:
                    while True:
                        if nuc_count == samples[sample][nuc]:
                            break
                        else:
                            l = random.randint(0,23)
                            random_chromosome = chromosomes[l]
                            if nuc_count < samples[sample][nuc]:
                                mutation_tracker[sample][nuc][random_chromosome] += 1
                                nuc_count += 1
                            else:
                                if mutation_tracker[sample][nuc][random_chromosome] != 0:
                                    mutation_tracker[sample][nuc][random_chromosome] -= 1
                                    nuc_count -= 1
    
    print ("Mutations have been distributed. Starting simulation now...")
    return (mutation_tracker)
    
    
    
    
    
    
    

def simulator (sample_names, samples, mutation_tracker, chromosome_string_path, chromosome_TSB_path, simulation_number, output_path, sim, mut_start, mut_save, updating, chromosomes, test, genome, context):
    '''
    Simulates mutational signatures in human cancer in an unbiased fashion. The function
        requires a list of sample names, a dictionary of the number of mutations for each
        nucleotide context for each sample, and a dictionary with the mutations allocated
        proportionally to every chromosome. This function also requires that a local 
        copy of each chromosome be saved as a string within individual files ('1.txt', 
        '2.txt', '3.txt', etc). If TSB simulations are desired, the user must also save a
        local binary file for each chromosome that contains the transcriptional info (see
        blah.py for details on how to create the binary file for each chromosome). 
        
    Parameters:
        sample_names  -> list of all samples 
                         (ex: sample_names = ['PDXXXX', 'PDYYYY', ...])
        
                       samples  -> dicationary with mutation counts for each mutation type for each
                                   sample.
                                   (ex: samples  -> {'PDXXXX':{'A[A>C]A':35, 'A[A>T]A':12, ...}
                                                     'PDYYYY':{'A[A>C]A':23, 'A[A>T]A':9,  ...}})
              mutation_tracker  -> {'PDXXXX':{'A[A>C]A':{'X':2,'Y':1,'1':4,...},
                                             {'A[A>T]A':{'X':2,'Y':1,...}, ...}
                                    'PDYYYY':{'A[A>C]A':{'X':1,'Y':3,'1':1,...},
                                             {'A[A>T]A':{'X':3,'Y':2,...}, ...}}
        chromosome_string_path  -> path to the chromosome reference files
           chromosome_TSB_path  -> path to the transcriptional strand reference files for each
                                   chromosome
             simulation_number  -> desired simulation number
                   output_path  -> output path for the simulations
                           sim  -> context dependent parameter
                     mut_start  -> context dependent parameter used to pull sequences of interest
                      mut_save  -> context dependent parameter used to pull sequences of interest
                      updating  -> single value to determine whether updating should occur. 
                   chromosomes  -> list of chromosomes for the given genome
                        genome  -> reference genome used for simulation
                       context  -> desired nucleotide context for simulation

    Returns:
        None 

    Output: 
        Writes the output to a single vcf file per folder for each desired context.
        See https://samtools.github.io/hts-specs/VCFv4.2.pdf for an example vcf format.

    '''

    # Saves the chromosome as a string in memory
    for chrom in chromosomes:
        with open (chromosome_string_path + chrom + ".txt") as f:
            initial_seq = f.readline().strip()
            
        # Only for TSB simulations, opens the transcriptional info strings:
        if sim == 4:
            with open (chromosome_TSB_path + chrom + "_192.txt", 'rb') as f:
                chrom_bias = f.read()
        

        for sample in sample_names:
            # Saves an unaltered chromosome, so that future updating of mutations
            # does not affect additional simulations.
            sequence = initial_seq
            simulations = simulation_number

            sample_path = output_path + sample + "/"
            if not os.path.exists(sample_path):
                os.makedirs(sample_path)

            while(simulations > 0):
                # Creates the output path if it does not already exist.  
                if not os.path.exists(output_path):
                    os.makedirs(output_path)

                # Takes the desired mutations for the current sample and chromosome and 
                # removes any nucleotides which have 0 allocated mutations    
                outputFile = sample_path + sample + "_" + str(sys.argv[1]) + "_" + str(simulations) + ".txt"
                with open(outputFile, "a") as out:
                    mutationsCount = {}
                    for nuc in samples[sample].keys():
                        mutationsCount[nuc] = mutation_tracker[sample][nuc][chrom]
                    initial_nuc_keys = list(mutationsCount.keys())
                    for nuc in initial_nuc_keys:
                        if mutationsCount[nuc] == 0:
                            del mutationsCount[nuc]

                    nuc_keys = list(mutationsCount.keys())
                    base_keys = []

                    # Simulations for INDEL context
                    if sim == 6: 

                        indel_lengths = []
                        repeat_lengths = []
                        indel_types = {}
                        indel_types_O = {}
                        indel_types_M = {}

                        # Organizes data structures to keep track of the desired INDEL mutations
                        for indels in mutationsCount.keys(): 
                            indel = indels.split(':')
                            if int(indel[0]) == 5 and int(indel[3]) == 5 and indel[2] == 'M':
                                indel_lengths.append(6)
                            else:
                                indel_lengths.append(int(indel[0]))

                            repeat_lengths.append(int(indel[3]))
                            # Saves the Insertion mutations with 0 repeats in a separate data structure
                            if indel[3] == '0' and indel[1] == 'Ins':
                                if (indel[0]+indel[3] + indel[2]) not in indel_types_O.keys():
                                    indel_types_O[(indel[0]+indel[3] + indel[2])] = [indel[1]]

                            # Saves the Insertion mutations for microhomologies separately
                            elif indel[1] == 'Ins' and indel[2] == 'M':
                                if (indel[0]+indel[3] + indel[2]) not in indel_types_M.keys():
                                    indel_types_M[(indel[0]+indel[3] + indel[2])] = [indel[1]]

                            # Saves all other INDEL mutations in a single data structure
                            else:
                                if (indel[0]+indel[3] + indel[2]) not in indel_types.keys():
                                    indel_types[(indel[0]+indel[3] + indel[2])] = [indel[1]]
                                else:
                                    indel_types[(indel[0]+indel[3] + indel[2])].append(indel[1])

                        # Repeats simulation until all mutations are assigned
                        while (any(mutationsCount) == True):
                            while (any(indel_types)) == True:

                                # Randomly chooses a location on the current chromosome
                                location_range = len(sequence)
                                random_number = random.randint(0, location_range)

                                # Pulls out the largest desired INDEL
                                for i in range (max(indel_lengths), 0, -1):
                                    inDel = sequence[random_number:i+random_number]

                                    # Ensures that all bases are known in the potential mutation
                                    if 'N' not in inDel:
                                        repeat_count = 0
                                        repeat_count_ins = 0


                                        # Counts the number of repeats of the INDEL in the forward direction
                                        for k in range (1, max(repeat_lengths)+1, 1):            
                                            if sequence[random_number+(k*i):random_number+((k+1)*i)] == inDel:
                                                repeat_count += 1
                                            else:
                                                break


                                        # Counts the number of repeats of the INDEL in the reverse direction
                                        for l in range (1, max(repeat_lengths)+1, 1):
                                            if sequence[random_number-(l*i):(random_number-(l*i))+i] == inDel:
                                                repeat_count += 1
                                            else:
                                                break

                                        # Organizes a naming structure for the current INDEL chosen on the chromosome
                                        mainType = str(i) + str(repeat_count+repeat_count_ins)
                                        mainType_ins = str(i) + str(repeat_count+1+repeat_count_ins) 
                                        subType = None
                                        complete_indel = None

                                        # Assigns the subtype category for the INDEL based on its context
                                        if i != 1:
                                            subType = 'R'
                                        else:
                                            if sequence[random_number] == 'A' or sequence[random_number] == 'T':
                                                subType = 'T'
                                            else:
                                                subType = 'C'
                                    
                                        # Saves a type for a deleltion and an insertion option
                                        mainType += subType
                                        mainType_ins += subType


                                        # Checks to see this randomly chosen INDEL is a desired deletion mutation
                                        if mainType in indel_types.keys():
                                            if indel_types[mainType][0] == 'Del':

                                                # Reassigns the original naming convention for the INDEL and writes it to the output file
                                                complete_indel = mainType[0] + ':Del:' + subType + ':' + mainType[1]
                                                #print (complete_indel + "\tGRCh37\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number+i) + "\t" + sequence[random_number-1:i+random_number] + "\t" + sequence[random_number-1] + "\t" +  sequence[random_number-1-(l*i):random_number-1 + ((k+1)*i)], file=out)
                                                print (test + "\t" + sample + "\tSimulation\t" + genome + "\tINDEL\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number+i) + "\t" + sequence[random_number-1:i+random_number] + "\t" + sequence[random_number-1] + "\tSOMATIC", file=out)
                                                # Updates the chromosome with the given mutation if desired
                                                if updating:
                                                    sequence = update_chromosome(sequence, random_number, sequence[random_number:i+random_number], 'Del')
                                             
                                                # Remove one mutation count for the current INDEL and update all relevant data structures
                                                mutationsCount[complete_indel] -= 1
                                                if mutationsCount[complete_indel] == 0:
                                                    del mutationsCount[complete_indel]
                                                    indel_lengths.remove(int(mainType[0]))
                                                    repeat_lengths.remove(repeat_count+repeat_count_ins)
                                                    if len(indel_types[mainType]) > 1:
                                                        del indel_types[mainType][0]
                                                    else:
                                                        del indel_types[mainType]
                                                break

                                        # Checks to see this randomly chosen INDEL is a desired insertion mutation
                                        if mainType_ins in indel_types.keys():
                                            if indel_types[mainType_ins][0] == 'Ins':

                                                #Reassigns the original naming convention for the INDEL and writes it to the output file
                                                complete_indel = mainType_ins[0] + ':Ins:' + subType + ':' + mainType_ins[1]
                                                potential_sequence = sequence[random_number:i+random_number]
                                                #print (complete_indel + "\tGRCh37\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number+i) + "\t" + sequence[random_number-1] + "\t" + sequence[random_number-1]+potential_sequence + "\t" + sequence[random_number-1-(l*i):random_number]+'['+potential_sequence+']'+sequence[random_number:random_number + ((k+1)*i)], file=out)
                                                print (test + "\t" + sample + "\tSimulation\t" + genome + "\tINDEL\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number+i) + "\t" + sequence[random_number-1:i+random_number] + "\t" + sequence[random_number-1] + "\tSOMATIC", file=out)

                                                # Updates the chromosome with the given mutation if desired
                                                if updating:
                                                    sequence = update_chromosome(sequence, random_number, sequence[random_number:i+random_number], 'Ins')
                                            

                                                # Remove one mutation count for the current INDEL and update all relevant data structures
                                                mutationsCount[complete_indel] -= 1
                                                if mutationsCount[complete_indel] == 0:
                                                    del mutationsCount[complete_indel]
                                                    indel_lengths.remove(int(mainType_ins[0]))
                                                    repeat_lengths.remove(repeat_count+1+repeat_count_ins)
                                                    if len(indel_types[mainType_ins]) > 1:
                                                        del indel_types[mainType_ins][0]
                                                    else:
                                                        del indel_types[mainType_ins]
                                                break


                                        # Simulates microhomology deletions
                                        else:
                                            max_repeat_length = max(repeat_lengths)+1
                                            if max_repeat_length > i:
                                                max_repeat_length = i


                                            # Counts homology in the forward direction
                                            homology_size1 = 0
                                            for k in range (1, max_repeat_length, 1):
                                                if sequence[random_number+i:random_number+k+i] == inDel[:k]:
                                                    homology_size1 += 1
                                                else:
                                                    break

                                            # Counts homology in the reverse direction
                                            homology_size2  = 0
                                            for l in range (1, max_repeat_length, 1):
                                                if sequence[random_number-l:random_number] == inDel[-l:]:
                                                    homology_size2 += 1
                                                else:
                                                    break

                                            # Assigns a new naming convetion for the current INDEL
                                            subType = 'M'
                                            if i > 5 and (homology_size1 >= 5 or homology_size2 >= 5):
                                                mainType1 = str(i-1) + str(homology_size1) + subType
                                                mainType2 = str(i-1) + str(homology_size2) + subType
                                            else:
                                                mainType1 = str(i) + str(homology_size1) + subType
                                                mainType2 = str(i) + str(homology_size2) + subType
                                            complete_indel = None
                                            
                                            # Checks to see if the forward homology is desired and that the reverse
                                            # homology equals 0. 
                                            if mainType1 in indel_types.keys() and homology_size2 == 0:
                                                if indel_types[mainType1][0] == 'Del' and sequence[random_number+i:random_number+(2*i)] != sequence[random_number:random_number+i] and sequence[random_number-i:random_number] != sequence[random_number:random_number+i]:

                                                    # Reassigns the original naming convention for the INDEL and writes it to the output file
                                                    complete_indel = mainType1[0] + ':Del:' + subType + ':' + mainType1[1]
                                                    #print (complete_indel + "\tGRCh37\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number+i) + "\t" + sequence[random_number-1:i+random_number] + "\t" + sequence[random_number-1] + "\t" +  sequence[random_number-5:random_number + 6 + k], file=out)
                                                    print (test + "\t" + sample + "\tSimulation\t" + genome + "\tINDEL\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number+i) + "\t" + sequence[random_number-1:i+random_number] + "\t" + sequence[random_number-1] + "\tSOMATIC", file=out)

                                                    # Updates the chromosome with the current INDEL if desired
                                                    if updating:
                                                        sequence = update_chromosome(sequence, random_number, sequence[random_number:i+random_number], 'Del')
                                             
                                                    # Remove one mutation count for the current INDEL and update all relevant data structures       
                                                    mutationsCount[complete_indel] -= 1
                                                    if mutationsCount[complete_indel] == 0:
                                                        del mutationsCount[complete_indel]
                                                        indel_lengths.remove(i)
                                                        repeat_lengths.remove(homology_size1)
                                                        if len(indel_types[mainType1]) > 1:
                                                            del indel_types[mainType1][0]
                                                        else:
                                                            del indel_types[mainType1]
                                                    break


                                            # Checks to see if the reverse homology is desired and that the forward
                                            # homology equals 0.
                                            elif mainType2 in indel_types.keys() and homology_size1 == 0:
                                                if indel_types[mainType2][0] == 'Del' and sequence[random_number+i:random_number+(2*i)] != sequence[random_number:random_number+i] and sequence[random_number-i:random_number] != sequence[random_number:random_number+i]:

                                                    # Reassigns the original naming convention for the INDEL and writes it to the output file
                                                    complete_indel = mainType2[0] + ':Del:' + subType + ':' + mainType2[1]
                                                    #print (complete_indel + "\tGRCh37\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number+i) + "\t" + sequence[random_number-1:i+random_number] + "\t" + sequence[random_number-1] + "\t" +  sequence[random_number-5-l:random_number + 6], file=out)
                                                    print (test + "\t" + sample + "\tSimulation\t" + genome + "\tINDEL\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number+i) + "\t" + sequence[random_number-1:i+random_number] + "\t" + sequence[random_number-1] + "\tSOMATIC", file=out)

                                                    # Updates the chromosome with the current INDEL if desired
                                                    if updating:
                                                        sequence = update_chromosome(sequence, random_number, sequence[random_number:i+random_number], 'Del')

                                                    # Remove one mutation count for the current INDEL and update all relevant data structures
                                                    mutationsCount[complete_indel] -= 1
                                                    if mutationsCount[complete_indel] == 0:
                                                        del mutationsCount[complete_indel]
                                                        indel_lengths.remove(i)
                                                        repeat_lengths.remove(homology_size2)
                                                        if len(indel_types[mainType2]) > 1:
                                                            del indel_types[mainType2][0]
                                                        else:
                                                            del indel_types[mainType2]
                                                    break

                                        out.flush()

                            # Simuales all micro-homology insertion mutations
                            for indels_M in indel_types_M.keys():

                                # Randomly chooses a location on the current chromosome
                                location_range = len(sequence)
                                random_number = random.randint(0, location_range)

                                # Assigns the original naming convention
                                complete_indel = indels_M[0] + ':Ins:' + indels_M[2] + ':' + indels_M[1]
                                
                                # Pulls the sequence of bases out for the current insertion homology
                                # equal to the length of the homology
                                M_length = int(indels_M[0])
                                if int(indels_M[0]) == 5 and int(indels_M[1]) == 5:
                                    M_length = 6

                                potential_sequence = sequence[random_number:random_number+int(indels_M[1])]

                                # Esnures that the region is known
                                if 'N' not in potential_sequence:
                                    
                                    # Saves the potential reverese homology sequence for reference. 
                                    reverse_homology = sequence[random_number-int(indels_M[1]):random_number]
                                    remaining_sequence = ''

                                    # Adds random bases to the end of the micro-homology, ensuring
                                    # that the added bases don't exceed the desired homology length
                                    for m in range (0, M_length-int(indels_M[1])-1, 1):
                                        while len(remaining_sequence) != 1:
                                            new_base = random_base(0,3)
                                            if new_base != sequence[random_number+int(indels_M[1])]:
                                                remaining_sequence += new_base
                                        potential_sequence += new_base#random_base(0,3)


                                    # Adds random bases until the desired insertion length is met,
                                    # without introducing reverse homology
                                    while len(potential_sequence) != M_length:
                                        last_base = random_base(0,3)
                                        if last_base != reverse_homology[-1]:
                                            potential_sequence += last_base

                                    # Prints the insertion micro-hommology if the insertion length is correct and the homology matches are correct
                                    if sequence[random_number-int(indels_M[1]):random_number] != potential_sequence[-int(indels_M[1]):] and sequence[random_number+M_length+int(indels_M[1]):random_number+M_length+(2*int(indels_M[1]))] != potential_sequence[:int(indels_M[1])] and sequence[random_number:random_number+int(indels_M[1])+1] != potential_sequence[:int(indels_M[1])+1]:
                                        #print (complete_indel + "\tGRCh37\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number+M_length) + "\t" + sequence[random_number-1] + "\t" + sequence[random_number-1]+potential_sequence + "\t" + sequence[random_number-5:random_number] + "[" + potential_sequence + "]" + sequence[random_number:random_number+int(indels_M[1])+M_length], file=out)
                                        print (test + "\t" + sample + "\tSimulation\t" + genome + "\tINDEL\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number+i) + "\t" + sequence[random_number-1:i+random_number] + "\t" + sequence[random_number-1] + "\tSOMATIC", file=out)

                                        # Remove one mutation count for the current INDEL and update all relevant data structures
                                        mutationsCount[complete_indel] -= 1
                                        if mutationsCount[complete_indel] == 0:
                                            del mutationsCount[complete_indel]
                                            indel_lengths.remove(M_length)
                                            repeat_lengths.remove(int(indels_M[1]))
                                            del indel_types_M[indels_M]
                                        break

                                        # Updates the chromosome with the current INDEL if desired
                                        if updating:
                                            sequence = update_chromosome(sequence, random_number, sequence[random_number:int(indels_M[0])+random_number], 'Ins')

                                        out.flush()


                            # Simulates the insertion INDELs that have 0 repeats
                            while (any(indel_types_O) == True):

                                # Randomly chooses a location on the current chromosome
                                location_range = len(sequence)
                                random_number = random.randint(0, location_range)

                                # Assigns a subtype for the chosen position on the chromosome
                                if sequence[random_number] == 'T' or sequence[random_number] == 'A':
                                    subType = 'T'
                                elif sequence[random_number] == 'G' or sequence[random_number] == 'C':
                                    subType = 'C'
                                else:
                                    break


                                for indels_O in indel_types_O.keys():

                                    # For INDELs of length 1, if the subType for the mutation does not match
                                    # the desired INDEL, break and find a new position
                                    if indels_O[0] == '1':
                                        if indels_O[2] != subType:
                                            break

                                    # Assigns the original naming convention
                                    complete_indel = indels_O[0] + ':Ins:' + indels_O[2] + ':' + indels_O[1]

                                    # Randomly assigns a base for insertions of length 1 based upon
                                    # the subType at the chosen position in the chromosome.
                                    potential_sequence = ''
                                    if int(indels_O[0]) == 1:
                                        if subType == 'T':
                                            potential_sequence += random_base(0,1)
                                        else:
                                            potential_sequence += random_base(2,3)

                                    # Randomly chooses bases until the insertion length equals the desired
                                    # INDEL length
                                    else:
                                        for m in range (0, int(indels_O[0]), 1):
                                            potential_sequence += random_base(0,3)

                                    # Ensures that the bases are known and that there are no repeats around the insertion
                                    if "N" not in sequence[random_number-int(indels_O[0]):random_number+int(indels_O[0])]:
                                        if sequence[random_number:random_number+int(indels_O[0])] != potential_sequence and sequence[random_number-int(indels_O[0])] != potential_sequence:
                                            #print (complete_indel + "\tGRCh37\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number+int(indels_O[0])) + "\t" + sequence[random_number-1] + "\t" + sequence[random_number-1]+potential_sequence + "\t" + sequence[random_number-5:random_number]+'['+potential_sequence+']'+sequence[random_number:random_number+5], file=out)
                                            print (test + "\t" + sample + "\tSimulation\t" + genome + "\tINDEL\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number+i) + "\t" + sequence[random_number-1:i+random_number] + "\t" + sequence[random_number-1] + "\tSOMATIC", file=out)

                                            # Remove one mutation count for the current INDEL and update all relevant data structures
                                            mutationsCount[complete_indel] -= 1
                                            if mutationsCount[complete_indel] == 0:
                                                del mutationsCount[complete_indel]
                                                indel_lengths.remove(int(indels_O[0]))
                                                repeat_lengths.remove(int(indels_O[1]))
                                                del indel_types_O[indels_O]
                                            break

                                            # Updates the chromosome with the current INDEL if desired
                                            if updating:
                                                sequence = update_chromosome(sequence, random_number, sequence[random_number:int(indels_O[0])+random_number], 'Ins')
                                                    
                                            out.flush()
                                    break
                                
                                
                                
                                
                    # Simulation technique for all other contexts        
                    else:

                        # Organizes nucleotide keys for later reference.
                        for nuc in nuc_keys:
                            if sim == 2:
                                base_keys.append(nuc[0] + nuc[2] + nuc[6])
                            elif sim == 3:
                                base_keys.append(nuc[0:2] + nuc[3] + nuc[7:])
                            elif sim == 4:
                                base_keys.append(nuc[0] + nuc[2] + nuc[4] + nuc[8])
                            elif sim == 5:
                                base_keys.append(nuc[0:2])
                        
                        # Simulates until all mutations have been assigned.
                        l = 0            
                        while (any(mutationsCount) == True):

                            # Picks a random location to throw a mutation limited to the
                            # length of the current chromosome
                            location_range = len(sequence)
                            random_number = random.randint(0, location_range)
                            
                            # If a specific mutation cannot be assinged after x iterations,
                            # skip that nucleotide context. Helps to prevent the simulation from
                            # stalling on a rare/non-existent mutation
                            l += 1
                            if l > 1000000:
                                print (mutationsCount)
                                mutationsCount = {}
                            mutNuc = None
                            revCompMutNuc = None
                
                            # Only for TSB simulations: organizes nucleotide references
                            if sim == 4:
                                nuc_bias = None
                                try:
                                    bias = chrom_bias[random_number]
                                except:
                                    print (chrom, len(initial_seq), random_number)
                        
                                if bias == 0:
                                    nuc_bias = 'N'
                                elif bias == 1:
                                    nuc_bias = 'T'
                                elif bias == 2:
                                    nuc_bias = 'U'
                                elif bias == 3:
                                    nuc_bias = 'B'
                                mutNuc = nuc_bias + sequence[random_number - mut_start:random_number + mut_start+1]
                                revCompMutNuc = nuc_bias + revcompl(mutNuc[1:])

                            # For DINUC context: organizes nucleotide references
                            elif sim == 5:
                                mutNuc = sequence[random_number:random_number + 2]
                                revCompMutNuc = revcompl(mutNuc)       

                            # For all other contexts: organize nucleotide references                 
                            else:
                                mutNuc = sequence[random_number - mut_start:random_number + mut_start+1]
                                revCompMutNuc = revcompl(mutNuc)
                
                            
                            # If the nucleotide is desired (present in the mutation dictionary), write
                            # it to the output file and update the dictionary
                            bases = None
                            context = None
                            if mutNuc in base_keys:
                                nucIndex = base_keys.index(mutNuc)
                                if nuc_keys[nucIndex] in mutationsCount.keys() and mutationsCount[nuc_keys[nucIndex]] != 0:
    
                                    if sim != 5 and sim != 4:
                                        context = 'SNP'
                                        bases = nuc_keys[nucIndex][mut_save+2]
                                        #print (sample + "\tGRCh37\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number) + "\t" + nuc_keys[nucIndex][mut_save] + "\t" + nuc_keys[nucIndex][mut_save+2] + "\tfor\t" , file=out)
                                        print (test + "\t" + sample + "\tSimulation\t" + genome + "\tSNP\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number) + "\t" + nuc_keys[nucIndex][mut_save] + "\t" + nuc_keys[nucIndex][mut_save+2] + "\tSOMATIC" + "\tfor\t" , file=out)
                                    
                                    elif sim == 4:
                                        context = 'SNP'
                                        bases = nuc_keys[nucIndex][mut_save+2]
                                        #print (sample + "\tGRCh37\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number) + "\t" + nuc_keys[nucIndex][mut_save] + "\t" + nuc_keys[nucIndex][mut_save+2] + "\tfor\t" + str(chrom_bias[random_number]), file=out)
                                        print (test + "\t" + sample + "\tSimulation\t" + genome + "\tSNP\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number) + "\t" + nuc_keys[nucIndex][mut_save] + "\t" + nuc_keys[nucIndex][mut_save+2] + "\tSOMATIC" + "\tfor\t" + str(chrom_bias[random_number]), file=out)
                                    elif sim == 5:
                                        context = 'DINUC'
                                        bases = nuc_keys[nucIndex][mut_save+3:mut_save+5]
                                        #print (sample + "\tGRCh37\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number) + "\t" + nuc_keys[nucIndex][mut_save:mut_save+2] + "\t" + nuc_keys[nucIndex][mut_save+3:mut_save+5] + "\tfor\t", file=out)
                                        print (test + "\t" + sample + "\tSimulation\t" + genome + "\tDINUC\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number) + "\t" + nuc_keys[nucIndex][mut_save:mut_save+2] + "\t" + nuc_keys[nucIndex][mut_save+3:mut_save+5] + "\tSOMATIC" + "\tfor\t", file=out)
                                
                                    mutationsCount[nuc_keys[nucIndex]] -= 1
                                    if mutationsCount[nuc_keys[nucIndex]] == 0:
                                        del mutationsCount[nuc_keys[nucIndex]]
                                        del nuc_keys[nucIndex]
                                        del base_keys[nucIndex] 
                    
                            # If the reverse complement of the nucleotide context is desired,
                            # write it to the output file as the reverse complement.
                            elif revCompMutNuc in base_keys:
                                nucIndex = base_keys.index(revCompMutNuc)
                                if nuc_keys[nucIndex] in mutationsCount.keys() and mutationsCount[nuc_keys[nucIndex]] != 0:
                                    if sim != 5 and sim != 4:
                                        context = 'SNP'
                                        bases = revcompl(nuc_keys[nucIndex][mut_save+2])
                                        #print (sample + "\tGRCh37\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number) + "\t" + revcompl(nuc_keys[nucIndex][mut_save]) + "\t" + revcompl(nuc_keys[nucIndex][mut_save+2]) + "\trev\t", file=out)
                                        print (test + "\t" + sample + "\tSimulation\t" + genome + "\tSNP\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number) + "\t" + revcompl(nuc_keys[nucIndex][mut_save]) + "\t" + revcompl(nuc_keys[nucIndex][mut_save+2]) + "\tSOMATIC" + "\trev\t", file=out)
                                    elif sim == 4:
                                        context = 'SNP'
                                        bases = revcompl(nuc_keys[nucIndex][mut_save+2])
                                        #print (sample + "\tGRCh37\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number) + "\t" + revcompl(nuc_keys[nucIndex][mut_save]) + "\t" + revcompl(nuc_keys[nucIndex][mut_save+2]) + "\trev\t" + str(chrom_bias[random_number]), file=out)
                                        print (test + "\t" + sample + "\tSimulation\t" + genome + "\tSNP\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number) + "\t" + revcompl(nuc_keys[nucIndex][mut_save]) + "\t" + revcompl(nuc_keys[nucIndex][mut_save+2]) + "\tSOMATIC\trev\t" + str(chrom_bias[random_number]), file=out)
                                    elif sim == 5:
                                        context = 'DINUC'
                                        bases = revcompl(nuc_keys[nucIndex][mut_save+3:mut_save+5])
                                        print (test + "\t" + sample + "\tSimulation\t" + genome + "\tDINUC\t" + chrom + "\t" + str(random_number) + "\t" + str(random_number) + "\t" + revcompl(nuc_keys[nucIndex][mut_save:mut_save+2]) + "\t" + revcompl(nuc_keys[nucIndex][mut_save+3:mut_save+5]) + "\tSOMATIC\trev\t", file=out)
                       
                                    mutationsCount[nuc_keys[nucIndex]] -= 1
                                    if mutationsCount[nuc_keys[nucIndex]] == 0:
                                        del mutationsCount[nuc_keys[nucIndex]]
                                        del nuc_keys[nucIndex]
                                        del base_keys[nucIndex]

                            # If the user specified udpating mutations, proceeds to update the chromosome
                            # with the current mutation
                            if updating and bases != None:
                                sequence = update_chromosome(sequence, random_number, bases, context)
            
                            out.flush()
                        
                
                    simulations -= 1
        print("Chromosome " + chrom + " done")
    
    
    
    
def main():
    #############################Organize Files, Data, and Inputs#############################
    simulation_number = 1
    updating = False
    exome = False

    parser = argparse.ArgumentParser(description="Provide the necessary arguments to begin simulations.")
    parser.add_argument("--test", "-t",help="Provide a unique name for your samples. (ex: BRCA)")
    parser.add_argument("--genome", "-g",help="Provide a reference genome. (ex: GRCh37, GRCh38, mm10)")
    parser.add_argument("--context", "-c",help="Provide the nucleotide context (ex: 96, 192, 1536, 3072, INDEL, DINUC).")
    parser.add_argument("-e", "--exome", help="Optional parameter instructs script to create the catalogues using only the exome regions. Whole genome context by default", action='store_true')
    parser.add_argument("--simulations", "-s", help="Provide the number of simulations per sample. The defualt is 1 simulation per sample.")
    parser.add_argument("-u", "--update", help="Optional parameter. Determines whether the chromosomes are updated with the current mutation.", action='store_true')


    args=parser.parse_args()
    test = args.test
    genome = args.genome
    context = args.context
    simulation_number = int(args.simulations)
    updating = args.update
    if args.exome:
        exome = True

    species = None
    if genome.upper() == ('GRCH37' or 'GRCH38' or 'HG19' or 'HG38'): 
        species = "homo_sapiens"
    elif genome.upper() == 'MM10': 
        species = "mus_musculus"
    else:
        print(genome + " is not supported. The following genomes are supported:\nGRCh37, GRCh38, mm10")

    ############################## Reference chromsomes ######################################

    chromosomes = ['X', 'Y', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 
                   '13', '14', '15', '16', '17', '18', '19', '20', '21', '22']

    if species == 'mus_musculus':
        chromosomes = chromosomes[:19]

    # Ensures that all of the necessary paths and files exist and are ready for simulations

    # Ensures that the chromosome strings are saves properly:
    chromosome_string_path = "references/chromosomes/chrom_string/" + genome + "/"
    chromosome_fasta_path = "references/chromosomes/fasta/" + genome + "/"
    if os.path.exists(chromosome_string_path) == False or len(os.listdir(chromosome_string_path)) <= len(chromosomes):
        if os.path.exists(chromosome_fasta_path) == False or len(os.listdir(chromosome_fasta_path)) <= len(chromosomes):
            print("Chromosomes are not currently saved as individual text files. You will need to download the files from your database of interest.")
            print("Ex: Ensembl-> ftp://ftp.ensembl.org/pub/grch37/update/fasta/homo_sapiens/dna/")
            print("     UCSC Genome Browser -> http://hgdownload.soe.ucsc.edu/goldenPath/hg38/chromosomes/")
            proceed = input("Would you like to download the chromosomes for the " + genome + " assembly now?[Y/N]").upper()
            if proceed == 'Y':
                print("Downloading the chromosomes now...")
                try:
                    os.system("wget -r -l1 -c -N --no-parent -A '*.dna.chromosome.*' -nd -P " + chromosome_fasta_path + " ftp://ftp.ensembl.org/pub/release-93/fasta/"+species+"/dna/")
                    os.system("gunzip references/chromosomes/fasta/" + genome + "/*.gz")
                except:
                    proceed = input("You may not have wget or homebrew installed. Download those dependencies now?[Y/N]").upper()
                    if proceed == 'Y':
                        try:
                            os.system("brew install wget")
                        except:
                            os.system('/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"')
                            os.system("brew install wget")
                            os.system("wget -r -l1 -c -N --no-parent -A '*.dna.chromosome.*' -nd -P " + chromosome_fasta_path + " ftp://ftp.ensembl.org/pub/release-93/fasta/"+species+"/dna/")
                            os.system("gunzip references/chromosomes/fasta/" + genome + "/*.gz")
                            print("Chromosome fasta files for " + genome + " have been installed. Creating the chromosome string files now...")
                    else:
                        print("Simulation has stopped. Please download the chromosome files before proceeding with the simulations.")
                        sys.exit()
            else:
                print("Simulatoin has stopped. Please download the chromosome files before proceeding with the simulations.")
                sys.exit()

        print("Chromosome fasta files for " + genome + " have been installed. Creating the chromosome string files now...")
        os.system("python3 scripts/save_chrom_strings.py -g " + genome)
        print("Chromosome string files have been created. Continuing with simulations.")


    # Ensures that the chromosome proportions are saved 
    if os.path.exists(chromosome_string_path + genome + "_proportions.txt") == False:
        print("Chromosome proportion file does not exist. Creating now...")
        chromosomeProbs = chrom_proportions(chromosome_string_path, genome, chromosomes)
        print("Chromosome proportion file created. Proceeding with simulation...")

    # Ensures the catalogue file is saved for the given context
    catalogue_file = "references/matrix/" + test + ".genome.mut" + context # input file
    vcf_files = "references/vcf_files/" + test + "/"
    if os.path.exists (catalogue_file) == False:
        if os.path.exists (vcf_files) == False or len(os.listdir(vcf_files)) == 0:
            print ("Please place your vcf files for each sample into the 'references/vcf_files/[test]/' directory. Once you have done that, rerun this script.")
        else:
            proceed = input(test + ".genome.mut" + context + " does not exist. Would you like to create this file now? [Y/N]").upper()
            if proceed == 'Y':
                print("Creating the matrix file now. This may take some time...")
                if exome:
                    os.system("python3 scripts/sigProfilerMatrixGenerator.py -c " + context + " -g " + genome + " -t "+ test + " -e")
                else:
                    os.system("python3 scripts/sigProfilerMatrixGenerator.py -c " + context + " -g " + genome + " -t "+ test)
                print("The matrix file has been created. Continuing with simulations...")
            else:
                print("Simulation has stopped. Please create the catalogue file before continuing with simulations.")
                sys.exit()

    # Ensures that the transcriptional strand reference files are saved properly
    chromosome_TSB_path = "references/chromosomes/tsb/" + genome + "/"
    transcript_files = "references/chromosomes/transcripts/" + genome + "/"
    if len(os.listdir(transcript_files)) < 1 or os.path.exists(transcript_files) == False:
        print("Please download the transcript files before proceeding. You can download the files from 'http://www.ensembl.org/biomart/martview'.")
        print("Follow the format presented in the README file:\n\n\tGene stable ID  Transcript stable ID    Chromosome/scaffold name    Strand  Transcript start (bp)   Transcript end (bp)")
        sys.exit()
    if os.path.exists(chromosome_TSB_path) == False or len(os.listdir(chromosome_TSB_path)) < len(chromosomes):
        proceed = input("The transcriptional data has not been saved. Would you like to run the script now? [Y/N]").upper()
        if proceed == 'Y':
            print("Proceeding...")
            os.system("python3 scripts/save_tsb_192.py -g " + genome)

    # Esnures that the nucleotide context files are saved properly
    nucleotide_context_file = "references/chromosomes/context_distributions/context_distribution_" + genome + "_" + context + ".csv"
    if os.path.exists(nucleotide_context_file) == False and context != 'INDEL':
        proceed_nuc = input("The context distribution file does not exist. You will need to create this file before simulating. Would you like to run the script to generate this file now? [Y/N]").upper()
        if proceed_nuc == 'Y':
            os.system("python3 scripts/save_context_distribution_96_192_1536_DINUC.py -c " + context + " -g " + genome) 
            print("Context distribution file successfully created. Proceeding with simulation...")
        else:
            print("Simulation has stopped. Please generate the context distribution file before simulating.")
            sys.exit()


    output_path = "simulation_output/" + test + '_simulations_' + genome + '_' + context + '/'
    

    # Set parameters for 96, 1536, TSB, DINUC, or INDEL:
    sim = None
    mut_start = None
    mut_length = None
    if context == '96':
        sim = 2
        mut_start = 1
        mut_save = 2
    elif context == '1536':
        sim = 3
        mut_start = 2
        mut_save = 3
    elif context == '192':
        sim = 4 
        mut_start = 1
        mut_save = 4
    elif context == 'DINUC':
        sim = 5
        mut_start = 0
        mut_save = 0
    elif context == 'INDEL':
        sim = 6
        mut_save = 0
        mut_start = 0
        

    # Begin the simulation process
    mut_prep = mutation_preparation(catalogue_file)
    reference_sample = mut_prep[0][0]
    mut_dict = mut_tracker(mut_prep[0], mut_prep[1], reference_sample, nucleotide_context_file, sim, chromosome_string_path, genome, chromosomes)
    simulator(mut_prep[0], mut_prep[1], mut_dict, chromosome_string_path, chromosome_TSB_path, simulation_number, output_path, sim, mut_start, mut_save, updating, chromosomes, test, genome, context)
    
if __name__ == '__main__':
    main()

end_run = time.time()
run_time = end_run - start_run
print("Simulation completed\nJob took " , run_time, " seconds")
