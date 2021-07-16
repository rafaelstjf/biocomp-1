# -*- coding: utf-8 -*-

""" Apps.py. Parsl Application Functions (@) 2021

This module encapsulates all Parsl configuration stuff in order to provide a
cluster configuration based in number of nodes and cores per node.

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
"""

# COPYRIGHT SECTION
__author__ = "Diego Carvalho"
__copyright__ = "Copyright 2021, The Biocomp Informal Collaboration (CEFET/RJ and LNCC)"
__credits__ = ["Diego Carvalho", "Carla Osthoff", "Kary Ocaña", "Rafael Terra"]
__license__ = "GPL"
__version__ = "1.0.1"
__maintainer__ = "Diego Carvalho"
__email__ = "d.carvalho@ieee.org"
__status__ = "Research"


#
# Parsl Bash and Python Applications
#
from pandas.core import base
import parsl
from bioconfig import BioConfig


# setup_phylip_data bash app
@parsl.python_app(executors=['single_thread'])
def setup_phylip_data(basedir: str, config: BioConfig,
                      stderr=parsl.AUTO_LOGNAME,
                      stdout=parsl.AUTO_LOGNAME):
    """Convert the gene alignments from the nexus format to the phylip format.

    Parameters:
        cbasedir: it is going to search for a tar file with nexus files. The script will create:
            seqdir=input/nexus
            seqdir=input/phylip
    Returns:
        returns an parsl's AppFuture.

    Raises:
        PhylipMissingData --- if cannot find a tar file with nexus files.


    TODO: Provide provenance.

    NB:
        Stdout and Stderr are defaulted to parsl.AUTO_LOGNAME, so the log will be automatically 
        named according to task id and saved under task_logs in the run directory.
    """
    import os
    import glob
    from appsexception import PhylipMissingData

    input_dir = os.path.join(basedir,'input')
    input_nexus_dir = os.path.join(input_dir, 'nexus')
    # So, some work must be done. Build the Nexus directory
    if not os.path.isdir(input_nexus_dir):
        os.mkdir(input_nexus_dir)
        # List all tar.gz files, they are supposed to be the input
        tar_file_list = glob.glob(f'{input_dir}/*.tar.gz')
        if len(tar_file_list) == 0:
            raise PhylipMissingData(input_dir)
        # So, loop over and untar every file
        for tar_file in tar_file_list:
            os.system(f'cd {input_nexus_dir}; tar zxvf {tar_file}')
    # Now, use the function to convert nexus to phylip.
    import sys
    sys.path.append(config.script_dir)
    import data_management as dm
    dm.nexus_to_phylip(input_nexus_dir) 
    return


# raxml bash app
@parsl.bash_app(executors=['raxml'])
def raxml(basedir: str, config: BioConfig,
          input_file: str,
          inputs=[],
          stderr=parsl.AUTO_LOGNAME,
          stdout=parsl.AUTO_LOGNAME):
    """Runs the Raxml's executable (RPS) on a gene alignment

    Parameters:
        TODO:
    Returns:
        returns an parsl's AppFuture

    TODO: Provide provenance.

    NB:
        Stdout and Stderr are defaulted to parsl.AUTO_LOGNAME, so the log will be automatically 
        named according to task id and saved under task_logs in the run directory.
    """
    import os
    import random
    import logging

    num_threads = config.raxml_threads
    raxml_exec = config.raxml
    exec_param = config.raxml_exec_param

    logging.info(f'raxml called with {basedir}')
    raxml_dir = basedir + '/' + config.raxml_dir

    # TODO: Create the following parameters(external configuration): -m, -N,
    flags = f"-T {num_threads} {exec_param}"

    p = random.randint(1, 10000)
    x = random.randint(1, 10000)

    output_file = os.path.basename(input_file).split('.')[0]

    # Return to Parsl to be executed on the workflow
    return f"cd {raxml_dir}; {raxml_exec} {flags} -p {p} -x {x} -s {input_file} -n {output_file}"


