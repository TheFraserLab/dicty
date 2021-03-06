"""Script to count reference and alternate reads at a list of SNPs

Output a tab-separated table with counts for reference, alternate, and
non-ref/alt read counts at each SNP location in a provided bedfile.

Positions in the output are 1-based coordinates.
"""

import pysam
import argparse
from tqdm import tqdm
from collections import defaultdict


def pipesplit(col):
    return lambda input: input.split("|")[col]


def parse_args():
    "Parse command line arguments"

    parser = argparse.ArgumentParser()
    parser.add_argument("snps", help="SNP BED file")
    parser.add_argument("reads", help="Mapped reads file BAM or (untested) SAM")
    parser.add_argument("output")
    return parser.parse_args()


def parse_bed(fname):
    """Parse bedfile into a by-chromosome ref/alt dictionary.

    Output: Dictionary of dictionaries. Outer dictionary keyed by chromosome
    name, inner dictionary keyed by 0-based SNP coordinate.  Each element of the
    inner dictionary is a list of [REFERENCE_BASE, ALTERNATE_BASE]
        """
    outdict = defaultdict(dict)
    for line in open(fname):
        chr, pos0, pos1, refalt = line.split()
        pos0 = int(pos0)
        chrdict = outdict[chr]
        chrdict[pos0] = refalt.split("|")
    return outdict


if __name__ == "__main__":
    args = parse_args()
    snps = parse_bed(args.snps)

    out_table = {(chr, pos + 1): [0, 0, 0] for chr in snps for pos in snps[chr]}

    reads = pysam.AlignmentFile(args.reads)
    chrnames = reads.references
    for read in tqdm(reads, total=reads.mapped):
        chrom = chrnames[read.reference_id]
        if chrom not in snps:
            continue
        chrsnps = snps[chrom]
        seq = read.seq

        for rpos, pos in read.get_aligned_pairs(matches_only=True):
            base = read.seq[rpos].upper()
            ptuple = chrom, pos + 1
            if pos in chrsnps:
                ref, alt = chrsnps[pos]
                if base == ref:
                    out_table[ptuple][0] += 1
                elif base == alt:
                    out_table[ptuple][1] += 1
                else:
                    out_table[ptuple][2] += 1

    with open(args.output, "w") as outfh:
        print(
            "CHROM",
            "POS",
            "REF_BASE",
            "ALT_BASE",
            "REF",
            "ALT",
            "NON_REFALT",
            sep="\t",
            file=outfh,
        )
        for (chrom, pos) in sorted(out_table):
            print(
                chrom,
                pos,
                *snps[chrom][pos - 1],
                *out_table[(chrom, pos)],
                sep="\t",
                file=outfh
            )
