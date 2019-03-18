----
Dictyostelium pooled processing
----

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Build Status](https://travis-ci.com/petercombs/dicty.svg?branch=master)](https://travis-ci.com/petercombs/dicty)

Software for processing data related to pooled Dicty strains.  As of 7/12/18,
we're looking for SNPs that are related to cheating/altruism by pooling dozens
of strains, then sequencing spores and stalks and comparing the allele frequencies.

In order to incorporate new samples, one needs to edit `config.yaml` to update
the `activesamples` variable to include the correct samples. I _think_ I wrote
the Snakefile to find files based on name assuming that it's relatively sanely
named, but ymmv...

After downloading prerequisite files, it should be straightforward to simply
use `snakemake` in the simplest possible way, i.e.:
 
```
snakemake --use-conda all
```

which should generate the appropriate output files in `analysis/results`. This
is a relatively wide job tree (with a couple narrow chokepoints), so giving
snakemake as many cores as you can will be helpful.


Prerequisites
======

You will need to download Dictyostelium and E. coli FASTA files and save them as:

* `Reference/reference.fasta` (Dictyostelium genome)
* `Reference/ecoli_k12_mg1655.fasta` (E. coli)

You should also have lmod installed, and have modules for:

* STAR
* bcftools
* bedtools
* bioawk
* blast
* bowtie2
* cufflinks
* java
* macs2
* picard
* samtools

Additionally, you should have docker installed and the Ensembl Variant Effect
Predictor dockerfile (ensemblorg/ensembl-vep) downloaded.

Analyses Performed
======

* Per-SNP Scores:

    1. The first step in this analysis is, for each fruiting body, to build a
       contingency table for each SNP `[[spore_ref, spore_alt], [stalk_ref,
       stalk_alt]]`. We can then use Fisher's Exact Test to test for deviation
       from the null hypothesis that there is no relationship between the
       REF/ALT status of the SNP and its representation in the different parts
       of the fruiting body. For reasons discussed below (see step 3), we
       perform a 1-sided test. (Snakemake rule: `score_snps`)

    2. We don't want to make the assumption that the scores from the FET have
       any particular distribution, so for combining scores between fruiting
       bodies, we first rank the p-values from 1/N to 1, where N is the number
       of SNPs that we could measure for that sorus. Then, we use Fisher's
       method to combine these ranks, and that satisfies the assumption that
       the inputs to that test are uniformly distributed. (Snakemake rule:
       `fisher_pvalues`)

    3. We perform step 2 both assuming that the reference allele is
       overrepresented in the stalk and that it's overrepresented in the spore.
       This is easily accomplished by simply reversing the order of the list.
       Further, as a null, we randomize the order of score-able SNPs within a
       fruiting body and calculate Fisher-combined p-values for those SNPs.

* GC Coverage Plot `analysis/combined/gc_cov_normed.png` (Generated by Snakemake Rule `plot_gc_bias`)
   - Dictyostelium is a very AT rich genome---an average of only about 23% GC.
     This has a huge effect on the PCR and library prep. Therefore, it's a good
     idea to at least check whether there's reasonable coverage of the low GC
     windows.  
   - This plot consists of a lower histogram of GC% for each 1kb window in the
     genome, and an upper scatter plot indicating the normalized coverage in
     windows of that size. There are as many subsets of libraries as you like,
     and can be controlled by editing the input files in the Snakemake
     `plot_gc_bias` rule.
   - _"Normalized coverage"_ in this case means **FIXMEFIXME**
   - About the best I can do after some testing of protocols is to have about
     the top half of windows have 1x coverage or better. 

* BLAST report `analysis/results/blastsummary.tsv` (Generated by rule
  `blast_summary`)
    - Due likely in part to the non-optimal growth conditions, and likely in
      part to the much more normal GC content of bacteria compared to Dicty,
      libraries tend to be pretty heavily contaminated with bacterial reads. 
    - This generates a table for each library containing the blast results of
      5,000 reads to the NT database. Ideally most of them will have
      Dictyostelium as the best hit, but in thus far the rate of successful
      libraries is actually quite low. 

* Assorted plots (Generated by Snakemake rule `pval_plot`):
    - Manhattan Plot `analysis/results/manhattan.png`
    - "Tehranchigram" `analysis/results/all_prepost.png`. This is the plot with
      allele frequency in the stalk on the X axis, and in the spore on the Y
      axis. Significant SNPs should be well above or below the diagonal.
    - QQ Plot (`analysis/results/combined_pvals_spore_and_stalk.png`): By
      plotting the score per SNP against the combined p-value after randomizing
      the order, we can get a better sense of which SNPs are likely to be
      significant.