@parsl.python_app(executors=['single_thread'])
def setup_tree_output(basedir: str,
                            config: BioConfig,
                            inputs=[],
                            outputs=[],
                            stderr=parsl.AUTO_LOGNAME,
                            stdout=parsl.AUTO_LOGNAME):
    """Create the phylogenetic tree software (raxml, iqtree,...) output file and organize the temporary files to subsequent softwares 

    Parameters:
        TODO:
    Returns:
        returns an parsl's AppFuture

    TODO: 
        Provide provenance.

    NB:
        Stdout and Stderr are defaulted to parsl.AUTO_LOGNAME, so the log will be automatically 
        named according to task id and saved under task_logs in the run directory.
    """
    import os
    import sys
    sys.path.append(config.script_dir)
    import data_management as dm
    if(config.tree_method == "ML-RAXML"):
        dm.setup_raxml_output(basedir, config.raxml_dir, config.raxml_output) 
    elif(config.tree_method == "ML-IQTREE"):
        dm.setup_iqtree_output(basedir, config.iqtree_dir, config.iqtree_output)
    return

@parsl.bash_app(executors=['single_thread'])
def astral(basedir: str,
           config: BioConfig,
           inputs=[],
           outputs=[],
           stderr=parsl.AUTO_LOGNAME,
           stdout=parsl.AUTO_LOGNAME):
    """Runs the Astral's executable (RPS) on a directory (input)

    Parameters:
        TODO:
    Returns:
        returns an parsl's AppFuture

    TODO: Provide provenance.

    NB:
        Stdout and Stderr are defaulted to parsl.AUTO_LOGNAME, so the log will be automatically 
        named according to task id and saved under task_logs in the run directory.
    """
    import glob

    astral_dir = f"{basedir}/{config.astral_dir}"
    bs_file = f'{astral_dir}/BSlistfiles'
    boot_strap = f"{basedir}/{config.raxml_dir}/bootstrap/*"

    # Build the invocation command.

    # TODO: manage the fixed bootstrap number...
    num_boot = 100

    # Create bs_file
    with open(bs_file, 'w') as f:
        for i in glob.glob(boot_strap):
            f.write(f'{i}\n')

    exec_astral = config.astral
    raxml_output = f"{basedir}/{config.raxml_output}"
    astral_output = f"{basedir}/{config.astral_output}"

    # Return to Parsl to be executed on the workflow
    return f'{exec_astral} -i {raxml_output} -b {bs_file} -r {num_boot} -o {astral_output}'

@parsl.bash_app(executors=['snaq'])
def snaq(basedir: str,
         config: BioConfig,
         inputs=[],
         outputs=[],
         stderr=parsl.AUTO_LOGNAME,
         stdout=parsl.AUTO_LOGNAME):
    #set environment variables
    import os
    from pathlib import Path
    os.environ["JULIA_SETUP"] = config.julia_setup
    os.environ["JULIA_PKGDIR"] = config.julia_pkgdir
    os.environ["JULIA_SYSIMAGE"] = config.julia_sysimage
    #run the julia script with PhyloNetworks
    snaq_exec = config.snaq
    num_threads = config.snaq_threads
    hmax = config.snaq_hmax
    if config.tree_method == "ML-RAXML":
        return f'julia {config.julia_sysimage} --threads {num_threads} {snaq_exec} 0 {basedir}/{config.raxml_output} {basedir}/{config.astral_output} {basedir} {num_threads} {hmax}'
    elif config.tree_method == "ML-IQTREE":
        return f'julia {config.julia_sysimage} --threads {num_threads} {snaq_exec} 0 {basedir}/{config.iqtree_output} {basedir}/{config.astral_output} {basedir} {num_threads} {hmax}'
    else:
        pass

# Mr.Bayes bash app
@parsl.bash_app(executors=['single_thread'])
def mrbayes(basedir: str,
            config: BioConfig,
            input_file: str,
            inputs=[],
            stderr=parsl.AUTO_LOGNAME,
            stdout=parsl.AUTO_LOGNAME):
    """Runs the Mr. Bayes' executable (RPS) on a gene alignment file

    Parameters:
        input_file
    Returns:
        returns an parsl's AppFuture

    TODO: Provide provenance.

    NB:
        Stdout and Stderr are defaulted to parsl.AUTO_LOGNAME, so the log will be automatically 
        named according to task id and saved under task_logs in the run directory.
    """
    import os
    from pathlib import Path
    gene_name = os.path.basename(input_file)
    mb_folder = os.path.join(basedir, "mrbayes")
    gene_file = open(input_file, 'r')
    gene_string = gene_file.read()
    gene_file.close()
    #open the gene alignment file, read its contents and create a new file with mrbayes parameters
    gene_par = open(os.path.join(mb_folder, gene_name), 'w+')
    gene_par.write(gene_string)
    par = f"begin mrbayes;\nset nowarnings=yes;\nset autoclose=yes;\nlset nst=2;\n{config.mrbayes_parameters};\nmcmc;\nsumt;\nend;"
    gene_par.write(par)
    return f"{config.MBExecutable} {os.path.join(mb_folder, gene_name)} 2>&1 | tee {os.path.join(mb_folder, gene_name + '.log')}"

# mbsum bash app
@parsl.bash_app(executors=['single_thread'])
def mbsum(basedir: str,
            config: BioConfig,
            input_file: str,
            inputs=[],
            stderr=parsl.AUTO_LOGNAME,
            stdout=parsl.AUTO_LOGNAME):
    """Runs the mbsum' executable (RPS) on a directory (input)

    Parameters:
        TODO:
    Returns:
        returns an parsl's AppFuture

    TODO: Provide provenance.

    NB:
        Stdout and Stderr are defaulted to parsl.AUTO_LOGNAME, so the log will be automatically 
        named according to task id and saved under task_logs in the run directory.
    """
    import os
    from pathlib import Path
    import glob
    gene_name = os.path.basename(input_file)
    mbsum_folder = os.path.join(basedir, "mbsum")
    mrbayes_folder = os.path.join(basedir, "mrbayes")
    #get the mrbayes parameters
    par = config.mrbayes_parameters.split(' ')
    par_dir = {}
    for p in par:
        P_split = p.split('=')
        par_dir[p[0]] = float(p[1])
    trim =(( (par_dir['ngen']/par_dir['samplefreq'])*par_dir['nruns']*par_dir['burninfrac'])/par_dir['nruns']) +1 
    #select all the mrbayes .t files of the gene alignment file
    trees = glob.glob(os.path.join(mrbayes_folder, gene_name + '*.t'))
    return f"mbsum {(' ').join(trees)} -n {trim} -o {os.path.join(mbsum_folder, gene_name + '.sum')}"

@parsl.python_app(executors=['single_thread'])
def setup_bucky_data(basedir: str,
            config: BioConfig,
            inputs=[],
            stderr=parsl.AUTO_LOGNAME,
            stdout=parsl.AUTO_LOGNAME):
    """Runs the mbsum' executable (RPS) on a directory (input)

    Parameters:
        TODO:
    Returns:
        returns an parsl's AppFuture

    TODO: Provide provenance.

    NB:
        Stdout and Stderr are defaulted to parsl.AUTO_LOGNAME, so the log will be automatically 
        named according to task id and saved under task_logs in the run directory.
    """
    import re
    import os
    from pathlib import Path
    import glob
    from itertools import combinations
    mbsum_folder = os.path.join(basedir, "mbsum")
    bucky_folder = os.path.join(basedir, "bucky")
    #parse the sumarized taxa by mbsum
    files = glob.glob(os.path.join(mbsum_folder, '*.sum'))
    taxa = {}
    selected_taxa = {}
    pattern = re.compile('translate(\n\s*\d+\s+\w+(,|;))+')
    taxa_pattern = re.compile('(\w+(,|;))')
    for file in files:
        gene_sum = open(file, 'r')
        text = gene_sum.read()
        gene_sum.close()
        translate_block = pattern.search(text)
        for match in re.findall(taxa_pattern, translate_block[0]):
            key = re.sub(re.compile('(,|;)'), '',match[0])
            if key in taxa:
                taxa[key]+=1
            else:
                taxa[key]=1
    #select the taxa shared across all genes
    for t in taxa:
        if(taxa[t] == len(files)):
            selected_taxa[t] = t
    #create all the selected quartets combinations
    quartets = combinations(selected_taxa, 4)
    for quartet in quartets:
        prune_tree_output = "translate\n"
        count = 0
        filename = ""
        for member in tuple(quartet):
            filename += member
            count+=1
            prune_tree_output+= f" {count} {member}"
            if count == 4:
                prune_tree_output+= ";\n"
            else:
                filename +="--"
                prune_tree_output+= ",\n"
        #create the prune tree file necessary for bucky
        prune_file_path = os.path.join(bucky_folder,f"{filename}-prune.txt")
        output_file = os.path.join(bucky_folder, filename)
        prune_file = open(prune_file_path, 'w')
        prune_file.write(prune_tree_output)
        prune_file.close()
    return

@parsl.bash_app(executors=['single_thread'])
def bucky(basedir: str,
                    config: BioConfig,
                    prune_file: str,
                    inputs=[],
                    outputs=[],
                    stderr = parsl.AUTO_LOGNAME,
                    stdout=parsl.AUTO_LOGNAME):
    import os
    import glob
    import re
    mbsum_folder = os.path.join(basedir, "mbsum")
    bucky_folder = os.path.join(basedir, "bucky")
    files = glob.glob(os.path.join(mbsum_folder, '*.sum'))
    output_file = os.path.basedir(prune_file)
    output_file = re.sub("-prune.txt", "", output_file)
    output_file = os.path.join(bucky_folder, output_file)
    return f"{config.bucky} -a 1 -n 1000000 -cf 0 -o {output_file} -p {prune_file} {(' ').join(files)}"

@parsl.python_app(executors=['single_thread'])
def setup_bucky_output(basedir: str,
                    config: BioConfig,
                    inputs=[],
                    outputs=[],
                    stderr = parsl.AUTO_LOGNAME,
                    stdout=parsl.AUTO_LOGNAME):
    import re
    import os
    import glob
    bucky_folder = os.path.join(basedir, "bucky")
    pattern = re.compile("Read \d+ genes with a ")
    out_files = glob.glob(os.path.join(bucky_folder, "*.out"))
    table_string = "taxon1,taxon2,taxon3,taxon4,CF12.34,CF12.34_lo,CF12.34_hi,CF13.24,CF13.24_lo,CF13.24_hi,CF14.23,CF14.23_lo,CF14.23_hi,ngenes\n"
    cf_95_pattern = re.compile("(95% CI for CF = \(\w+,\w+\))")
    mean_num_loci_pattern = re.compile("(=\s+\d+\.\d+\s+\(number of loci\))")
    translate_block_pattern = re.compile("translate\n(\s*\w+\s*\w+(,|;)\n*)+")
    #open all the bucky's output files and parse them 
    for out_file in out_files:
        taxa = []
        splits = {}
        f = open(out_file, 'r')
        lines = f.read()
        f.close()
        num_genes = re.search(pattern, lines).group(0)
        num_genes = re.search("\d+",num_genes).group(0)
        name_wo_extension = re.sub(".out|", "", os.path.basename(out_file))
        concordance_file = os.path.join(os.path.dirname(out_file), f"{name_wo_extension}.concordance")
        f = open(concordance_file, 'r')
        lines = f.read()
        f.close()
        translate_block = re.search(translate_block_pattern, lines).group(0)
        translate_block = re.sub("(,|;|translate\n)", "", translate_block)
        taxon_list = translate_block.split('\n')
        for taxon in taxon_list:
            if(taxon == ""):
                break;
            t = taxon.split(" ")
            taxa.append(t[2])
        all_splits_block= lines.split("All Splits:\n")[1]
        split = re.findall("{\w+,\w+\|\w+,\w+}", all_splits_block)
        cf = re.findall(mean_num_loci_pattern, all_splits_block)
        cf_95 = re.findall(cf_95_pattern, all_splits_block)
        for i in range(0, len(split)):
            split[i] = re.sub("({|,|})", "", split[i])
            split_dict = {}
            cf[i] = re.sub("(=|\(number of loci\)|\s+)", "", cf[i])
            cf_95[i] = re.sub("(95% CI for CF = \(|\))", "", cf_95[i])
            cf_95_list = cf_95[i].split(',')
            print(cf_95_list)
            split_dict['CF'] = float(cf[i])/float(num_genes)
            split_dict['95_CI_LO'] = float(cf_95_list[0])/float(num_genes)
            split_dict['95_CI_HI'] = float(cf_95_list[1])/float(num_genes)
            splits[split[i]] = split_dict
        parsed_line = (',').join(taxa)
        parsed_line+=','
        if "12|34" in splits:
            parsed_line+= f"{splits['12|34']['CF']},{splits['12|34']['95_CI_LO']},{splits['12|34']['95_CI_HI']},"
        else:
            parsed_line+= "0,0,0,"
        if "13|24" in splits:
                    parsed_line+= f"{splits['13|24']['CF']},{splits['13|24']['95_CI_LO']},{splits['13|24']['95_CI_HI']},"

        else:
            parsed_line+= "0,0,0,"
        if "14|23" in splits:
                    parsed_line+= f"{splits['14|23']['CF']},{splits['14|23']['95_CI_LO']},{splits['14|23']['95_CI_HI']}"
        else:
            parsed_line+= "0,0,0"
        parsed_line+= f",{num_genes}\n"
        table_string+=parsed_line
    #create the table folder
    table_name = os.path.basename(basedir)
    table_name = os.path.join(bucky_folder, f"{table_name}.csv")
    table_file = open(table_name, 'w')
    table_file.write(table_string)
    table_file.close()

@parsl.python_app(executors=['single_thread'])
def setup_qmc_data(basedir: str,
                    config: BioConfig,
                    inputs=[],
                    outputs=[],
                    stderr = parsl.AUTO_LOGNAME,
                    stdout=parsl.AUTO_LOGNAME):
    import pandas as pd
    import json
    import os
    from pathlib import Path
    dir_name = os.path.basename(basedir)
    bucky_folder = os.path.join(basedir, "bucky")
    table_filename = os.path.join(bucky_folder, f'{dir_name}.csv')
    try:
        table = pd.read_csv(table_filename, delimiter=',', dtype = 'string')   
    except Exception:
        print("Failed to open CF table")
    table = pd.read_csv(table_filename, delimiter=',', dtype = 'string')
    #parse the table
    quartets = []
    taxa = {}
    for index, row in table.iterrows():
        for i in range (1, 5):
            if row['taxon' + str(i)] in taxa:
                taxa[row['taxon' + str(i)]]+=1
            else:
                taxa[row['taxon' + str(i)]]=1
        cf = {'CF12.34': float(row['CF12.34']), 'CF13.24': float(row['CF13.24']), 'CF14.23': float(row['CF14.23'])}
        cf_sorted = [k for k in sorted(cf, key=cf.get, reverse=True)]
        cf_1 = row[cf_sorted[0]]
        cf_2 = row[cf_sorted[1]]
        cf_3 = row[cf_sorted[2]]
        split_1 = f"{row['taxon' + cf_sorted[0][2]]},{row['taxon' + cf_sorted[0][3]]}|{row['taxon' + cf_sorted[0][5]]},{row['taxon' + cf_sorted[0][6]]}"
        split_2 = f"{row['taxon' + cf_sorted[1][2]]},{row['taxon' + cf_sorted[1][3]]}|{row['taxon' + cf_sorted[1][5]]},{row['taxon' + cf_sorted[1][6]]}"
        split_3 = f"{row['taxon' + cf_sorted[2][2]]},{row['taxon' + cf_sorted[2][3]]}|{row['taxon' + cf_sorted[2][5]]},{row['taxon' + cf_sorted[2][6]]}"
        if(cf_1 == cf_2 == cf_3):
            quartets.extend([split_1, split_2, split_3])	
        elif (cf_1 == cf_2):
            quartets.extend([split_1, split_2])
        else:
            quartets.append(split_1)
    #change taxon names to ids	
    taxa_id = 1
    taxon_to_id = {}
    dir_name = os.path.basename(basedir)
    for k in sorted(taxa):
        taxon_to_id[k] = taxa_id
        taxa_id+=1
    for i in range(0, len(quartets)):
        tmp1 = quartets[i].split('|')
        old_quartets = []
        old_quartets.extend(tmp1[0].split(','))
        old_quartets.extend(tmp1[1].split(','))
        quartets[i] = f"{taxon_to_id[old_quartets[0]]},{taxon_to_id[old_quartets[1]]}|{taxon_to_id[old_quartets[2]]},{taxon_to_id[old_quartets[3]]}"
    qmc_folder = os.path.join(basedir, "qmc")
    qmc_input = os.path.join(qmc_folder, f'{dir_name}.txt')
    qmc_input_file = open(qmc_input, 'w+')
    qmc_input_file.write((' ').join(quartets))
    qmc_input_file.close()
    #dump ids
    with open(os.path.join(qmc_folder, f'{dir_name}.json'), "w+") as outfile: 
        json.dump(taxon_to_id, outfile)
    return

@parsl.bash_app(executors=['single_thread'])
def quartet_maxcut(basedir: str,
                      config: BioConfig,
                      inputs=[],
                      outputs=[],
                      stderr=parsl.AUTO_LOGNAME,
                      stdout=parsl.AUTO_LOGNAME):
    import os
    dir_name = os.path.basename(basedir)
    qmc_folder = os.path.join(basedir, "qmc")
    qmc_input = os.path.join(qmc_folder, f'{dir_name}.txt')
    qmc_output = os.path.join(qmc_folder, f'{dir_name}.txt')
    exec_qmc = config.quartet_maxcut
    return f'{exec_qmc} qrtt={qmc_input} otre={qmc_output}'

@parsl.python_app(executors=['single_thread'])
def setup_qmc_output(basedir: str,
                      config: BioConfig,
                      inputs=[],
                      outputs=[],
                      stderr=parsl.AUTO_LOGNAME,
                      stdout=parsl.AUTO_LOGNAME):
    import os
    import pandas as pd
    import re
    dir_name = os.basedir
    qmc_folder = os.path.join(basedir, "qmc")
    qmc_input = os.path.join(qmc_folder, f'{dir_name}.txt')
    qmc_output = os.path.join(qmc_folder, f'{dir_name}.txt')
    taxon_json = os.path.join(qmc_folder, f'{dir_name}.json')
    taxon_to_id = pd.read_json (taxon_json)
    tree_file = open(qmc_output, 'r+')
    lines = tree_file.read()
    tree_file.close()
    tree_file = open(qmc_output, 'w')
    for k in sorted(taxon_to_id, key=taxon_to_id.get, reverse=True):
        lines = re.sub(str(taxon_to_id[k]), k, lines)
    tree_file.write(lines)
    tree_file.close()
    return 


@parsl.python_app(executors=['single_thread'])
def setup_phylonet_data(basedir: str,
                      config: BioConfig,
                      inputs=[],
                      outputs=[],
                      stderr=parsl.AUTO_LOGNAME,
                      stdout=parsl.AUTO_LOGNAME):
    """Get the raxml/iqtree's output and create a NEXUS file as output for the phylonet in the basedir

    Parameters:
        TODO:
    Returns:
        returns an parsl's AppFuture

    TODO: Provide provenance.

    NB:
        Stdout and Stderr are defaulted to parsl.AUTO_LOGNAME, so the log will be automatically 
        named according to task id and saved under task_logs in the run directory.
    """
    import os
    if(config.tree_method == "ML-RAXML"):        
        gene_trees = os.path.join(basedir, config.raxml_dir)
        gene_trees = os.path.join(gene_trees, config.raxml_output)
    else:
        gene_trees = os.path.join(basedir, config.iqtree_dir)
        gene_trees = os.path.join(gene_trees, config.iqtree_output)
    out_dir = os.path.join(basedir,config.phylonet_input)
    import sys
    sys.path.append(config.script_dir)
    import data_management as dm
    dm.create_phylonet_input(gene_trees, out_dir, config.phylonet_hmax, config.phylonet_threads, config.phylonet_threads)
    return
    
@parsl.bash_app(executors=['snaq'])
def phylonet(basedir: str,
         config: BioConfig,
         inputs=[],
         outputs=[],
         stderr=parsl.AUTO_LOGNAME,
         stdout=parsl.AUTO_LOGNAME):
    """Run PhyloNet using as input the phylonet_input variable

    Parameters:
        TODO:
    Returns:
        returns an parsl's AppFuture

    TODO: Provide provenance.

    NB:
        Stdout and Stderr are defaulted to parsl.AUTO_LOGNAME, so the log will be automatically 
        named according to task id and saved under task_logs in the run directory.
    """
    exec_phylonet = config.phylonet
    import os
    input_file = os.path.join(basedir,config.phylonet_input)

    # Return to Parsl to be executed on the workflow
    return f'{exec_phylonet} {input_file}'

@parsl.python_app(executors=['single_thread'])
def clear_temporary_files(basedir: str,
                      config: BioConfig,
                      inputs=[],
                      outputs=[],
                      stderr=parsl.AUTO_LOGNAME,
                      stdout=parsl.AUTO_LOGNAME):
    import sys
    import os
    sys.path.append(config.script_dir)
    import data_management as dm
    dm.clear_execution(config.network_method, config.tree_method, basedir)
    return

@parsl.python_app(executors=['single_thread'])
def create_folders(basedir: str,
                      config: BioConfig,
                      folders=[],
                      inputs=[],
                      outputs=[],
                      stderr=parsl.AUTO_LOGNAME,
                      stdout=parsl.AUTO_LOGNAME):
    import os
    import sys
    sys.path.append(config.script_dir)
    import data_management as dm
    dm.create_folders(basedir, folders)
    return
    
@parsl.bash_app(executors=['raxml'])
def iqtree(basedir: str, config: BioConfig,
          input_file: str,
          inputs=[],
          stderr=parsl.AUTO_LOGNAME,
          stdout=parsl.AUTO_LOGNAME):
    import os
    iqtree_dir = os.path.join(basedir, config.iqtree_dir)
    flags = f"-T {config.iqtree_threads} {config.iqtree_exec_param} -s {input_file}"
    # Return to Parsl to be executed on the workflow
    return f"cd {iqtree_dir}; {config.iqtree} {flags}"